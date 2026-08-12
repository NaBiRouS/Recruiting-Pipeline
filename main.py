from src.enrichment import run_enrichment
from src.deduplicate import run_deduplication
from src.matcher import run_matching


def main():
    print("=" * 60)
    print("STARTING PIPELINE")
    print("=" * 60)

    print("\n[TASK 1/3] ENRICHMENT")
    enrichment_result = run_enrichment()

    print("\n[TASK 2/3] DEDUPLICATION")
    deduplication_result = run_deduplication()

    print("\n[TASK 3/3] MATCHING")
    matching_result = run_matching()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    print("\nSummary:")
    print(
        f"Enrichment: "
        f"{enrichment_result['successful']} updated, "
        f"{enrichment_result['failed']} failed"
    )

    print(
        f"Deduplication: "
        f"{deduplication_result['duplicates_found']} duplicates, "
        f"{deduplication_result['updated']} API updates, "
        f"{deduplication_result['failed']} failed"
    )

    print(
        f"Matching: "
        f"{matching_result['submitted']} candidates submitted "
        f"for {matching_result['job_id']} - "
        f"{matching_result['job_title']}"
    )



if __name__ == "__main__":
    main()