import type {
  HealthResponse,
  OutlineArtifact,
  Project,
  ProjectConfig,
  ProjectListResponse,
  ResearchPack,
  RequirementBrief,
  SearchArtifact,
  SlidePlanArtifact,
  SvgSlideArtifact,
} from "../types";

const apiBaseUrl = window.deckflow.getRuntimeInfo().apiBaseUrl;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => window.deckflow.pingBackend() as Promise<HealthResponse>,
  listProjects: async () => {
    const payload = await request<ProjectListResponse>("/api/projects");
    return payload.items;
  },
  createProject: (payload: {
    title: string;
    topic: string;
    config: ProjectConfig;
  }) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  intakeProject: (prompt: string, files: File[]) => {
    const formData = new FormData();
    formData.set("prompt", prompt);
    files.forEach((file) => formData.append("files", file));
    return request<Project>("/api/projects/intake", {
      method: "POST",
      body: formData,
    });
  },
  getProject: (projectId: string) =>
    request<Project>(`/api/projects/${projectId}`),
  runResearch: (projectId: string) =>
    request<ResearchPack>(`/api/projects/${projectId}/research/run`, {
      method: "POST",
    }),
  getResearch: (projectId: string) =>
    request<ResearchPack>(`/api/projects/${projectId}/research`),
  getSearchPages: (projectId: string) =>
    request<SearchArtifact>(`/api/projects/${projectId}/search`),
  generateSearchPages: (projectId: string) =>
    request<SearchArtifact>(`/api/projects/${projectId}/search/generate`, {
      method: "POST",
    }),
  getBrief: (projectId: string) =>
    request<RequirementBrief>(`/api/projects/${projectId}/brief`),
  generateBrief: (projectId: string) =>
    request<RequirementBrief>(`/api/projects/${projectId}/brief/generate`, {
      method: "POST",
    }),
  confirmBrief: (projectId: string) =>
    request<{ project_id: string; confirmed: boolean }>(
      `/api/projects/${projectId}/brief/confirm`,
      { method: "POST" }
    ),
  getOutline: (projectId: string) =>
    request<OutlineArtifact>(`/api/projects/${projectId}/outline`),
  generateOutline: (projectId: string) =>
    request<OutlineArtifact>(`/api/projects/${projectId}/outline/generate`, {
      method: "POST",
    }),
  getSlidePlan: (projectId: string) =>
    request<SlidePlanArtifact>(`/api/projects/${projectId}/slide-plan`),
  generateSlidePlan: (projectId: string) =>
    request<SlidePlanArtifact>(`/api/projects/${projectId}/slide-plan/generate`, {
      method: "POST",
    }),
  getSvg: (projectId: string) =>
    request<SvgSlideArtifact>(`/api/projects/${projectId}/svg`),
  generateSvg: (projectId: string) =>
    request<SvgSlideArtifact>(`/api/projects/${projectId}/svg/generate`, {
      method: "POST",
    }),
  reorderOutline: (projectId: string, slideIds: string[]) =>
    request<OutlineArtifact>(`/api/projects/${projectId}/outline/reorder`, {
      method: "POST",
      body: JSON.stringify({ slide_ids: slideIds }),
    }),
};
