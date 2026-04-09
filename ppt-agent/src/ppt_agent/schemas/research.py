from pydantic import BaseModel


class ResearchCitation(BaseModel):
    title: str
    url: str
    snippet: str


class ResearchTopic(BaseModel):
    name: str
    summary: str
    cluster: str
    facts: list[str]
    citations: list[ResearchCitation]


class ResearchPack(BaseModel):
    project_id: str
    version: int
    summary: str
    topics: list[ResearchTopic]
