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
