from pydantic import BaseModel, Field


class SvgSlidePage(BaseModel):
    slide_id: str
    order_no: int = Field(ge=1)
    title: str
    svg: str


class SvgSlideArtifact(BaseModel):
    project_id: str
    version: int
    pages: list[SvgSlidePage]
