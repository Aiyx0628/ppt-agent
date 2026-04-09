from pydantic import BaseModel, Field


class SlidePlanBlock(BaseModel):
    block_id: str
    kind: str
    title: str
    content: str
    words_budget: int = Field(ge=0, le=400)
    emphasis: str


class SlidePlanPage(BaseModel):
    slide_id: str
    order_no: int = Field(ge=1)
    title: str
    narrative_role: str
    core_message: str
    visual_focus: str
    suggested_layout: str
    design_notes: list[str]
    blocks: list[SlidePlanBlock]


class SlidePlanArtifact(BaseModel):
    project_id: str
    version: int
    pages: list[SlidePlanPage]
