import httpx

# VMRay Cloud API Reference v2026.2.1
# Submit:      POST /rest/sample/submit  (form field: sample_url)
# Get submission: GET /rest/submission/<submission_id>
# Auth header: "Authorization: api_key <key>"


class VMRayClient:
    def __init__(self, base_url: str, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http_client

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url and self._api_key)

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"api_key {self._api_key}"}

    async def submit_url(self, url: str) -> dict:
        """POST /rest/sample/submit with form field sample_url.

        Response schema (SampleSubmit):
          { "result": "ok",
            "data": { "submissions": [{"submission_id": <int>, ...}], ... } }
        """
        resp = await self._http.post(
            f"{self._base_url}/rest/sample/submit",
            data={"sample_url": url},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_submission(self, submission_id: str) -> dict:
        """GET /rest/submission/<submission_id>.

        Response schema (SubmissionItem):
          { "result": "ok",
            "data": { "submission_id": <int>,
                      "submission_finished": <bool>,
                      "submission_verdict": <"malicious"|"suspicious"|"clean"|null>,
                      "submission_score": <int|null>,
                      ... } }
        """
        resp = await self._http.get(
            f"{self._base_url}/rest/submission/{submission_id}",
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()
