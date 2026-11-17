# Draft Application Content — Efficient, Structured and Controllable AI Systems

**Applicant:** LIFE AFTER CRISIS GLOBAL ORGANISATION COMMUNITY INTEREST COMPANY (proposed; eligibility not yet cleared)  
**Project title:** Learning to Allocate Evidence and Computation for Reliable AI Research  
**Proposed theme:** Theme 1 — Resource and data adaptive learning  
**Proposed priority:** Active and probabilistic learning  
**Status:** working narrative only. Not submitted. Financial, company, SME, IP, TRL and board information remains incomplete.

> Submission warning: the competition closes 18 November 2026 at 11:00 UK time. Do not submit unless all mandatory applicant, technical and financial evidence is complete and accurate. No information has been invented to fill missing company or budget details.

## A. Project summary — draft (within 400 words)

ORIOM7 is developing an evidence-grounded AI research platform. Its current research workflow uses a fixed sequence of planning, evidence retrieval and synthesis. This provides a reproducible baseline, but it does not learn which evidence-acquisition or verification action is most valuable for a particular research task, nor when further retrieval is no longer worth its compute cost.

This project will investigate and experimentally validate an uncertainty-aware learning mechanism that selects the next evidence action under explicit quality, latency and compute constraints. Candidate actions include retrieving another lexical or semantic batch, broadening a query, fetching a permitted source, invoking a validated evidence-checking operation, requesting human review, or stopping and synthesising with stated limitations. The mechanism will be constrained to authorised, rights-compliant actions.

The central hypothesis is that a learned policy conditioned on task state, evidence diversity, uncertainty, disagreement and remaining resource budget can improve evidence-supported answer quality or reduce compute per supported claim compared with fixed retrieval and stopping policies, without increasing unsupported claims.

The project will compare the learned policy against fixed top-k retrieval, BM25, hybrid lexical/vector retrieval with reciprocal-rank fusion, ORIOM7's existing fixed sequential workflow and static uncertainty-threshold policies. Evaluation will use a rights-cleared benchmark with held-out test data and pre-defined claim-support, coverage, unsupported-claim, calibration, compute and latency measures. Ablations and negative controls will test whether any measured gains arise from the proposed adaptive mechanism rather than leakage or evaluation artefacts.

The principal output will be a prototype controller, reproducible experimental environment, benchmark results, ablation and negative-control evidence, and a technical white paper. The project is research into a reusable AI/ML decision mechanism, not routine integration of third-party AI tools or a general agent-orchestration exercise.

**Completion required before submission:** insert confirmed starting TRL, named delivery team, numeric success thresholds, sample-size/power rationale, costed work packages and verified applicant/SME details.

## B. Public description — draft (within 400 words)

ORIOM7 is researching ways to make AI-assisted research more evidence-efficient and reliable. Current systems can retrieve large quantities of information, but additional retrieval and computation do not always improve an answer. The research will test whether a learning mechanism can decide which evidence to seek next, when further checking is worthwhile and when the available evidence is insufficient.

The project will develop and evaluate a prototype policy that considers task characteristics, evidence coverage, uncertainty, source diversity, disagreement and remaining compute resources. It will be compared with fixed retrieval and verification approaches using a benchmark designed to test both ordinary and difficult cases, including conflicting sources, stale information, missing evidence and provider failures.

The work will measure evidence support, unsupported claims, task coverage, calibration, compute use and response time. Controlled experiments, ablations and negative controls will be used to identify what causes any improvement and where the approach fails.

The intended output is a reusable technical mechanism and an experimental evidence package that can inform future evidence-grounded AI services. The research is not intended to replace human judgement where evidence is insufficient, and the system will be designed to abstain or request review when appropriate.

The proposed applicant is Life After Crisis Global Organisation CIC. The final application must explain the project's specific community benefit in a manner consistent with the CIC's governing documents and community-interest purpose. The project will be undertaken and exploited in the UK, subject to final delivery and commercialisation arrangements.

**Before publication:** confirm the CIC community-benefit wording, registered legal name, delivery location, and that all public claims are approved.

## C. Scope — draft (within 800 words)

### Technical problem and novelty

The current ORIOM7 research pipeline performs planning, retrieval and synthesis in a fixed sequence. It does not contain a learned policy that allocates evidence-acquisition and verification actions according to uncertainty and expected information value. The proposed R&D addresses the technical uncertainty of whether such a policy can learn state-dependent decisions under constrained resources while maintaining evidence quality.

The intended advance is not a wrapper around a frontier model, a prompt-engineering exercise or a generic multi-agent framework. It is a learned decision mechanism with a defined state representation, constrained action space, cost-sensitive objective, training/evaluation protocol and measurable behaviour. The exact algorithmic contribution must be refined after prior-art review and baseline analysis; novelty must not be asserted merely because the policy is learned.

### Hypothesis

A policy trained on rights-cleared research trajectories can select evidence acquisition, verification and stopping actions that achieve either (a) higher evidence-supported claim quality at matched compute, or (b) lower compute per supported claim at matched quality, without increasing unsupported-claim rate, compared with named fixed baselines.

### Proposed mechanism

The state may include task category, retrieval score distribution, evidence count and diversity, source quality/freshness indicators, claim-support estimates from a separately validated verifier, disagreement signals, calibrated uncertainty and remaining compute/latency budget. Candidate actions are bounded to permitted retrieval, source-fetch, verification, human-review and stopping operations. The controller must not be able to bypass source permissions, user authorisation or safety constraints.

A contextual policy is the initial learned candidate. More complex sequential policies will be considered only if data volume and experimental design justify them. The work will compare the learned approach with fixed top-k, BM25, hybrid retrieval, the current fixed workflow and static threshold policies.

### Experimental validation

The benchmark will use documented provenance and rights, task categories, gold evidence and claim-support labels where feasible, and leakage-resistant train/validation/test splits. Hard cases will include conflicting, stale, missing and adversarial evidence, duplicated evidence, ambiguous queries and provider failures.

Measures will include claim-level evidence support, unsupported-claim rate, coverage/task success, calibration/selective risk, compute per supported claim, latency and human-review/abstention rates. The final application must set numeric success criteria after measuring baseline variance and calculating sample size/minimum detectable effect. The team will report sample sizes, confidence intervals, effect sizes, category breakdowns and failure cases.

Required ablations will remove uncertainty, source-diversity, cost/budget and disagreement features, and disable learned stopping. Negative controls will include random policies, shuffled labels, stale/irrelevant or duplicated evidence, no-evidence cases and provider failures.

### Technical asset and exploitation

The project will create a prototype adaptive evidence/computation controller, versioned state/action/trace schemas, a reproducible evaluation environment, a rights-cleared benchmark specification, model/configuration artefacts and a technical white paper. Potential future applications include evidence-grounded research, enterprise knowledge systems and other AI services where evidence acquisition and verification consume material compute.

Foreground IP ownership and licensing must be defined before submission. Because the proposed applicant is a CIC, ownership, licensing and any commercial exploitation must be compatible with its community-interest purpose and asset lock. The application must not promise an IP transfer or exclusive licence before legal review.

### TRL and project delivery

The competition requires starting TRL 1–3 and an advance of 0.5–1 TRL. The starting TRL for this controller must be evidenced separately from ORIOM7's wider product maturity. The project must deliver a prototype subsystem, validation environment, baseline comparisons, ablations, negative controls and a technical white paper within 1–3 months. No subcontractors are permitted.

**Before submission:** specify the evidenced TRL, detailed algorithmic novelty, numeric targets, sample size, project dates, UK delivery plan, named team, background/foreground IP arrangements and costed work packages.

## D. Mandatory applicant-specific facts — not yet supplied or evidenced

- CIC confirmation-statement submission/acceptance reference.
- CIC articles, community-interest statement and latest CIC report.
- Evidence that the CIC undertakes relevant economic activity.
- FTE employee count, turnover and balance-sheet total.
- Linked/partner enterprise and ownership/control analysis.
- Current management accounts, cash-flow forecast and liabilities.
- Confirmed match funding and board approval.
- Named staff, skills, rates and project time allocations.
- Background IP chain-of-title and third-party licence register.
- Project start TRL and technical baseline commit.
- Numeric success criteria, sample-size/power rationale and full budget.
- Board approval, conflicts register and CIC asset-lock/IP advice.

## E. Cost and grant placeholders

Do not populate total eligible costs or grant requested until a bottom-up eligible-cost model is completed. The competition's maximum industrial-research grant rates are up to 70% for micro/small, 60% for medium and 50% for large organisations. Actual applicant classification and project category must be verified. Subcontractor costs are not allowed.

## F. Submission status

**Not submitted.** This document is a working draft only. No application account, portal form, submission or grant commitment has been created by this document.
