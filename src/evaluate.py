import json
import random

from src.api import TalentBaseAPI


SAMPLE_SIZE = 30
RANDOM_SEED = 42
LABEL_FILE = "evaluation_labels.json"


def select_candidates(api):
    print("Fetching candidates...")
    candidates = api.get_all_candidates()

    random.seed(RANDOM_SEED)
    selected = random.sample(candidates, SAMPLE_SIZE)

    print(f"Selected {len(selected)} candidates.")

    labels = []

    for candidate in selected:
        candidate_id = candidate["id"]

        print(f"Fetching {candidate_id}...")

        data = api.get(
            f"/candidates/{candidate_id}"
        )

        labels.append({
            "candidate_id": candidate_id,
            "name": data.get("name"),
            "resume_text": data.get("resume_text"),
            "work_mode": data.get("work_mode"),
            "manual": {
                "skills": [],
                "seniority": "",
                "domain": ""
            }
        })

    with open(LABEL_FILE, "w", encoding="utf-8") as f:
        json.dump(
            labels,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"\nCreated {LABEL_FILE}."
    )

    print(
        "Read the resumes and fill the 'manual' "
        "section for all 30 candidates."
    )


def calculate_skill_metrics(manual, predicted):
    manual = set(manual or [])
    predicted = set(predicted or [])

    if not predicted:
        precision = 1.0 if not manual else 0.0
    else:
        precision = len(
            manual.intersection(predicted)
        ) / len(predicted)

    if not manual:
        recall = 1.0 if not predicted else 0.0
    else:
        recall = len(
            manual.intersection(predicted)
        ) / len(manual)

    return precision, recall


def evaluate(api):
    with open(LABEL_FILE, "r", encoding="utf-8") as f:
        labels = json.load(f)

    total = len(labels)

    seniority_correct = 0
    domain_correct = 0
    work_mode_correct = 0

    total_skill_precision = 0
    total_skill_recall = 0

    print("\n" + "=" * 60)
    print("MANUAL EVALUATION")
    print("=" * 60)

    for item in labels:
        candidate_id = item["candidate_id"]
        manual = item["manual"]

        candidate = api.get(
            f"/candidates/{candidate_id}"
        )

        predicted = candidate.get("enrichment") or {}

        manual_seniority = manual["seniority"]
        manual_domain = manual["domain"]
        manual_work_mode = item["work_mode"]

        predicted_seniority = predicted.get("seniority")
        predicted_domain = predicted.get("domain")
        predicted_work_mode = predicted.get("work_mode")

        skill_precision, skill_recall = calculate_skill_metrics(
            manual["skills"],
            predicted.get("skills")
        )

        total_skill_precision += skill_precision
        total_skill_recall += skill_recall

        if manual_seniority == predicted_seniority:
            seniority_correct += 1

        if manual_domain == predicted_domain:
            domain_correct += 1

        if manual_work_mode == predicted_work_mode:
            work_mode_correct += 1

        print(
            f"\n{candidate_id} - {item['name']}"
        )

        print(
            f"  Seniority: "
            f"{manual_seniority} -> {predicted_seniority}"
        )

        print(
            f"  Domain: "
            f"{manual_domain} -> {predicted_domain}"
        )

        print(
            f"  Work mode: "
            f"{manual_work_mode} -> {predicted_work_mode}"
        )

        print(
            f"  Skills: "
            f"precision={skill_precision:.2f}, "
            f"recall={skill_recall:.2f}"
        )

    seniority_accuracy = (
        seniority_correct / total
    )

    domain_accuracy = (
        domain_correct / total
    )

    work_mode_accuracy = (
        work_mode_correct / total
    )

    skill_precision = (
        total_skill_precision / total
    )

    skill_recall = (
        total_skill_recall / total
    )

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    print(
        f"Candidates evaluated: {total}"
    )

    print(
        f"Seniority accuracy: "
        f"{seniority_accuracy:.2%}"
    )

    print(
        f"Domain accuracy: "
        f"{domain_accuracy:.2%}"
    )

    print(
        f"Work mode accuracy: "
        f"{work_mode_accuracy:.2%}"
    )

    print(
        f"Skills precision: "
        f"{skill_precision:.2%}"
    )

    print(
        f"Skills recall: "
        f"{skill_recall:.2%}"
    )


def main():
    api = TalentBaseAPI()

    try:
        with open(LABEL_FILE, "r", encoding="utf-8"):
            pass

        evaluate(api)

    except FileNotFoundError:
        select_candidates(api)


if __name__ == "__main__":
    main()