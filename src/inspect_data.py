import re

from src.api import TalentBaseAPI
from src.utils import (
    normalize_name,
    normalize_email,
    normalize_email_local,
    normalize_phone
)



def find_groups(candidates, key_function):
    groups = {}

    for candidate in candidates:
        key = key_function(candidate)

        if key:
            groups.setdefault(key, []).append(candidate)

    return [
        group
        for group in groups.values()
        if len(group) > 1
    ]


def print_duplicate_group(group):
    print("-" * 60)

    for candidate in group:
        print(f"ID:    {candidate['id']}")
        print(f"Name:  {candidate['name']}")
        print(f"Email: {candidate['email']}")
        print(f"Phone: {candidate['phone']}")
        print(f"Title: {candidate['current_title']}")
        print()


def analyze_ambiguous_pairs(candidates):
    from itertools import combinations

    # Group candidates by normalized name
    name_groups = {}

    for candidate in candidates:
        name = normalize_name(candidate.get("name"))

        if name:
            name_groups.setdefault(name, []).append(candidate)

    strong_email_pairs = []
    strong_phone_pairs = []
    ambiguous_pairs = []
    name_only_pairs = []

    for group in name_groups.values():
        if len(group) < 2:
            continue

        for a, b in combinations(group, 2):
            same_email = (
                normalize_email(a.get("email"))
                == normalize_email(b.get("email"))
            )

            same_phone = (
                normalize_phone(a.get("phone"))
                == normalize_phone(b.get("phone"))
            )

            same_title = (
                normalize_name(a.get("current_title"))
                == normalize_name(b.get("current_title"))
            )

            pair = (a, b)

            if same_email:
                strong_email_pairs.append(pair)

            elif same_phone:
                strong_phone_pairs.append(pair)

            elif same_title:
                ambiguous_pairs.append(pair)

            else:
                name_only_pairs.append(pair)

    print("\n=== AMBIGUOUS DUPLICATE ANALYSIS ===")
    print(f"Same email + same name: {len(strong_email_pairs)}")
    print(f"Same phone + same name: {len(strong_phone_pairs)}")
    print(f"Same name + same title: {len(ambiguous_pairs)}")
    print(f"Same name only: {len(name_only_pairs)}")

    print("\nExample ambiguous pairs:")

    for a, b in ambiguous_pairs[:10]:
        print("-" * 60)

        print(
            f"{a['id']} | {a['name']} | "
            f"{a['email']} | {a['phone']} | {a['current_title']}"
        )

        print(
            f"{b['id']} | {b['name']} | "
            f"{b['email']} | {b['phone']} | {b['current_title']}"
        )

    return (
        strong_email_pairs,
        strong_phone_pairs,
        ambiguous_pairs,
        name_only_pairs,
    )



def main():
    api = TalentBaseAPI()

    print("Fetching candidates...")
    candidates = api.get_all_candidates()

    print(f"Total candidates: {len(candidates)}")


    # Basic missing-data analysis
    empty_resumes = []
    short_resumes = []
    missing_emails = []
    missing_phones = []
    missing_names = []

    for candidate in candidates:
        resume = (candidate.get("resume_text") or "").strip()

        if not resume:
            empty_resumes.append(candidate["id"])

        elif len(resume) < 100:
            short_resumes.append(candidate["id"])

        if not candidate.get("email"):
            missing_emails.append(candidate["id"])

        if not candidate.get("phone"):
            missing_phones.append(candidate["id"])

        if not candidate.get("name"):
            missing_names.append(candidate["id"])


    # Duplicate exact signals
    duplicate_email_groups = find_groups(
        candidates,
        lambda c: normalize_email(c.get("email"))
    )

    duplicate_phone_groups = find_groups(
        candidates,
        lambda c: normalize_phone(c.get("phone"))
    )

    duplicate_name_groups = find_groups(
        candidates,
        lambda c: normalize_name(c.get("name"))
    )


    # Suspicious prompt-injection-like content
    suspicious_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(the\s+)?approved\s+vocabulary",
        r"system\s+message",
        r"developer\s+message",
        r"assistant\s*:",
        r"user\s*:",
        r"you\s+are\s+now",
        r"follow\s+(these|the\s+following)\s+instructions",
        r"override",
        r"regardless\s+of\s+(the\s+)?resume",
    ]

    html_comment_pattern = r"<!--.*?-->"

    suspicious_candidates = []

    for candidate in candidates:
        resume = candidate.get("resume_text") or ""

        suspicious = False

        for pattern in suspicious_patterns:
            if re.search(pattern, resume, re.IGNORECASE | re.DOTALL):
                suspicious = True
                break

        if re.search(html_comment_pattern, resume, re.IGNORECASE | re.DOTALL):
            suspicious = True

        if suspicious:
            suspicious_candidates.append(candidate["resume_text"])


    print("\n=== DATA QUALITY ===")
    print(f"Empty resumes: {len(empty_resumes)}")
    print(f"Very short resumes (<100 chars): {len(short_resumes)}")
    print(f"Missing emails: {len(missing_emails)}")
    print(f"Missing phones: {len(missing_phones)}")
    print(f"Missing names: {len(missing_names)}")

    print("\n=== DUPLICATE SIGNALS ===")
    print(
        f"Exact duplicate email groups: "
        f"{len(duplicate_email_groups)}"
    )

    print(
        f"Exact duplicate phone groups: "
        f"{len(duplicate_phone_groups)}"
    )

    print(
        f"Exact duplicate name groups: "
        f"{len(duplicate_name_groups)}"
    )

    print("\n=== SUSPICIOUS CONTENT ===")
    print(
        f"Candidates containing suspicious "
        f"instruction-like text: {len(suspicious_candidates)}"
    )


    # Show examples
    if empty_resumes:
        print("\nExample empty resume:")
        print(empty_resumes[:10])

    if suspicious_candidates:
        print("\nExample suspicious candidate:")
        print(suspicious_candidates[0])

    if duplicate_email_groups:
        print("\n=== EXAMPLE EMAIL DUPLICATES ===")
        for group in duplicate_email_groups[:5]:
            print_duplicate_group(group)

    if duplicate_phone_groups:
        print("\n=== EXAMPLE PHONE DUPLICATES ===")
        for group in duplicate_phone_groups[:5]:
            print_duplicate_group(group)

    if duplicate_name_groups:
        print("\n=== EXAMPLE NAME DUPLICATES ===")
        for group in duplicate_name_groups[:5]:
            print_duplicate_group(group)       

    analyze_ambiguous_pairs(candidates)


if __name__ == "__main__":
    main()