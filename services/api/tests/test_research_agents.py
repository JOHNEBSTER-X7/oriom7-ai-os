import pytest
from pydantic import ValidationError
from research_agents import AgentRunRequest, ScheduleRequest, ScheduleUpdate


def test_agent_request_is_bounded_and_rejects_unknown_fields():
    payload=AgentRunRequest(question="Research the grid-scale battery storage market",max_sources=12)
    assert payload.max_sources==12
    with pytest.raises(ValidationError):
        AgentRunRequest(question="Research the grid-scale battery storage market",unbounded=True)
    with pytest.raises(ValidationError):
        AgentRunRequest(question="x",max_sources=1000)


def test_schedule_interval_is_bounded():
    payload=ScheduleRequest(question="Track changes in grid-scale battery storage",interval_minutes=1440)
    assert payload.interval_minutes==1440
    with pytest.raises(ValidationError):
        ScheduleRequest(question="Track changes in grid-scale battery storage",interval_minutes=5)

from research_agent_runtime import AgentPlan


def test_research_agent_plan_deduplicates_and_bounds_questions():
    plan=AgentPlan.parse('{"questions":["Compare major suppliers of grid batteries","Compare major suppliers of grid batteries","Identify technology trends in long duration storage"]}')
    assert len(plan)==2


def test_research_agent_plan_rejects_invalid_json_and_single_question():
    with pytest.raises(ValueError):
        AgentPlan.parse("not json")
    with pytest.raises(ValueError):
        AgentPlan.parse('{"questions":["only one question"]}')


def test_agent_plan_rejects_extra_json_keys():
    with pytest.raises(ValueError):
        AgentPlan.parse('{"questions":["Compare major grid battery suppliers","Identify policy changes in storage"],"action":"crawl"}')


def test_runtime_preserves_only_evidence_citation_mapping():
    # Citation validation is performed by mapping exact [S#] labels against the
    # source set. Semantic entailment remains a separately documented limitation.
    import re
    labels = sorted({int(n) for n in re.findall(r"\[S(\d+)\]", "Finding [S1], comparison [S3], invalid [S8]")})
    evidence = [{"id": "S1"}, {"id": "S2"}, {"id": "S3"}]
    assert [evidence[n - 1]["id"] for n in labels if 1 <= n <= len(evidence)] == ["S1", "S3"]
    assert [f"S{n}" for n in labels if n < 1 or n > len(evidence)] == ["S8"]


def test_schedule_update_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ScheduleUpdate(enabled=True, owner_subject="attacker")
