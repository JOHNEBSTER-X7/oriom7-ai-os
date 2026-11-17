# ORIOM7 — UK R&D&I Funding Eligibility Readiness

**Status:** preparation framework; not an award, eligibility determination or submitted application.  
**Applicant model:** UK-registered SME as sole business applicant, if the chosen competition permits it.  
**Research focus:** adaptive evidence acquisition and compute allocation for evidence-grounded AI research.  
**Product baseline:** existing ORIOM7 monorepo on the `main` branch.  
**Funding envelope:** £500,000 is the wider programme ambition, not the budget for the previously reviewed Innovate UK competition.

## 1. Important competition boundary

The Innovate UK competition previously reviewed, **Efficient, Structured and Controllable AI Systems**, closed at 11:00 UK time on 17 November 2026. This document prepares ORIOM7 for a future competition; it does not reopen that round or imply that a future call will have the same rules.

That competition's published limits included:
- £50,000–£150,000 eligible project costs;
- 1–3 months duration;
- UK-registered micro, small or medium business eligibility, including a single-business applicant route;
- no subcontractors;
- industrial research grant intensity up to 70% for micro/small businesses, 60% for medium businesses and 50% for large businesses;
- a requirement for genuinely novel, reusable AI mechanisms, experimental validation, baselines, ablations, negative controls and a technical white paper.

A £150,000 project at a 70% grant rate would require £45,000 of eligible match funding. A £50,000 project would still require £15,000. The £500,000 wider programme cannot be represented as eligible under that call's £150,000 cap.

**No grant rate, match requirement, duration, eligible cost or theme should be carried into a future application without checking that future competition's live guidance.**

## 2. Applicant eligibility — evidence required

The company must complete and retain documentary evidence for each item. Do not state an item is satisfied until verified.

| Gate | Evidence to assemble | Current status |
|---|---|---|
| UK legal entity | Companies House company number, incorporation record and registered office | Founder confirmation required |
| SME classification | Latest accounts, employee count, turnover/balance-sheet data and linked/partner enterprise analysis | To verify |
| Ownership and control | Share register, PSC register, cap table and group structure | To verify |
| Financial health | Filed accounts, current management accounts, cash-flow forecast and going-concern evidence | To verify |
| Match funding | Bank evidence, board-approved allocation, investor commitment or other permitted source | Not confirmed |
| Subsidy control | Record of relevant public support and confirmation of applicable subsidy route | To verify |
| Project capacity | Named delivery lead, staff CVs, time allocation and delivery plan | To assemble |
| IP ownership | Founder/employee/contractor assignments, licences, open-source notices and third-party terms | To audit |
| Data and security | Data map, lawful access/rights basis, retention, security controls and supplier terms | To audit |

A company-only application is possible only where the particular competition explicitly allows a single applicant. A university is not assumed to be a partner, subcontractor or cost recipient in this proposal.

## 3. Proposed eligible R&D project

**Working title:** Learning to Allocate Evidence and Computation for Reliable AI Research.

**Research question:** Can a learned, uncertainty-aware controller select the next evidence-acquisition or verification action—and decide when to stop—so that evidence-supported answer quality is improved at a lower or comparable compute budget than fixed retrieval and fixed verification policies?

**Research hypothesis:** A controller trained and evaluated on logged research trajectories can learn state-dependent action and stopping policies that outperform pre-registered fixed baselines on a held-out evaluation set, without increasing unsupported claims.

### Research boundary

The primary R&D subject is the adaptive decision mechanism, not a general-purpose agent framework, product integration exercise, or routine orchestration layer.

The existing planner/retriever/synthesiser workflow is retained as:
1. the current product baseline;
2. a source of reproducible research trajectories, subject to data rights and privacy review;
3. a comparator against which the new controller will be tested.

The research will investigate:
- evidence sufficiency and uncertainty representations;
- expected information gain and marginal compute cost;
- sequential action selection and optimal stopping;
- calibration, robustness and generalisation across task types;
- failure conditions, negative results and reproducibility.

The controller is a research hypothesis, not a capability claimed to exist today.

## 4. Work packages and outputs

| Work package | Activity | Verifiable output |
|---|---|---|
| WP1 — Baseline and dataset | Freeze baseline versions; define tasks, splits, rights and evaluation labels | Baseline report, dataset card, data-rights register |
| WP2 — State and reward design | Define observable state, actions, reward, cost accounting and safety constraints | Versioned technical specification |
| WP3 — Controller research | Compare contextual-bandit and sequential-policy approaches; train only on approved data | Reproducible training code and model artefacts |
| WP4 — Controlled evaluation | Compare learned policy with fixed top-k, BM25, hybrid RRF and static verification policies | Benchmark results, confidence intervals, ablations |
| WP5 — Robustness and safety | Test unsupported claims, missing evidence, conflicting sources, provider failure and budget exhaustion | Failure analysis and guardrail report |
| WP6 — Translation and dissemination | Integrate only validated components behind feature flags; publish technical white paper | Reproducibility package and technical white paper |

## 5. Accessibility is a product invariant, not a second research claim

The existing `packages/accessibility-engine/` remains part of ORIOM7's product architecture. The R&D work must preserve canonical answer meaning, citations, uncertainty, warnings and safety information when output presentation is adapted.

Accessibility preference resolution must not change retrieval ranking, source selection, factual claims or the evidential threshold. The proposal must not claim formal verification, WCAG conformance or independent user validation unless the corresponding tests and audit evidence exist.

The research programme may evaluate whether adaptive presentation preserves information and provenance, but the primary research question remains the learned evidence/computation controller.

## 6. Budget and match-funding controls

The £500,000 figure is a multi-stage programme envelope. It must be split into separately costed projects only where a live funding call permits the scope, duration and cost categories.

For every application:
- build the budget from named staff, salary rates, productive hours and project time;
- calculate grant and match from the competition's exact intervention rate;
- include only eligible and necessary costs;
- do not rely on unpaid founder time as match unless expressly permitted;
- do not count the same cost or match source twice;
- do not assume subcontracting, cloud compute, equipment or overheads are eligible without the call's rules;
- obtain evidence of available cash before committing to a match-funded project.

**Go/no-go rule:** do not submit a match-funded bid until the full match amount, cash timing and working-capital exposure have been evidenced and approved.

## 7. Claims discipline

Use these labels in all application material:
- **Implemented:** supported by code and tests in the repository.
- **Partially implemented:** code exists but integration, deployment or validation remains outstanding.
- **Research proposed:** a hypothesis or work package to be tested.
- **Target:** a prospective metric, not a result.
- **Not yet validated:** requires external audit, user study, benchmark or production evidence.

Never claim that ORIOM7 is already trained with a VoI policy, semantically verifies every claim, guarantees factual correctness, is independently WCAG-certified, or has passed a security audit unless evidence is produced.

## 8. Submission pack checklist

- [ ] Company eligibility and Companies House evidence
- [ ] SME and connected-enterprise assessment
- [ ] Ownership, control and IP chain-of-title
- [ ] Accounts, cash-flow forecast and match-funding proof
- [ ] Competition-specific subsidy-control declaration
- [ ] Technical baseline and reproducible commit references
- [ ] Research novelty statement and prior-art review
- [ ] Dataset provenance, rights and privacy assessment
- [ ] Pre-registered metrics, baselines, ablations and negative controls
- [ ] Detailed cost model tied to named resources
- [ ] Risk register, milestones and exploitation plan
- [ ] Competition-specific application form and terms checked on submission day

## 9. Decision log

This is a readiness framework for future opportunities. It does not certify the company, make a funding body decision, create a university partnership, commit match funding or submit an application.
