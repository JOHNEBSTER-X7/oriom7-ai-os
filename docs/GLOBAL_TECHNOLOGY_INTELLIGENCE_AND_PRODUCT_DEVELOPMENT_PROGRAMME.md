# ORIOM7 Global Technology Intelligence & Proprietary Product Development Programme

**Status:** Proposed programme baseline  
**Date:** 13 November 2026  
**Repository:** `JOHNEBSTER-X7/oriom7-ai-os`

## 1. Purpose

Extend ORIOM7 from a hybrid AI search and intelligence platform into a global technology intelligence, product-discovery and proprietary product-development platform. ORIOM7 will index and analyse public, licensed and otherwise lawfully accessible information about products, components, technologies, suppliers, standards, patents, software and markets. It will use that intelligence to identify opportunities for independently designed products and services.

ORIOM7 is not to be represented as already owning, manufacturing or outperforming products that remain at research or proposal stage.

## 2. Architecture principles to preserve

This programme extends, and does not replace, the approved ORIOM7 baseline:

- Hybrid search: independently operated index plus external search providers.
- Hybrid multi-model orchestration through provider-neutral adapters.
- Next.js, React and TypeScript web application; Vercel as initial frontend host.
- Python/FastAPI API and managed backend infrastructure.
- PostgreSQL as primary relational store; Redis for cache and coordination.
- Search, assistant and developer API remain co-equal initial product priorities.
- Evidence-linked answers, source provenance, privacy, security and accessibility remain core requirements.
- Long-running ingestion and enrichment execute in background workers, not frontend request handlers.
- Proprietary cloud and hardware are progressive programmes, not MVP dependencies.

## 3. Programme divisions

1. **ORIOM7 Search & Intelligence** — discovery, retrieval, synthesis and evidence validation.
2. **ORIOM7 Global Registry** — products, components, software, technologies, suppliers and standards.
3. **ORIOM7 Research & Benchmarking** — competitive analysis, technical comparison and opportunity discovery.
4. **ORIOM7 Developer Platform** — APIs, SDKs, connectors and developer tools.
5. **ORIOM7 Proprietary Product Development** — original software, platforms, hardware architectures and services.
6. **ORIOM7 Marketplace & Commercialisation** — distribution, licensing, procurement and partner discovery.

These are programme capabilities. Separate legal entities or subsidiaries should only be established after commercial, legal and operational validation.

## 4. Initial registry coverage

The registry must be vendor-neutral and extend beyond NVIDIA and Amazon.

### Technology and hardware
- Semiconductor vendors, foundries, packaging and test providers.
- GPU, CPU, NPU, DPU, FPGA and other accelerator families.
- Processor architectures, chip models, boards, modules and systems.
- Memory, storage, interconnect, networking and optical components.
- Power delivery, cooling, thermal management and rack infrastructure.
- Servers, workstations, edge devices, robotics, automotive and industrial systems.
- Materials, manufacturing processes and equipment where reliable public or licensed evidence exists.

### Software and services
- Operating systems, runtimes, compilers and developer environments.
- AI models, frameworks, inference engines and training systems.
- Libraries, SDKs, APIs, protocols and standards.
- Cloud, database, storage, security, observability and virtualisation services.
- E-commerce, marketplace, payments, advertising, fulfilment and logistics platforms.
- Open-source projects, with licence and maintenance metadata.

### Intellectual-property and supply-chain intelligence
- Public patent records and published applications.
- Public technical papers, specifications and standards.
- Manufacturer and supplier relationships where supported by evidence.
- Product lifecycle, availability and end-of-life announcements.
- Publicly disclosed manufacturing and packaging relationships.
- Licensing, open-source and usage restrictions.

## 5. Canonical registry record

Every registry object should use a stable internal identifier and support versioning, provenance and correction.

Required common fields:

- `entity_id`: immutable ORIOM7 identifier.
- `entity_type`: company, product_family, product_model, component, subcomponent, technology, software, API, standard, material, process, supplier, patent_record or service.
- `canonical_name` and `aliases`.
- `manufacturer_or_publisher`.
- `parent_entity_id` and `related_entity_ids`.
- `description` and `technical_attributes`.
- `market_categories` and `industry_verticals`.
- `country_or_region`, where evidenced.
- `lifecycle_status`: announced, active, limited, discontinued, end_of_life, unknown.
- `first_seen_at`, `last_verified_at` and `effective_date`.
- `source_records`: URL or licensed source reference, publisher, retrieval time and source type.
- `evidence_status`: unverified, single_source, corroborated, primary_source_verified or disputed.
- `rights_basis`: public metadata, licensed, permission-based, user-supplied or other documented lawful basis.
- `confidence`, `review_status` and `change_history`.

Technical product records should additionally support:
- Model and SKU identifiers.
- Architecture and generation.
- Component bill of materials, where reliably disclosed.
- Interfaces, compatibility and dependencies.
- Performance claims with workload, configuration, date and source.
- Power, thermal, memory, capacity and physical specifications.
- Software support and firmware.
- Manufacturing and supply-chain relationships.
- Price and availability observations with geography and timestamp.

Do not invent hidden bills of materials, confidential supplier relationships, undocumented performance figures or patent ownership.

## 6. Entity relationship model

Core relationships include:

- company **MAKES** product family.
- product family **CONTAINS_MODEL** product model.
- product model **INCLUDES_COMPONENT** component.
- component **CONTAINS_SUBCOMPONENT** subcomponent.
- product **USES_ARCHITECTURE** architecture.
- product **SUPPORTS_INTERFACE** interface or standard.
- software **RUNS_ON** hardware.
- software **DEPENDS_ON** library or runtime.
- supplier **SUPPLIES** component, only where evidenced.
- manufacturer **FABRICATES** or **PACKAGES** a device, only where evidenced.
- patent record **RELATES_TO** technology or organisation.
- benchmark **MEASURES** product under a defined workload.
- source **SUPPORTS** or **CONTRADICTS** a claim.

Every material relationship must have its own provenance and evidence status. The knowledge graph must distinguish a confirmed relationship from a model-generated hypothesis.

## 7. Ingestion and verification pipeline

1. Discover candidate sources and entities.
2. Check source terms, robots directives, licence and permitted acquisition method.
3. Retrieve through approved connectors or licensed APIs.
4. Parse structured data and documents.
5. Canonicalise names, URLs, model numbers and identifiers.
6. Resolve duplicates without merging uncertain entities.
7. Extract claims, specifications and relationships.
8. Attach source-level provenance to every material claim.
9. Cross-check important claims against manufacturer documentation or other primary sources.
10. Record conflicts, missing data and confidence.
11. Publish approved records to lexical, vector and graph indexes.
12. Schedule refreshes and lifecycle updates.
13. Preserve audit history and process correction or deletion requests.

Publicly accessible information is not automatically free of copyright, database rights, contractual restrictions or privacy obligations. Acquisition and reuse must be reviewed for each source and jurisdiction.

## 8. Competitive intelligence and benchmarking

Benchmark NVIDIA, AMD, Intel, Amazon/AWS and other vendors using transparent, reproducible criteria.

Hardware benchmarks must record exact model, system configuration, software version, precision, workload, batch size, latency, throughput, power measurement and test date. Cloud comparisons must record region, instance configuration, storage/network costs, discounts and workload. Marketplace comparisons must record geography, product basket, fees, fulfilment and delivery assumptions.

ORIOM7 must not declare a product universally better from an isolated benchmark. Reports must state where a product leads, where it trails and where evidence is insufficient.

## 9. Proprietary product development lifecycle

Each proposed ORIOM7 product passes these gates:

1. **Opportunity:** identify a real customer problem and measurable unmet need.
2. **Prior art:** search patents, papers, standards, products and open-source implementations.
3. **Freedom to operate:** obtain qualified legal review before commercial implementation.
4. **Original design:** document independent requirements, architecture and design decisions.
5. **Prototype:** build a working software, FPGA or hardware proof of concept.
6. **Evaluation:** run reproducible functional, security, performance, accessibility and cost tests.
7. **IP review:** verify ownership, contractor assignments, third-party licences and patentability.
8. **Commercial validation:** test customer demand, unit economics, manufacturing feasibility and support costs.
9. **Release approval:** security, legal, reliability, documentation and operational sign-off.
10. **Lifecycle:** versioning, vulnerability response, support and end-of-life policy.

Proprietary status must be established through documented authorship, ownership and rights. A brand name or original product label alone does not establish unique technology.

## 10. Proposed ORIOM7 product portfolio

The following are proposed brand and product families, not existing products or confirmed available trademarks:

- **ORIOM7 SILICON** — semiconductor architecture and design research.
- **ORIOM7 COMPUTE** — accelerated and heterogeneous computing.
- **ORIOM7 AI** — models, inference, orchestration and AI services.
- **ORIOM7 CLOUD** — cloud compute and managed infrastructure.
- **ORIOM7 NETWORKS** — networking software and, subject to feasibility, hardware.
- **ORIOM7 STORAGE** — storage and data infrastructure.
- **ORIOM7 GRAPHICS** — graphics, rendering and visual computing.
- **ORIOM7 ROBOTICS** — robotics software and physical AI.
- **ORIOM7 AUTOMOTIVE** — automotive compute and software.
- **ORIOM7 INDUSTRIAL** — industrial automation and edge intelligence.
- **ORIOM7 COMMERCE** — marketplace and commerce infrastructure.
- **ORIOM7 LOGISTICS** — fulfilment, routing and supply-chain software.
- **ORIOM7 DEVELOPER** — APIs, SDKs, tools and developer services.
- **ORIOM7 CYBER** — cybersecurity products and services.
- **ORIOM7 DATA** — data engineering, analytics and intelligence.
- **ORIOM7 SPATIAL** — simulation, digital twins and spatial computing.

Brand, domain, company-name and trademark clearance is required before public launch.

## 11. Initial implementation sequence

### Workstream A — Registry foundation
- Define entity and relationship schemas.
- Create source and evidence models.
- Add lifecycle and verification states.
- Build vendor-neutral ingestion adapters.
- Add search and filtering endpoints.
- Create an initial NVIDIA, AMD, Intel and Amazon/AWS seed catalogue using manufacturer and other permitted sources.

### Workstream B — Search integration
- Index approved registry records in ORIOM7 search.
- Add filters for vendor, category, model, region, lifecycle and evidence status.
- Display source provenance and last-verified date.
- Support comparison queries that link to underlying records.
- Expose registry search through a versioned developer API.

### Workstream C — Research and product opportunity engine
- Detect product gaps and underserved workloads.
- Compare technical specifications and total cost of ownership.
- Generate evidence-linked product opportunity briefs.
- Create proposed product requirements and test plans.
- Require human review before a research hypothesis becomes an approved product claim.

### Workstream D — Proprietary software and hardware
- Prioritise software and infrastructure products with a feasible path to market.
- Characterise actual ORIOM7 workloads before choosing hardware architecture.
- Prototype software and compiler/runtime capabilities.
- Progress accelerator research through simulation and FPGA.
- Require separate technical, legal and investment gates before ASIC or fabrication commitments.

## 12. Initial acceptance criteria

The registry foundation is not complete until:

- A product family can be linked to multiple models and components.
- Every published material claim has a traceable source.
- Conflicting sources can be represented without silently overwriting one another.
- Unknown fields remain explicitly unknown.
- Product lifecycle and last-verified dates are searchable.
- Duplicate detection is tested and reversible.
- Search results distinguish first-party registry data from external provider results.
- API responses are covered by OpenAPI contract tests.
- Tenant access, source permissions, deletion and audit controls are tested.
- Registry ingestion runs through background workers.
- No confidential or unauthorised third-party data is ingested.
- UI and API claims distinguish existing ORIOM7 capabilities from proposed products and future research.

## 13. Governance

Maintain separate statuses for:
- Existing and implemented ORIOM7 capability.
- Approved specification.
- Prototype.
- Research hypothesis.
- Commercially released product.

No marketing, investor or developer material may present a research hypothesis or proposed brand as a manufactured product or proven performance advantage.

## 14. Immediate next deliverables

1. Registry data model and database migration proposal.
2. OpenAPI specification for registry search and entity retrieval.
3. Source acquisition and evidence policy.
4. Initial vendor-neutral taxonomy.
5. NVIDIA product/component seed dataset.
6. AMD, Intel and Amazon/AWS expansion datasets.
7. Search UI integration specification.
8. Competitive benchmarking framework.
9. Proprietary product opportunity scoring model.
10. Hardware R&D stage-gate plan.

**Programme principle:** ORIOM7 learns from the market through lawful, evidence-based intelligence; it creates value through independently designed products, measurable performance and defensible intellectual property.
