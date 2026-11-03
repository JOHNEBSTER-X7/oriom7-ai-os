import asyncio
from datetime import datetime, timezone

from graph_research import format_graph_context, retrieve_graph_context


class FakeConnection:
    def __init__(self):
        self.calls = 0

    async def fetch(self, query, *args):
        self.calls += 1
        if self.calls == 1:
            return [
                {"id": "entity-1", "type": "organisation", "name": "Acme Energy"},
                {"id": "entity-2", "type": "technology", "name": "Grid Storage"},
            ]
        return [{
            "assertion_id": "assertion-1", "predicate": "develops",
            "evidence_excerpt": "Acme Energy develops Grid Storage for utility-scale projects.",
            "confidence": 0.95, "valid_from": None, "valid_to": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "subject_id": "entity-1", "subject_name": "Acme Energy",
            "subject_type": "organisation", "object_id": "entity-2",
            "object_name": "Grid Storage", "object_type": "technology",
            "document_id": "doc-1", "title": "Acme project report",
            "canonical_url": "https://example.org/report", "provider": "oriom7_index",
            "fetched_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "published_at": None,
        }]


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, *args):
        return False


class FakePool:
    def __init__(self):
        self.connection = FakeConnection()

    def acquire(self):
        return FakeAcquire(self.connection)


def test_graph_context_uses_only_accepted_evidence_and_returns_provenance():
    pool = FakePool()
    result = asyncio.run(retrieve_graph_context(pool, "How does Acme Energy use Grid Storage?"))
    assert [item["name"] for item in result["entities"]] == ["Acme Energy", "Grid Storage"]
    assert result["assertions"][0]["predicate"] == "develops"
    assert result["assertions"][0]["evidence"]["url"] == "https://example.org/report"
    assert result["potential_inconsistencies"] == []


def test_graph_context_skips_database_for_queries_without_entity_terms():
    result = asyncio.run(retrieve_graph_context(None, "!!!"))
    assert result == {"entities": [], "assertions": [], "potential_inconsistencies": []}


def test_graph_context_format_uses_separate_stable_citation_namespace():
    graph = {
        "assertions": [{
            "assertion_id": "a1",
            "subject": {"name": "Acme Energy"},
            "predicate": "develops",
            "object": {"name": "Grid Storage"},
            "evidence": {
                "document_id": "doc-1", "title": "Project report",
                "url": "https://example.org/report",
                "excerpt": "Acme Energy develops Grid Storage for utility-scale projects.",
                "provider": "oriom7_index",
                "retrieved_at": "2026-01-02T00:00:00+00:00",
                "published_at": None,
            },
            "valid_from": None, "valid_to": None,
        }],
        "potential_inconsistencies": [],
    }
    block, sources = format_graph_context(graph)
    assert "[G1]" in block
    assert sources[0]["id"] == "G1"
    assert "[" not in sources[0]["id"]
    assert "not independent proof of causation" in block
