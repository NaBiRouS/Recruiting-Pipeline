import json

from src.api import TalentBaseAPI


SENIORITY_LEVELS = {
    "intern": 0,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
    "manager": 6,
    "director": 7,
    "executive": 8,
}


def load_duplicate_ids():
    """
    Load candidates that were identified as duplicates.
    """

    with open("duplicates.json", "r", encoding="utf-8") as f:
        duplicates = json.load(f)

    return {
        duplicate["candidate_id"]
        for duplicate in duplicates
    }


def is_eligible(candidate, job, duplicate_ids):
    """
    Apply hard filters.

    A candidate is rejected if:
    - they are a duplicate
    - enrichment is missing
    - seniority is below the job minimum
    """

    candidate_id = candidate["id"]

    if candidate_id in duplicate_ids:
        return False, "duplicate"

    enrichment = candidate.get("enrichment")

    if not enrichment:
        return False, "missing enrichment"

    candidate_seniority = enrichment.get("seniority")
    job_min_seniority = job["min_seniority"]

    # Missing/invalid seniority
    if candidate_seniority not in SENIORITY_LEVELS:
        return False, "invalid seniority"

    # Seniority below minimum
    if (
        SENIORITY_LEVELS[candidate_seniority]
        < SENIORITY_LEVELS[job_min_seniority]
    ):
        return False, "seniority below minimum"

    return True, None


def score_candidate(candidate, job):
    """
    Score an eligible candidate.
    """

    enrichment = candidate["enrichment"]

    skills = set(enrichment.get("skills") or [])


    score = 0

    must_have = set(job.get("must_have") or [])
    matched_must_have = skills.intersection(must_have)
    # 15 points per must-have skill
    score += len(matched_must_have) * 15

    nice_to_have = set(job.get("nice_to_have") or [])
    matched_nice_to_have = skills.intersection(nice_to_have)
    # 5 points per nice-to-have skill
    score += len(matched_nice_to_have) * 5

    # 2 points per higer seniority level
    seniority_level = SENIORITY_LEVELS[enrichment["seniority"]]
    minimum_level = SENIORITY_LEVELS[job["min_seniority"]]

    seniority_points = (seniority_level - minimum_level) * 2
    score += seniority_points

    # Preferred domain
    if enrichment.get("domain") == job.get("domain_preference"):
        score += 10

    # work mode
    candidate_work_mode = enrichment.get("work_mode")
    job_work_mode = job.get("work_mode")
    if candidate_work_mode == job_work_mode:
        score += 10

    # Uncertain enrichment gets a small penalty
    if enrichment.get("needs_review", False):
        score -= 5

    return score


def build_reason(candidate, job, score):
    """
    Build the required one-line shortlist reason.
    """

    enrichment = candidate["enrichment"]

    skills = set(enrichment.get("skills") or [])

    must_have = set(job.get("must_have") or [])
    nice_to_have = set(job.get("nice_to_have") or [])

    matched_must = sorted(skills.intersection(must_have))
    matched_nice = sorted(skills.intersection(nice_to_have))

    seniority = enrichment.get("seniority")
    domain = enrichment.get("domain")
    work_mode = enrichment.get("work_mode")

    parts = [
        f"{len(matched_must)}/{len(must_have)} required skills: "
        f"{', '.join(matched_must) if matched_must else 'none'}",
    ]

    if seniority:
        parts.append(f"{seniority} seniority")
    
    if matched_nice:
        parts.append(
            f"nice-to-have: {', '.join(matched_nice)}"
        )

    if domain == job.get("domain_preference"):
        parts.append(f"{domain} domain")

    if work_mode == job.get("work_mode"):
        parts.append(f"work mode as required: {work_mode}")

    parts.append(f"score {score}")

    return ", ".join(parts)


def rank_candidates(candidates, job, duplicate_ids):
    """
    Filter and rank candidates for one job.
    """

    ranked = []
    rejected = {}

    for candidate in candidates:
        eligible, reason = is_eligible(
            candidate,
            job,
            duplicate_ids,
        )

        if not eligible:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue

        score = score_candidate(candidate, job)

        reason_text = build_reason(
            candidate,
            job,
            score,
        )

        ranked.append({
            "candidate_id": candidate["id"],
            "name": candidate["name"],
            "score": score,
            "reason": reason_text,
        })

    ranked.sort(
        key=lambda x: (-x["score"], x["candidate_id"])
    )

    return ranked, rejected


def run_matching():
    api = TalentBaseAPI()

    print("Fetching jobs...")
    jobs_response = api.get("/jobs")

    jobs = jobs_response["jobs"]

    job = next(
        job for job in jobs
        if job["id"] == "ROLE-2203"
    )

    print(
        f"\nSelected job: "
        f"{job['id']} - {job['title']}"
    )

    print("Fetching candidates...")
    candidates = api.get_all_candidates()

    print(f"Candidate IDs found: {len(candidates)}")

    duplicate_ids = load_duplicate_ids()

    print(
        f"Duplicate candidates excluded: "
        f"{len(duplicate_ids)}"
    )

    print("\nFetching candidate enrichments...")

    enriched_candidates = []

    for index, candidate in enumerate(candidates, start=1):
        candidate_id = candidate["id"]

        candidate_data = api.get(
            f"/candidates/{candidate_id}"
        )

        enriched_candidates.append(candidate_data)

    print("Finished fetching enrichments.")

    ranked, rejected = rank_candidates(
        enriched_candidates,
        job,
        duplicate_ids,
    )

    print("\n=== MATCHING RESULTS ===")
    print(f"Eligible candidates: {len(ranked)}")

    print("\n=== REJECTION SUMMARY ===")
    for reason, count in sorted(rejected.items()):
        print(f"{reason}: {count}")

    print("\n=== TOP 10 ===")
    for index, candidate in enumerate(
        ranked[:10],
        start=1,
    ):
        print(
            f"\n{index}. "
            f"{candidate['candidate_id']} - "
            f"{candidate['name']}"
        )
        print(f"Reason: {candidate['reason']}")


    matches = [
        {
            "candidate_id": candidate["candidate_id"],
            "reason": candidate["reason"],
        }
        for candidate in ranked[:10]

    ]

    # save to json
    submission = {
        "job_id": job["id"],
        "job_title": job["title"],
        "matches": matches,
    }

    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(
            submission,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"\nSaved {len(matches)} shortlisted candidates "
        f"for {job['id']} - {job['title']} to matches.json"
    )

    # write to api
    print("\nSubmitting shortlist...")
    result = api.submit_matches(
        job["id"],
        matches,
    )
    print("Submission result:")
    print(result)

    return {
        "job_id": job["id"],
        "job_title": job["title"],
        "eligible": len(ranked),
        "submitted": len(matches),
    }



if __name__ == "__main__":
    run_matching()