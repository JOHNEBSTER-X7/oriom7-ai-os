# ORIOM7 Adaptive Evidence and Compute Controller — Research Plan

**Classification:** proposed R&D; not yet implemented or validated.  
**Existing baseline:** durable research worker, provider-neutral model orchestration, hybrid lexical/optional vector retrieval, source-label citation mapping and human-reviewed knowledge-graph assertions.

## 1. Why this is research

ORIOM7 currently executes a fixed sequence: generate a research plan, retrieve evidence for each sub-question, then synthesise an answer. The stages are role prompts within one worker process and share the configured model orchestrator. They are not independent agent runtimes.

The research question is whether a learned controller can improve the choice and timing of evidence and verification actions under explicit quality and compute constraints. Simply inserting a neural network or renaming the stages is not sufficient novelty.

## 2. Research environment and monorepo fit

Keep the current monorepo and product interfaces. Add the research system as a bounded module, with offline training and evaluation separated from production request handling.

Proposed organisation (paths are proposals until implemented):

```text
oriom7-ai-os/
├── contracts/
│   └── research-controller/       # Versioned state/action/trace schemas
├── services/api/
│   ├── research_agents.py         # Existing authenticated job API; retain
│   ├── research_agent_runtime.py  # Existing sequential baseline; retain
│   └── adaptive_research/         # New controller adapter; feature-flagged
├── research/
│   └── adaptive_controller/
│       ├── data/                  # Dataset cards and split manifests; no secrets
│       ├── experiments/           # Versioned configurations
│       ├── models/                # Model metadata/checksums, not private data
│       ├── evaluation/            # Metrics, confidence intervals, ablations
│       └── reports/               # Reproducible experiment outputs
└── packages/accessibility-engine/ # Existing package; invariant tests only
```

The research package must not replace the API entrypoint or alter the current worker's default behaviour until validated.

## 3. State, actions and outcomes

Candidate state features, subject to ablation and leakage analysis:
- query/task category and complexity indicators;
- number and diversity of retrieved sources;
- retrieval rank and score distributions;
- evidence freshness and source-quality indicators where available;
- claim-to-evidence support estimates from a separately validated verifier;
- disagreement/contradiction indicators;
- calibrated uncertainty estimates;
- remaining latency and monetary/compute budget.

Candidate actions:
- retrieve another lexical batch;
- retrieve another semantic batch (only when configured);
- broaden or reformulate a query;
- fetch or chunk a permitted source;
- invoke a separately validated claim-evidence verifier;
- ask for human review;
- stop and synthesise with explicit limitations.

The action space must only expose operations that are implemented, permitted by source rights and bounded by policy. Do not treat arbitrary external URLs or model-generated tool calls as authorised actions.

## 4. Policy candidates

Evaluate at least:
1. fixed top-k retrieval;
2. BM25-only;
3. hybrid lexical/vector retrieval with reciprocal-rank fusion;
4. current fixed sequential research workflow;
5. static uncertainty/threshold stopping policy;
6. a contextual-bandit policy;
7. a sequential policy (for example, a constrained MDP or actor-critic approach) only if the dataset and sample size support it.

Do not preselect actor-critic as the answer. The experiment must be allowed to show that a simpler contextual policy is better, safer or more reproducible.

## 5. Reward and constraints

Define a multi-objective reward before training. It must balance:
- claim-level evidence support and citation correctness;
- answer coverage and task success;
- compute expenditure and end-to-end latency;
- unsupported-claim rate and critical error penalties;
- abstention/human-review behaviour when evidence is insufficient.

Hard constraints:
- no reward for unsupported claims;
- no synthetic citation IDs or simulated evidence updates;
- no improvement claim based only on model confidence;
- no budget overrun;
- preserve source permissions, privacy and user authorisation;
- preserve canonical answer meaning and citations under accessibility transformations.

All reward components, normalisation, weights and constraint thresholds must be versioned and justified. Report Pareto trade-offs rather than hiding quality regressions behind one aggregate score.

## 6. Evaluation design

Create a fixed, documented corpus with:
- training, validation and held-out test splits;
- source provenance, licence/rights basis and permitted processing;
- task taxonomy and language coverage;
- gold evidence passages and claim-support labels where feasible;
- hard cases: conflicting sources, stale sources, missing evidence, adversarial snippets, provider outages and ambiguous queries.

Prevent train/test leakage by grouping related documents, source domains and near-duplicate questions across splits.

Primary measures:
- claim-level precision/recall and citation-to-passage support;
- unsupported-claim rate;
- task completion/coverage;
- calibration error and selective risk;
- compute cost per supported claim;
- end-to-end latency;
- abstention and human-review rate.

Report confidence intervals, sample sizes, effect sizes and per-category/per-language breakdowns. A single aggregate score is insufficient.

## 7. Pre-registered hypotheses and gates

Candidate targets (to be finalised after baseline variance and sample-size analysis):
- improve evidence-supported claim precision at a matched compute budget;
- reduce compute per supported claim at a matched quality level;
- maintain or reduce unsupported-claim rate;
- improve calibration or selective-risk behaviour;
- demonstrate reproducible results across at least three pre-defined task categories.

No numeric target should be represented as achieved until measured on the held-out test set. Set minimum detectable effects and sample size before running the final experiment.

## 8. Ablations and negative controls

Required ablations:
- remove uncertainty features;
- remove source-diversity features;
- remove cost/budget features;
- remove contradiction/disagreement features;
- disable learned stopping;
- compare learned policy to a parameter-matched static policy.

Negative controls:
- shuffled evidence labels;
- random policy;
- deliberately stale or irrelevant evidence;
- duplicated evidence;
- no-evidence and provider-failure conditions;
- permuted task labels.

Ablations should isolate which features drive gains; negative controls should detect leakage, evaluation artefacts and false confidence.

## 9. Accessibility preservation tests

The accessibility engine remains a separate, deterministic presentation layer. Test that transformations preserve:
- all source references and citation targets;
- uncertainty and qualification language;
- safety warnings and material limitations;
- numerical values, dates and named entities;
- the distinction between verified evidence, model-generated synthesis and human-reviewed assertions.

Test screen-reader output, keyboard navigation, text scaling, contrast and reduced-motion behaviour with appropriate assistive technology and user testing. Automated checks do not establish WCAG conformance.

## 10. Reproducibility and governance

Every experiment records:
- Git commit SHA and clean/dirty status;
- configuration and random seeds;
- dataset version and checksums;
- model/provider/version and relevant inference settings;
- hardware/runtime and cost measurement method;
- evaluation code version;
- failed runs and exclusions with reasons.

Keep personal data and licensed corpus content out of Git. Store only synthetic/sample fixtures or approved metadata in the repository. Restrict model artefacts and dataset access according to licence and privacy requirements.

## 11. Acceptance criteria before production integration

- Baselines run end-to-end from a documented command.
- Dataset provenance and rights review are complete.
- The controller beats the pre-registered baseline on held-out data with uncertainty intervals reported.
- No material regression in unsupported-claim rate or critical safety behaviour.
- Budget and latency constraints are respected.
- Ablations and negative controls behave as expected.
- Accessibility preservation tests pass.
- Model card, limitations and reproducibility report are reviewed.
- Feature-flagged integration can be disabled without disrupting existing research jobs.

Until these gates are met, the current research worker remains the production path and the controller remains experimental.
