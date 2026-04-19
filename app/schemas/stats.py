from datetime import datetime

from pydantic import BaseModel


class URLStatusCounts(BaseModel):
    pending: int = 0
    submitted: int = 0
    analyzing: int = 0
    done: int = 0
    failed: int = 0


class VerdictCounts(BaseModel):
    malicious: int = 0
    suspicious: int = 0
    clean: int = 0
    unknown: int = 0


class TopDomain(BaseModel):
    domain: str
    count: int


class StatsSummary(BaseModel):
    total_comments: int
    total_urls: int
    total_unique_normalized_urls: int
    url_statuses: URLStatusCounts
    total_submissions: int
    completed_submissions: int
    verdict_counts: VerdictCounts
    top_domains: list[TopDomain]
    latest_comment_at: datetime | None
    latest_url_at: datetime | None
    latest_submission_at: datetime | None
