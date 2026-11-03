from datetime import date

from knowledge_graph import (
    GraphRelationInput,
    rank_entity_match_candidates,
    temporal_ranges_overlap,
)


def test_entity_resolution_ranks_exact_alias_without_merging():
    candidates = [
        {"entity_id": "1", "entity_type": "organisation", "canonical_name": "Acme Holdings", "aliases": ["ACME"]},
        {"entity_id": "2", "entity_type": "organisation", "canonical_name": "Acorn Holdings", "aliases": []},
    ]
    ranked = rank_entity_match_candidates("Acme", candidates)
    assert ranked[0]["id"] == "1"
    assert ranked[0]["matched_aliases"] == ["ACME"]
    assert len(ranked) >= 1


def test_entity_resolution_does_not_suggest_dissimilar_records():
    assert rank_entity_match_candidates(
        "Acme", [{"entity_id": "2", "entity_type": "organisation", "canonical_name": "Northstar Mining", "aliases": []}]
    ) == []


def test_temporal_ranges_overlap_with_open_ended_bounds():
    assert temporal_ranges_overlap(date(2020, 1, 1), date(2022, 1, 1), date(2021, 1, 1), None)
    assert not temporal_ranges_overlap(date(2020, 1, 1), date(2020, 12, 31), date(2021, 1, 1), None)


def test_graph_relation_rejects_reversed_validity_range():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GraphRelationInput(
            subject_name="Acme Energy",
            subject_type="organisation",
            predicate="headquartered_in",
            object_name="Sheffield",
            object_type="location",
            evidence_excerpt="Acme Energy is headquartered in Sheffield according to this report.",
            confidence=0.9,
            valid_from="2025-01-01",
            valid_to="2024-01-01",
        )
