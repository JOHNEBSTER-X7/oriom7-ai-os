import pytest
from pydantic import ValidationError

from research_agents import AgentPlan, AgentRunRequest


def test_agent_plan_requires_two_distinct_search_questions():
    questions = AgentPlan.parse('{"questions":["Compare current battery storage technologies","Compare current battery storage technologies","Identify major grid-scale suppliers"]}')
    assert len(questions) == 2


def test_agent_plan_rejects_invalid_or_underspecified_output():
    with pytest.raises(ValueError):
        AgentPlan.parse('{"questions":["only one useful question"]}')
    with pytest.raises(ValueError):
        AgentPlan.parse('not json')


def test_agent_run_request_is_bounded_and_rejects_unknown_fields():
    payload = AgentRunRequest(question="Research the grid-scale battery storage market", max_sources=12)
    assert payload.max_sources == 12
    with pytest.raises(ValidationError):
        AgentRunRequest(question="Research the grid-scale battery storage market", unbounded=True)
