import json

from src.api import TalentBaseAPI
from src.llm import ResumeEnricher


def run_enrichment():
    api = TalentBaseAPI()

    print("Fetching taxonomy...")
    taxonomy = api.get("/taxonomy")

    print("Fetching candidates...")
    candidates = api.get_all_candidates()
    print(f"Fetched {len(candidates)} candidates.")

    service = ResumeEnricher(taxonomy)

    successful = 0
    failed = 0

    with open("output.jsonl", "w", encoding="utf-8") as f:

        for index, candidate in enumerate(candidates, start=1):
            candidate_id = candidate["id"]

            full_candidate = api.get_candidate(candidate_id)

            work_mode = full_candidate.get("work_mode")
            if work_mode not in taxonomy["work_mode"]:
                work_mode = "unknown"

            print(
                f"\n[{index}/{len(candidates)}] "
                f"{candidate_id} - {candidate.get('name')}"
            )

            resume = full_candidate.get("resume_text") or ""
            # Empty resume
            if not resume.strip():
                result = {
                    "skills": [],
                    "seniority": None,
                    "domain": None,
                    "confidence": 0.0,
                    "needs_review": True,
                }

                print("Empty resume -> needs_review=True")

            else:
                try:
                    result = service.enrich(resume)

                except Exception as e:
                    print(f"LLM failed: {e}")

                    result = {
                        "skills": [],
                        "seniority": None,
                        "domain": None,
                        "work_mode": work_mode,
                        "confidence": 0.0,
                        "needs_review": True,
                    }

            result["work_mode"] = work_mode

            # Save locally
            record = {
                "candidate_id": candidate_id,
                "enrichment": result,
            }

            try:
                api.update_enrichment(
                    candidate_id,
                    result
                )

                successful += 1

                print("API update: SUCCESS")

            except Exception as e:
                failed += 1

                print(f"API update: FAILED - {e}")

                record["api_update_failed"] = True
                record["error"] = str(e)

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("\n" + "=" * 60)
    print("ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"Total candidates: {len(candidates)}")
    print(f"Successfully updated: {successful}")
    print(f"Failed API updates: {failed}")


    print("\nVerifying Enrichment API write-back...")
    for candidate in candidates[:5]:
        candidate_id = candidate["id"]

        updated_candidate = api.get(f"/candidates/{candidate_id}")

        print(f"\n{candidate_id} - {updated_candidate.get('name')}")
        print(
            json.dumps(
                updated_candidate.get("enrichment"),
                indent=2,
                ensure_ascii=False
            )
        )

    return {
        "total": len(candidates),
        "successful": successful,
        "failed": failed,
    }



if __name__ == "__main__":
    run_enrichment()