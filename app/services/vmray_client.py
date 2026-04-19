import httpx


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
        resp = await self._http.post(
            f"{self._base_url}/api/v2/sample/url",
            data={"sample_url": url},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_submission(self, submission_id: str) -> dict:
        resp = await self._http.get(
            f"{self._base_url}/api/v2/submission/{submission_id}",
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()
