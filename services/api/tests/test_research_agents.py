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
