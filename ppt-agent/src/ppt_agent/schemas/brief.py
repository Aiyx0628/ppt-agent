from pydantic import BaseModel, Field


class BriefQuestion(BaseModel):
    id: str
    prompt: str
    rationale: str
    answer: str = ""


class RequirementBrief(BaseModel):
    project_id: str
    version: int
    goal: str
    audience: str
    tone: str
    scenario: str
    key_questions: list[BriefQuestion]
    must_include: list[str]
    forbidden: list[str]
    research_summary: str
    confirmed: bool = False


class BriefUpdateRequest(BaseModel):
    goal: str | None = Field(default=None, min_length=3, max_length=300)
    tone: str | None = Field(default=None, min_length=2, max_length=80)
    must_include: list[str] | None = None
    forbidden: list[str] | None = None
    key_questions: list[BriefQuestion] | None = None


class BriefConfirmResponse(BaseModel):
    project_id: str
    confirmed: bool
