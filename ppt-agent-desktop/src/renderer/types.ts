export type ServiceStatus = {
  status: "ok" | "error" | "degraded" | "not_configured";
  detail: string;
};

export type HealthResponse = {
  app: string;
  environment: string;
  timestamp: string;
  storage_root: string;
  services: Record<string, ServiceStatus>;
};

export type ProjectConfig = {
  scenario: string;
  audience: string;
  style_pref: string;
  page_limit: number;
  research_enabled: boolean;
  narration_enabled: boolean;
};

export type Project = {
  id: string;
  title: string;
  topic: string;
  status: "draft" | "briefing" | "brief_confirmed" | "outline_ready";
  config: ProjectConfig;
  created_at: string;
  updated_at: string;
};

export type ProjectListResponse = {
  items: Project[];
};

export type BriefQuestion = {
  id: string;
  prompt: string;
  rationale: string;
  answer: string;
};

export type RequirementBrief = {
  project_id: string;
  version: number;
  goal: string;
  audience: string;
  tone: string;
  scenario: string;
  key_questions: BriefQuestion[];
  must_include: string[];
  forbidden: string[];
  research_summary: string;
  confirmed: boolean;
};

export type ResearchTopic = {
  name: string;
  summary: string;
  cluster: string;
  facts: string[];
  citations: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
};

export type ResearchPack = {
  project_id: string;
  version: number;
  summary: string;
  topics: ResearchTopic[];
};

export type SearchPage = {
  slide_id: string;
  order_no: number;
  title: string;
  section: string;
  key_message: string;
  summary: string;
  facts: string[];
  citations: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
};

export type SearchArtifact = {
  project_id: string;
  version: number;
  pages: SearchPage[];
};

export type OutlineSlide = {
  slide_id: string;
  order_no: number;
  section: string;
  title: string;
  type: string;
  key_message: string;
};

export type OutlineArtifact = {
  project_id: string;
  version: number;
  slides: OutlineSlide[];
};

export type SlidePlanBlock = {
  block_id: string;
  kind: string;
  title: string;
  content: string;
  words_budget: number;
  emphasis: "high" | "medium" | "low";
};

export type SlidePlanPage = {
  slide_id: string;
  order_no: number;
  title: string;
  narrative_role: string;
  core_message: string;
  visual_focus: string;
  suggested_layout: string;
  design_notes: string[];
  blocks: SlidePlanBlock[];
};

export type SlidePlanArtifact = {
  project_id: string;
  version: number;
  pages: SlidePlanPage[];
};

export type SvgSlidePage = {
  slide_id: string;
  order_no: number;
  title: string;
  svg: string;
};

export type SvgSlideArtifact = {
  project_id: string;
  version: number;
  pages: SvgSlidePage[];
};
