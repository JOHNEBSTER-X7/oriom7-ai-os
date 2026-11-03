# ORIOM7 Graph-Aware AI Research Assistant

## Overview

The assistant can now supplement hybrid search with accepted knowledge-graph assertions. It resolves explicit entity-name or alias mentions in the user's question, then retrieves a bounded set of accepted relationships connected to those entities. Graph evidence is supplied to the configured model as untrusted context and remains distinct from ordinary search results.

## Evidence and citation rules

- Only `accepted` assertions are eligible.
- Every assertion is joined to a currently indexed, non-deleted source with a non-empty rights basis and an allowed/not-applicable robots status.
- Each graph citation uses its own `[G1]`, `[G2]` namespace; ordinary search citations remain `[S1]`, `[S2]`.
- Returned graph citation metadata includes the source title, canonical URL, document ID, excerpt, provider and retrieval/publication dates.
- The API maps model-cited graph labels back to retrieved evidence and reports invalid graph references separately.
- Entity matching is deterministic name/alias substring matching, not identity verification. Similarity candidates must not be treated as proof that two entities are the same.
- Unverified assertions never enter assistant context.

## Relationships, paths and inconsistencies

The first integration retrieves direct accepted assertions connected to matched entities, bounded to 12 entity matches and 40 assertions. It does not yet perform open-ended multi-hop traversal in the response path. Existing bounded graph-path APIs remain available for explicit graph exploration.

Where retrieved assertions for the same subject and predicate have different objects and overlapping or unknown validity ranges, the assistant context may flag a **potential inconsistency requiring human assessment**. This is not a verified contradiction. Source scope, context, dates and predicate semantics still require review.

A connected graph path does not establish causation, entailment or transitive truth. The assistant is instructed to distinguish source statements from graph-derived connections and to preserve uncertainty.

## API response

`POST /v1/assistant/responses` retains its existing search-grounding response and adds:

- `grounding.knowledge_graph.status`
- `grounding.knowledge_graph.matched_entities`
- `grounding.knowledge_graph.assertion_count`
- `grounding.knowledge_graph.potential_inconsistencies`
- `grounding.knowledge_graph.citations`
- `grounding.knowledge_graph.invalid_references`
- `grounding.knowledge_graph.interpretation`

When no database/graph is configured, the assistant continues to use the existing retrieval path and reports no graph assertions. When the graph query itself fails while a database is configured, the request fails closed with a service-unavailable response rather than silently implying graph coverage.

## Limitations and next steps

This is a first graph-aware assistant integration, not a full research agent. Entity extraction from free-form questions is deliberately conservative; there is no LLM entity linking, automatic entity merging, claim-entailment checking, graph-wide contradiction detection, graph visualisation, or automated multi-hop proof. Search and graph evidence are provenance-linked, but citation label validity does not prove that a source semantically supports every generated claim. Human review remains mandatory for consequential conclusions.
