import pytest
from pydantic import ValidationError

from knowledge_graph import (
    GraphEntityInput,
    GraphRelationInput,
    KnowledgeObservationRequest,
    normalise_name,
)


def test_normalise_name_handles_unicode_and_spacing():
    assert normalise_name("  STRAẞE   Energy ") == "strasse energy"
    assert normalise_name("ＡＣＭＥ") == "acme"


def test_relation_requires_normalised_distinct_endpoints():
    with pytest.raises(ValidationError):
        GraphRelationInput(
            subject_name="Acme",
            subject_type="organisation",
            predicate="owns",
            object_name=" ACME ",
            object_type="organisation",
            evidence_excerpt="The source describes the organisation as its own owner.",
            confidence=0.8,
        )


def test_observation_requires_every_relation_endpoint_in_entity_batch():
    request = {
        "evidence_document_id": "00000000-0000-0000-0000-000000000001",
        "entities": [
            {"name": "Acme", "entity_type": "organisation"},
            {"name": "Battery One", "entity_type": "product"},
        ],
        "relations": [{
            "subject_name": "Acme",
            "subject_type": "organisation",
            "predicate": "manufactures",
            "object_name": "Battery Two",
            "object_type": "product",
            "evidence_excerpt": "Acme manufactures Battery Two according to the report.",
            "confidence": 0.91,
        }],
    }
    with pytest.raises(ValidationError):
        KnowledgeObservationRequest.model_validate(request)


def test_graph_entity_aliases_are_normalised_and_deduplicated():
    entity = GraphEntityInput(
        name="Acme Energy",
        entity_type="organisation",
        aliases=["ACME", " ACME ", "Acme Energy Group"],
    )
    assert entity.aliases == ["ACME", "Acme Energy Group"]
