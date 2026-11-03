import pytest
from pydantic import ValidationError

from knowledge_extraction import (
    ExtractionError,
    _parse_candidate_payload,
    filter_verbatim_relations,
)
from knowledge_graph import KnowledgeObservationRequest


def candidate_payload(excerpt):
    return KnowledgeObservationRequest.model_validate({
        "evidence_document_id": "00000000-0000-0000-0000-000000000001",
        "entities": [
            {"name": "Acme Energy", "entity_type": "organisation"},
            {"name": "Battery One", "entity_type": "product"},
        ],
        "relations": [{
            "subject_name": "Acme Energy",
            "subject_type": "organisation",
            "predicate": "manufactures",
            "object_name": "Battery One",
            "object_type": "product",
            "evidence_excerpt": excerpt,
            "confidence": 0.88,
        }],
    })


def test_parser_accepts_only_expected_json_shape():
    parsed = _parse_candidate_payload('{"entities":[],"relations":[]}')
    assert parsed == {"entities": [], "relations": []}


@pytest.mark.parametrize("value", [
    "not json",
    '{"entities":[],"relations":[],"accepted":true}',
    '{"entities":{},"relations":[]}',
])
def test_parser_rejects_invalid_or_unexpected_model_output(value):
    with pytest.raises(ExtractionError):
        _parse_candidate_payload(value)


def test_only_exact_source_excerpt_is_retained():
    exact = "Acme Energy manufactures Battery One at its Sheffield facility."
    payload = candidate_payload(exact)
    assert len(filter_verbatim_relations(payload, "Report: " + exact + " Further details.")) == 1


def test_paraphrased_or_invented_excerpt_is_rejected():
    payload = candidate_payload(
        "Acme Energy makes Battery One at its Sheffield manufacturing facility."
    )
    assert filter_verbatim_relations(
        payload,
        "Acme Energy manufactures Battery One at its Sheffield facility.",
    ) == []


def test_extraction_output_cannot_link_missing_entities():
    with pytest.raises(ValidationError):
        KnowledgeObservationRequest.model_validate({
            "evidence_document_id": "00000000-0000-0000-0000-000000000001",
            "entities": [{"name": "Acme Energy", "entity_type": "organisation"}],
            "relations": [{
                "subject_name": "Acme Energy",
                "subject_type": "organisation",
                "predicate": "manufactures",
                "object_name": "Battery One",
                "object_type": "product",
                "evidence_excerpt": "Acme Energy manufactures Battery One at its Sheffield facility.",
                "confidence": 0.88,
            }],
        })
