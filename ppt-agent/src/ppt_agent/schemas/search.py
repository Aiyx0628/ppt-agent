from pydantic import BaseModel, Field


class SearchCitation(BaseModel):
    title: str
    url: str
    snippet: str


class SearchPage(BaseModel):
    slide_id: str
    order_no: int = Field(ge=1)
    title: str
    section: str
    key_message: str
    summary: str
    facts: list[str]
    citations: list[SearchCitation]


class SearchArtifact(BaseModel):
    project_id: str
    version: int
    pages: list[SearchPage]
