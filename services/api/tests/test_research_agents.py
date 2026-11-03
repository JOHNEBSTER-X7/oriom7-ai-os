import pytest
from pydantic import ValidationError
from research_agents import AgentRunRequest, ScheduleRequest


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
