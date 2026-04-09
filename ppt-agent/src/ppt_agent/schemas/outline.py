from pydantic import BaseModel, Field


class OutlineSlide(BaseModel):
    slide_id: str
    order_no: int = Field(ge=1)
    section: str
    title: str
    type: str
    key_message: str


class OutlineArtifact(BaseModel):
    project_id: str
    version: int
    slides: list[OutlineSlide]


class OutlineReorderRequest(BaseModel):
    slide_ids: list[str] = Field(min_length=1)
