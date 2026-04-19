from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

# VirusTotal API v3 — Comments endpoint
# GET /api/v3/comments
# Auth header: "x-apikey: <key>"
#
# filter=tag:clickfix is a TAG-BASED filter, not full-text search.
# It returns only comments that VT users have explicitly tagged with "clickfix".
# Comments that mention "clickfix" in their text but have no such tag will NOT
# be returned by this filter.
#
# Documented comment attributes: votes, tags, text, html, date (unix timestamp).
# There is no "author" field in the documented API response; it is always stored
# as empty string.


@dataclass
class VTCommentData:
    comment_id: str
    author: str  # not in documented API; always ""
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
        """GET /api/v3/comments with filter=tag:clickfix.

        Pagination cursor comes from meta.cursor in the response.

        Response structure:
          { "data": [{ "type": "comment", "id": "<id>",
                       "attributes": { "text": str, "date": int,
                                       "tags": [...], "votes": {...} },
                       "links": { "self": str } }],
            "meta": { "cursor": str | null },
            "links": { "self": str, "next": str } }
        """
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
                    author="",  # not in documented API response
                    content=attrs.get("text", ""),
                    published_at=published_at,
                    raw=item,
                )
            )
        next_cursor: str | None = body.get("meta", {}).get("cursor")
        return comments, next_cursor
