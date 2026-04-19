import uuid
from datetime import datetime

from pydantic import BaseModel


class VMRaySubmissionOut(BaseModel):
    id: uuid.UUID
    submission_id: str | None
    verdict: str | None
    score: int | None
    severity: str | None
    submission_status: str | None
    report_url: str | None
    submitted_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class URLOut(BaseModel):
    id: uuid.UUID
    normalized_url: str
    domain: str | None
    status: str
    verdict: str | None = None
    score: int | None = None
    report_url: str | None = None
    created_at: datetime
    updated_at: datetime
    submission: VMRaySubmissionOut | None = None

    model_config = {"from_attributes": True}


class VTCommentRef(BaseModel):
    id: uuid.UUID
    comment_id: str
    content: str
    published_at: datetime | None

    model_config = {"from_attributes": True}


class URLDetailOut(BaseModel):
    id: uuid.UUID
    original_defanged: str
    normalized_url: str
    domain: str | None
    scheme: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    source_comment: VTCommentRef | None = None
    submission: VMRaySubmissionOut | None = None

    model_config = {"from_attributes": True}


class URLListResponse(BaseModel):
    items: list[URLOut]
    total: int
    page: int
    page_size: int
