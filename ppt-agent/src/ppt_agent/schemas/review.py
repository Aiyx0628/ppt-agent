from typing import Literal
from pydantic import BaseModel


class ReviewIssue(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    detail: str


class ReviewPage(BaseModel):
    slide_id: str
    order_no: int
    issues: list[ReviewIssue]
    passed: bool


class ReviewArtifact(BaseModel):
    project_id: str
    version: int
    pages: list[ReviewPage]
