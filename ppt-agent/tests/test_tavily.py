import pytest
from unittest.mock import patch
from ppt_agent.schemas.project import ProjectConfigPayload, ProjectResponse
from ppt_agent.services.project_service import ProjectService
from datetime import UTC, datetime


def make_project_response(project_id: str = "proj_test") -> ProjectResponse:
    return ProjectResponse(
        id=project_id,
        title="测试项目",
        topic="AI 运维平台介绍，重点突出监控和告警能力",
        status="draft",
        config=ProjectConfigPayload(
            scenario="汇报", audience="团队", style_pref="科技",
            research_enabled=True,
        ),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_fetch_search_results_returns_list(service: ProjectService):
    project = make_project_response()
    mock_result = {
        "results": [
            {"title": "AI 运维最佳实践", "url": "https://example.com/1", "content": "内容摘要1"},
            {"title": "监控系统选型", "url": "https://example.com/2", "content": "内容摘要2"},
        ]
    }
    with patch("ppt_agent.services.project_service.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_result
        results = service._fetch_tavily_results(project, api_key="fake-key")

    assert len(results) >= 2
    assert any(r["title"] == "AI 运维最佳实践" for r in results)


def test_fetch_search_results_skips_when_no_key(service: ProjectService):
    project = make_project_response()
    results = service._fetch_tavily_results(project, api_key=None)
    assert results == []


def test_build_research_prompt_includes_search_results(service: ProjectService):
    project = make_project_response()
    search_results = [
        {"title": "标题1", "url": "https://a.com", "content": "摘要1"},
    ]
    prompt = service._build_research_prompt(project, search_results=search_results)
    assert "标题1" in prompt
    assert "https://a.com" in prompt
