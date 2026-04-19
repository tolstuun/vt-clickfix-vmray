from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass
class VTCommentData:
    comment_id: str
    author: str
    content: str
    published_at: datetime | None
    raw: dict


class VTClient:
    _BASE = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http = http_client

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def get_comments(
        self, cursor: str | None = None
    ) -> tuple[list[VTCommentData], str | None]:
        params: dict = {"limit": 40, "filter": "tag:clickfix"}
        if cursor:
            params["cursor"] = cursor
        resp = await self._http.get(
            f"{self._BASE}/comments",
            params=params,
            headers={"x-apikey": self._api_key},
        )
        resp.raise_for_status()
        body = resp.json()
        comments: list[VTCommentData] = []
        for item in body.get("data", []):
            attrs = item.get("attributes", {})
            raw_ts = attrs.get("date")
            published_at: datetime | None = None
            if raw_ts is not None:
                published_at = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)
            comments.append(
                VTCommentData(
                    comment_id=item["id"],
                    author=attrs.get("author", ""),
                    content=attrs.get("text", ""),
                    published_at=published_at,
                    raw=item,
                )
            )
        next_cursor: str | None = body.get("meta", {}).get("cursor")
        return comments, next_cursor
