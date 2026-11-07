# ORIOM7 Quantitative Intelligence and Market Research Architecture

## Mission
Build a research-grade quantitative intelligence stack for market discovery, financial time series, macroeconomic analysis, digital assets, commodity markets and general time-dependent data. The system is for lawful research, risk analysis and decision support. It is not designed for spoofing, wash trading, quote stuffing, manipulation, insider trading, evasion of exchange controls or unauthorised access.

## Existing V1 implementation
Authenticated `POST /v1/quant/analyse` accepts 30–5,000 chronological OHLCV bars and calculates:
- EMA 12 and EMA 26.
- RSI 14.
- Annualised realised volatility from logarithmic returns.
- Maximum observed close-to-close drawdown.
- Methodology metadata and explicit data limitations.

Bars are caller-supplied. The API does not connect to exchanges, validate corporate actions, execute trades or issue buy/sell recommendations. Usage is metered by observation count.

## Professional quantitative research capabilities to build

### 1. Market data and event-time infrastructure
- Licensed exchange and broker feeds; consolidated trades and quotes where legally available.
- Level 1/Level 2 order-book snapshots and incremental updates; sequence-gap detection and feed-health metrics.
- Trades, OHLCV, funding rates, open interest, liquidations, borrow costs, corporate actions and instrument metadata.
- Macro releases, central-bank data, economic calendars, filings, earnings, news and geospatial/commodity data.
- Event-time ingestion, immutable raw-data archive, schema registry, replay, late-event handling and source provenance.
- Point-in-time datasets and bitemporal storage to prevent look-ahead leakage.

### 2. Quantitative feature research
- Returns, volatility surfaces, realised volatility, range estimators, drawdowns and liquidity measures.
- Market microstructure: spread, depth, order-flow imbalance, volume imbalance, signed trade flow, adverse-selection proxies and impact curves.
- Cross-asset correlations, cointegration diagnostics, factor exposures, carry, momentum, value and quality.
- Regime detection using transparent statistical baselines and validated hidden Markov/state-space models.
- Event studies, anomaly detection, change-point detection and robust time-series forecasting.
- NLP and LLM-assisted extraction from authorised filings/news with evidence citations and uncertainty labels.

### 3. Backtesting and simulation
- Event-driven simulator with explicit order lifecycle and partial fills.
- Bid/ask spread, fees, borrow, funding, latency, slippage and market impact.
- Walk-forward evaluation, purged/embargoed time-series cross-validation and strict train/validation/test separation.
- Point-in-time universe membership and delisted instruments to control survivorship bias.
- Stress scenarios, bootstrap/Monte Carlo simulation and sensitivity analysis.
- Paper trading separated from production brokerage credentials; no live execution in this phase.

### 4. Portfolio and risk laboratory
- Position sizing and exposure aggregation.
- Volatility targeting, concentration, leverage and liquidity limits.
- Historical and parametric VaR, expected shortfall/CVaR, drawdown, stress loss and scenario analysis.
- Factor, sector, currency, counterparty and venue concentration.
- Portfolio construction with covariance shrinkage and robust optimisation.
- Independent pre-trade and post-trade risk controls before any future execution capability.

### 5. Machine learning and PyTorch
- PyTorch training pipelines for sequence models, temporal convolution, transformers and graph neural networks where justified by validated out-of-sample performance.
- GPU training with mixed precision, gradient accumulation, deterministic experiment tracking and checkpoint provenance.
- Feature stores with point-in-time joins; labels, dataset hashes and reproducible experiment manifests.
- Calibration, drift monitoring, explainability and baseline comparisons.
- No model is promoted solely on in-sample returns; require realistic costs, statistical significance, robustness and independent review.

### 6. LLM and agentic research
- Retrieval-augmented research over filings, news, papers, market documentation and internal research.
- Citation-preserving extraction, entity resolution, claim/evidence separation and source trust scoring.
- Tool-using agents may prepare analyses and simulations, but cannot bypass permissions, risk limits or human approvals.
- Prompt injection isolation for retrieved web documents and data feeds.

## LLM inference architecture inspired by Faster LLM Inference

The Machine Learning Mastery tutorial's major themes are incorporated as engineering workstreams:
1. Prefill/decode separation and time-to-first-token versus inter-token latency measurement.
2. KV-cache sizing, allocation, reuse and eviction.
3. Continuous batching and queue-aware scheduling.
4. FlashAttention/efficient attention kernels and operator fusion when supported by the selected model/runtime.
5. Numerical precision and quantization (FP16/BF16/FP8/INT8/4-bit) subject to quality and hardware validation.
6. Speculative decoding and prefix/prompt caching where supported and safe.
7. Tensor/pipeline parallelism and disaggregated prefill/decode for larger deployments.
8. Multi-model routing, adapters/LoRA and workload-aware selection.
9. Load testing and dashboards for p50/p95/p99 latency, TTFT, inter-token latency, tokens/sec, queue time, GPU utilisation, VRAM, cache hit rate, error rate and cost per million tokens.

### VLLM integration added
The API now supports an optional OpenAI-compatible vLLM `/chat/completions` endpoint via:
- `ORIOM7_VLLM_BASE_URL`
- `ORIOM7_VLLM_API_KEY`
- `ORIOM7_VLLM_MODEL`

Set `ORIOM7_MODEL_PRIMARY=vllm` to select it as primary, or `ORIOM7_MODEL_FALLBACK=vllm` to use it as fallback. Keep the endpoint on a private network, configure authentication and TLS/service-mesh protections, and never expose its key in browser code. This is an adapter, not a deployed GPU server. No PyTorch/vLLM dependency or model weights are installed in the API service.

## Deployment tiers
- Developer: CPU tests, small local models, reproducible datasets.
- Research workstation: one GPU, PyTorch, Transformers and vLLM for experimentation.
- Production inference: isolated GPU pool, autoscaling, continuous batching, model registry, canary rollout and workload quotas.
- High-scale research: distributed feature/data pipelines, GPU training cluster, object storage, stream processing and dedicated observability.

## Security and market integrity
- Use only licensed, authorised data and exchange APIs.
- Respect venue rate limits, data redistribution rights and jurisdictional rules.
- No spoofing, layering, wash trading, quote stuffing, manipulation, insider trading, credential abuse or evasion.
- Keep research, paper trading and any future live execution environments separate.
- Secrets remain server-side; enforce tenant isolation, audit trails, key rotation and least privilege.
- Models and agents cannot grant themselves trading permissions or override hard risk controls.

## Roadmap
1. V1: authenticated OHLCV analytics and vLLM adapter (implemented; tests pending CI).
2. V2: licensed market-data adapters, instrument master, event-time store and point-in-time feature contracts.
3. V3: event-driven backtesting, execution-cost models and walk-forward evaluation.
4. V4: PyTorch experiment pipeline, model registry, feature store and drift monitoring.
5. V5: portfolio risk engine, paper-trading simulation and controlled approvals.
6. V6: GPU inference scheduler, vLLM deployment, benchmarking, quantization and multi-model routing.
7. V7: advanced order-book analytics, graph/alternative data and multi-asset intelligence.

## Readiness boundary
The quantitative endpoint and vLLM adapter are code foundations. No market feed, PyTorch training cluster, vLLM server, GPU fleet, feature store, backtester, portfolio risk engine or broker execution is connected by this change. Validate each subsystem with licensed data, reproducible tests, security review and operational monitoring before production use.

## Implementation references
- vLLM documentation: https://docs.vllm.ai/en/stable/ — PagedAttention, continuous batching, chunked prefill, prefix caching, quantization, speculative decoding, parallelism, streaming and OpenAI-compatible serving.
- PyTorch compiler documentation: https://docs.pytorch.org/docs/stable/torch.compiler.html — `torch.compile` and compiler/runtime optimisation.
- PyTorch scaled dot-product attention: https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention — backend selection and fused attention implementations.
- Machine Learning Mastery, Faster LLM Inference: https://machinelearningmastery.com/faster-llm-inference/ — conceptual and practical learning guide informing this roadmap.

Runtime features must be benchmarked on the exact model, accelerator, driver, precision and workload. Quantization or compilation can change numerical outputs and may reduce quality; no setting should be enabled globally without regression tests.
