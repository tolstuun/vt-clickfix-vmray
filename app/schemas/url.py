import uuid
from datetime import datetime

from pydantic import BaseModel


class VMRaySubmissionOut(BaseModel):
    id: uuid.UUID
    submission_id: str | None
    verdict: str | None
    score: int | None
    submitted_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class URLOut(BaseModel):
    id: uuid.UUID
    url_hash: str
    original_defanged: str
    normalized_url: str
    vt_comment_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime
    submission: VMRaySubmissionOut | None = None

    model_config = {"from_attributes": True}


class URLListResponse(BaseModel):
    items: list[URLOut]
    total: int
    page: int
    page_size: int
