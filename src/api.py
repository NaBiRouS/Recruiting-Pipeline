import time
import requests

from config import BASE_URL, HEADERS


class TalentBaseAPI:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS

    def get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"

        while True:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

    def get_health(self):
        return self.get("/health")

    def get_taxonomy(self):
        return self.get("/taxonomy")

    def get_jobs(self):
        return self.get("/jobs")

    def get_candidate(self, candidate_id):
        return self.get(f"/candidates/{candidate_id}")
    
    def get_candidate_page(self, page, per_page=100):
        return self.get(
            "/candidates",
            params={
                "page": page,
                "per_page": per_page,
            },
        )

    def get_all_candidates(self):
        first_page = self.get_candidate_page(1, 100)

        candidates = first_page["candidates"]
        total_pages = first_page["total_pages"]

        for page in range(2, total_pages + 1):
            data = self.get_candidate_page(page, 100)
            candidates.extend(data["candidates"])

        return candidates

    def update_enrichment(self, candidate_id, enrichment):
        url = f"{self.base_url}/candidates/{candidate_id}/enrichment"

        while True:
            response = requests.patch(
                url,
                headers=self.headers,
                json=enrichment,
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

    def submit_matches(self, job_id, matches):
        url = f"{self.base_url}/jobs/{job_id}/matches"

        while True:
            response = requests.post(
                url,
                headers=self.headers,
                json={"matches": matches},
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()