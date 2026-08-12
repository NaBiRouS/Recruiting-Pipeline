import json
from src.api import TalentBaseAPI
from src.utils import (
    normalize_name,
    normalize_email,
    normalize_email_local,
    normalize_phone,
)


def find_duplicate_pairs(candidates):
    """
    Find duplicate groups using strong deterministic identity signals,
    then return one canonical record for each duplicate group.
    """

    parent = {candidate["id"]: candidate["id"] for candidate in candidates}

    def find(candidate_id):
        while parent[candidate_id] != candidate_id:
            parent[candidate_id] = parent[parent[candidate_id]]
            candidate_id = parent[candidate_id]

        return candidate_id

    def union(a_id, b_id):
        root_a = find(a_id)
        root_b = find(b_id)

        if root_a != root_b:
            parent[root_b] = root_a

    # Group by strong identity signals
    email_groups = {}
    phone_groups = {}
    ambiguous_groups = {}

    for candidate in candidates:
        candidate_id = candidate["id"]

        email = normalize_email(candidate.get("email"))
        phone = normalize_phone(candidate.get("phone"))

        name = normalize_name(candidate.get("name"))
        local = normalize_email_local(candidate.get("email"))
        title = normalize_name(candidate.get("current_title"))

        if email:
            email_groups.setdefault(email, []).append(candidate_id)

        if phone:
            phone_groups.setdefault(phone, []).append(candidate_id)

        # Ambiguous signal:
        # same name + same email local-part + same title
        if name and local and title:
            key = (name, local, title)
            ambiguous_groups.setdefault(key, []).append(candidate_id)

    # Exact email matches
    for group in email_groups.values():
        for candidate_id in group[1:]:
            union(group[0], candidate_id)

    # Exact phone matches
    for group in phone_groups.values():
        for candidate_id in group[1:]:
            union(group[0], candidate_id)

    # Same name + email local-part + title
    for group in ambiguous_groups.values():
        for candidate_id in group[1:]:
            union(group[0], candidate_id)

    # Build connected components
    components = {}

    for candidate in candidates:
        root = find(candidate["id"])
        components.setdefault(root, []).append(candidate)

    duplicates = []

    # Each component with >1 candidate is a duplicate group
    for group in components.values():

        if len(group) < 2:
            continue

        # Choose canonical record
        canonical = group[0]

        for candidate in group[1:]:
            canonical, _ = choose_canonical(canonical, candidate)

        for candidate in group:
            if candidate["id"] == canonical["id"]:
                continue

            # Determine why this candidate belongs to the group
            reasons = []

            canonical_email = normalize_email(canonical.get("email"))
            candidate_email = normalize_email(candidate.get("email"))

            canonical_phone = normalize_phone(canonical.get("phone"))
            candidate_phone = normalize_phone(candidate.get("phone"))

            canonical_name = normalize_name(canonical.get("name"))
            candidate_name = normalize_name(candidate.get("name"))

            if (
                canonical_email
                and canonical_email == candidate_email
            ):
                reasons.append("same email")

            if (
                canonical_phone
                and canonical_phone == candidate_phone
            ):
                reasons.append("same phone")

            if (
                canonical_name
                and canonical_name == candidate_name
                and normalize_email_local(canonical.get("email"))
                == normalize_email_local(candidate.get("email"))
                and normalize_name(canonical.get("current_title"))
                == normalize_name(candidate.get("current_title"))
            ):
                reasons.append(
                    "same name, email local-part, and title"
                )

            # If this candidate is connected through another duplicate,
            # use the fact that it belongs to the same duplicate component.
            if not reasons:
                reasons.append("connected to duplicate group through matching email or phone")

            duplicates.append({
                "candidate_id": candidate["id"],
                "duplicate_of": canonical["id"],
                "confidence": 1.0 if (
                    "same email" in reasons or
                    "same phone" in reasons
                ) else 0.95,
                "reason": ", ".join(reasons),
            })

    return duplicates


def choose_canonical(a, b):
    """
    Prefer the record with the longer resume.
    If equally long, use the smaller candidate ID.
    """

    resume_a = a.get("resume_text") or ""
    resume_b = b.get("resume_text") or ""

    if len(resume_a) > len(resume_b):
        return a, b

    if len(resume_b) > len(resume_a):
        return b, a

    if a["id"] < b["id"]:
        return a, b

    return b, a


def run_deduplication():
    api = TalentBaseAPI()

    print("Fetching candidates...")
    candidates = api.get_all_candidates()
    print(f"Fetched {len(candidates)} candidates.")


    duplicates = find_duplicate_pairs(candidates)

    output = []
    for duplicate in duplicates:
        output.append({
            "candidate_id": duplicate["candidate_id"],
            "duplicate_id": duplicate["duplicate_of"],
            "confidence": duplicate["confidence"],
            "reason": duplicate["reason"]
        })

    with open("duplicates.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(output)} duplicate relationships to duplicates.json")


    print("\nWriting duplicate information to API...")
    updated = 0
    failed = 0

    for duplicate in duplicates:
        candidate_id = duplicate["candidate_id"]

        enrichment = {
            "duplicate_of": duplicate["duplicate_of"]
        }

        try:
            api.update_enrichment(candidate_id, enrichment)
            updated += 1

        except Exception as e:
            failed += 1
            print(f"Failed: {candidate_id} -> {e}")

    print("\nAPI write-back complete.")
    print(f"Updated: {updated}")
    print(f"Failed:  {failed}")


    print("\nVerifying API write-back...")
    for duplicate in duplicates[:5]:
        candidate_id = duplicate["candidate_id"]

        candidate = api.get(f"/candidates/{candidate_id}")

        print(
            f"{candidate_id} -> "
            f"{candidate['enrichment']}"
        )

    return {
        "duplicates_found": len(duplicates),
        "updated": updated,
        "failed": failed,
    }



if __name__ == "__main__":
    run_deduplication()