from pydantic import BaseModel


class URLStatusCounts(BaseModel):
    pending: int = 0
    submitted: int = 0
    analyzing: int = 0
    done: int = 0
    failed: int = 0


class StatsSummary(BaseModel):
    total_comments: int
    total_urls: int
    url_statuses: URLStatusCounts
    total_submissions: int
    completed_submissions: int
