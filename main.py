from src.api import TalentBaseAPI


def main():
    api = TalentBaseAPI()

    print("Health:")
    print(api.get_health())

    print("\nTaxonomy:")
    print(api.get_taxonomy())

    print("\nJobs:")
    print(api.get_jobs())

    print("\nFetching candidates...")
    candidates = api.get_all_candidates()

    print(f"Fetched {len(candidates)} candidates.")

    if candidates:
        print("\nFirst candidate:")
        print(candidates[0])


if __name__ == "__main__":
    main()