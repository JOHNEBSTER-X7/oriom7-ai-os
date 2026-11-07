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

## Quant Engine V2: historical backtesting
Authenticated `POST /v1/quant/backtest` accepts 35–5,000 chronological OHLCV bars and runs a deterministic long-only SMA crossover research simulation. The fast/slow periods, per-side fees, per-side slippage and annualisation periods are explicit inputs.

Execution assumptions:
- At each bar open, the target position is derived only from closes strictly before that bar.
- Rebalancing uses the current bar's open as a reference fill.
- Exposure is marked open-to-next-open.
- Fee plus slippage basis points are charged on each position change.
- Any remaining position is liquidated at the final available open and charged a final side.
- No leverage, shorting or live order routing.

Reported outputs include total and annualised return, annualised volatility, Sharpe ratio, maximum drawdown, buy-and-hold benchmark return, position changes, turnover, trade log and equity curve.

The endpoint is intentionally a baseline, not an institutional-grade simulator. It does not model bid/ask spread, order-book depth, market impact, queue position, latency, funding, borrow, dividends, corporate actions, delisted assets or survivorship bias. It does not perform walk-forward validation or claim out-of-sample performance. Next work should add realistic execution-cost models, point-in-time data and purged/embargoed walk-forward validation before strategy comparisons are treated as robust.


## Quant Engine V3: walk-forward validation

Authenticated `POST /v1/quant/walk-forward` adds expanding-training, rolling-test evaluation for the SMA crossover baseline.

- Accepts 100–5,000 chronological OHLCV bars.
- Uses an expanding training window, a configurable embargo gap, a held-out test window and a configurable step.
- Evaluates a bounded grid of fast/slow SMA candidates independently inside each training window. The candidate with the highest training-window total return after configured fee and slippage is selected; deterministic ties prefer lower fast and then lower slow periods.
- The selected parameters are frozen for that fold's test window. Test-window returns do not participate in that fold's parameter selection.
- Historical closes before the test window provide indicator warm-up, but only returns generated within the held-out test window are scored.
- Reports per-fold boundaries, selected parameters, training selection return, test return, annualised return/volatility, Sharpe ratio, maximum drawdown, trade count and turnover; aggregate output reports compounded fold return and fold-return dispersion.
- Usage is metered by input observation count under `quant_walk_forward`.

### Validation boundaries and cautions

The embargo interval is excluded from the training slice and scored test slice. Historical bars in the embargo may still be used as signal warm-up before the test starts; this is valid for causal indicator state, but it is not a claim of a fully purged label-based cross-validation framework. This baseline uses non-overlapping test windows when `step_bars >= test_bars`; if the step is smaller, windows overlap and compounded aggregate return double-counts dates. Use non-overlapping windows for aggregate compounding.

Parameter selection maximises in-sample total return across a candidate grid, so multiple-testing and overfitting risks remain. Fold counts and trade counts may be small; no statistical significance, probability of profitability or generalisation guarantee is claimed. Data remains caller-supplied OHLCV; execution uses open-price references and simplified fee/slippage assumptions. No exchange feed, broker connection or live execution is present.


## Quant Engine V4: chronological ML feature pipeline and PyTorch baseline

Added authenticated endpoints:
- `POST /v1/quant/ml/dataset` builds a reproducible, chronological supervised dataset from caller-supplied OHLCV.
- `POST /v1/quant/ml/train` trains a small PyTorch MLP baseline when the optional PyTorch runtime is installed.

### Dataset construction
- Uses 1-, 5-, 10- and 20-bar log returns, 20-bar realised volatility and close-versus-20-bar-SMA deviation.
- Target is the next bar's close-to-close log return. Feature rows are timestamped separately from their future target timestamp.
- Uses ordered 70% train / 15% validation / 15% test partitions without shuffling.
- Z-score scaling statistics are calculated on the training partition only and then applied to validation and test rows.
- Strict timestamp uniqueness/order and OHLC consistency validation; 100–5,000 input bars.

### PyTorch training baseline
- Small feed-forward regressor (6 → 16 → 8 → 1), ReLU activations, Adam optimiser and MSE objective.
- Training partition updates model weights; validation MSE selects the best epoch; the held-out test partition is evaluated after model selection.
- Deterministic seed is set and deterministic PyTorch algorithms are requested where supported.
- Returns test MSE and directional accuracy, validation/training loss history and model configuration.
- Model weights are not persisted; this is a request-scoped research baseline, not a production model registry.

### Optional runtime
The core API does not install PyTorch by default. Install the separate optional dependency set from `services/api/requirements-ml.txt` in a suitable CPU/GPU environment. The dataset endpoint works without PyTorch; the training endpoint returns HTTP 503 with setup guidance when PyTorch is unavailable. GPU drivers, CUDA compatibility, model serving, weights persistence, feature store, experiment tracking and scheduled retraining are not provisioned by this milestone.

### Validation boundaries
A single chronological holdout and a small MLP do not establish predictive validity, statistical significance or profitability. There is no hyperparameter search, nested walk-forward retraining, calibrated uncertainty, transaction-cost model, portfolio evaluation, market feed or execution. This is experimental research only, not financial advice or a trading instruction.


## Quant Engine V5: historical portfolio risk laboratory

Authenticated `POST /v1/quant/risk/portfolio` adds historical multi-asset portfolio diagnostics.

### Inputs and calculations
- Accepts 2–20 assets, each with 61–5,000 chronological OHLCV bars.
- Requires unique symbols, identical aligned timestamps and long-only non-negative weights summing to 1.0.
- Builds close-to-close simple returns for each asset and static-weight portfolio returns.
- Calculates annualised volatility, cumulative return, Sharpe ratio against a configurable annual risk-free rate and maximum drawdown.
- Calculates empirical historical VaR and expected shortfall at 95% or 99% confidence, including tail observation count.
- Reports asset return correlation matrix, portfolio variance risk-contribution fractions and Herfindahl concentration/effective position count.
- Accepts up to 20 deterministic, user-supplied asset shock scenarios and reports their weighted portfolio impact.
- Usage is metered by total submitted asset-bar observations under `quant_portfolio_risk`.

### Assumptions and limitations
The engine uses static long-only weights and historical close-to-close returns. It does not model rebalancing, leverage, short positions, derivatives, currency conversion, intraperiod gaps, spread, liquidity, market impact, funding, taxes or execution costs. Empirical VaR/expected shortfall are sample-dependent and do not bound worst-case losses. User-defined stress scenarios are not probability-weighted forecasts. Instrument identity, corporate actions, data licensing and survivorship are not independently verified. No market feed, broker or order execution is connected. This is risk research, not investment advice.


## Market Data Fabric V1: public Binance Spot candle ingestion

### Connected provider
- Binance Spot public REST market data is connected through the documented market-data-only host `https://data-api.binance.vision`.
- Authenticated ORIOM7 endpoint: `POST /v1/market-data/binance/klines`.
- Provider catalogue: `GET /v1/market-data/providers`.
- Supported candle intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w and 1M.
- Bounded request size: 1–1,000 candles; optional timezone-aware start/end timestamps.
- Public endpoint needs no Binance API key and does not request account, trade or withdrawal permissions.
- Redirects are disabled; requests have a 10-second timeout; oversized responses are rejected; provider rate-limit/ban responses are mapped to a retryable service error.

### Normalisation and storage
- Converts provider kline arrays into canonical UTC timestamps, decimal OHLCV/quote volume, trade count, closed/open status and a SHA-256 digest of the raw candle row.
- Validates chronological uniqueness, numeric fields, non-negative volume, OHLC consistency and time range.
- Upserts candles by provider, symbol, timeframe and open time, so repeat ingestion refreshes a still-open candle instead of creating duplicates.
- Migration `017_market_data.sql` creates `market_candles` with numeric precision, primary key, integrity checks and symbol/time indexes.
- API requires configured `DATABASE_URL` and migration 017; it returns HTTP 503 instead of pretending data was stored when persistence is unavailable.
- Raw provider response payloads are not persisted. Only normalised candle fields and a per-row raw payload digest are stored.
- Usage is metered by received candle count under `market_data_ingestion`.

### Provider roadmap and boundaries
Binance Spot public REST candles are the only connected provider in this V1. Coinbase Exchange and Kraken Spot are listed as planned, not integrated. Real-time WebSocket ingestion, exchange instrument master synchronisation, L1/L2 order books, trade prints, cross-provider symbol mapping, streaming queue, TimescaleDB partitioning, Redis cache and automatic scheduled backfills remain future work.

Provider access, instrument coverage, geo-availability, redistribution rights and commercial use must be checked against the exchange's current terms. Public endpoint access does not grant unrestricted data redistribution rights. No exchange account is linked; no private credentials, order routing or trading permissions are used.


## Market Data Fabric V2: multi-exchange instrument master

### Public instrument adapters
- Added provider-specific instrument catalogue synchronisation for Binance Spot `GET /api/v3/exchangeInfo`, Coinbase Exchange `GET /products`, and Kraken Spot `GET /0/public/AssetPairs`.
- Added authenticated `POST /v1/market-data/instruments/sync?provider=...` and `GET /v1/market-data/instruments`.
- All adapters use fixed HTTPS hostnames, 15-second timeouts, disabled redirects and a 5 MB response cap. Public endpoints require no exchange API credentials.
- Normalised fields include provider, venue, native instrument ID, base and quote asset codes, display symbol, status, and available tick/lot/minimum-size metadata. Missing metadata remains null rather than being guessed.
- Binance tick and lot metadata is extracted from PRICE_FILTER and LOT_SIZE. Coinbase increments and minimum base size are mapped from product metadata. Kraken preserves its internal pair key and WebSocket/display symbol separately; tick size and order minimum are mapped where supplied.
- Provider metadata is hashed and stored with first/last-seen timestamps. Migration `018_market_instruments.sql` creates the provider-specific instrument master and indexes.

### Identity and data-quality policy
- Primary identity is `(provider, instrument_id)`. The same text symbol on two venues is never merged automatically.
- Base/quote strings are preserved exactly as supplied by each provider. For example, Kraken's internal asset codes may differ from the familiar display codes.
- No cross-provider fungibility, token contract identity, wrapped-asset equivalence, or fiat settlement equivalence is inferred. A future canonical asset graph requires independently verified mappings and provenance.
- Catalogue sync is a point-in-time snapshot/upsert, not a complete delisting reconciliation process. Instruments absent from a later response are not automatically marked inactive; status is taken from the provider response.
- The 20,000-instrument parser ceiling, 5 MB response ceiling and bounded list endpoint are safety limits, not claims of complete exchange coverage.

### Validation boundaries
- Instrument sync is connected to public exchange REST endpoints in code, but provider-backed live sync and the PostgreSQL migration have not been represented as completed until staging credentials/environment and database migration validation are run.
- Binance remains the only connected candle-ingestion adapter in V2. Coinbase and Kraken candle ingestion, WebSocket feeds, order books, trades, scheduled refresh, stale-record reconciliation and canonical cross-venue asset mapping remain future milestones.
- Public API access does not grant unrestricted commercial redistribution rights. Review each exchange's current terms, regional availability, attribution and licensing requirements before resale or redistribution.


## Market Data Fabric V3: public WebSocket trade and ticker streaming

### Architecture delivered
- Added `services/api/market_stream.py` with a provider-neutral event envelope, venue-specific parsers, SHA-256 raw-message fingerprints and a reusable monotonic sequence-gap tracker.
- Added standalone `services/api/market_stream_worker.py`; streaming is deliberately isolated from the FastAPI request lifecycle.
- Added optional dependencies in `services/api/requirements-streaming.txt` (`websockets` and `redis`); the core API dependency set is unchanged.
- Added authenticated `GET /v1/market-data/streaming/capabilities` to expose supported adapters and limitations. It explicitly reports that the worker is optional and is not started by the API.
- Added the capability route to OpenAPI and unit tests for Binance, Coinbase and Kraken event normalisation, sequence-gap utility and endpoint response.

### Public feed adapters
- Binance Spot: market-data-only WebSocket host `wss://data-stream.binance.vision`; combined `@trade` and `@bookTicker` streams for configured symbols.
- Coinbase Exchange: `wss://ws-feed.exchange.coinbase.com`; public `ticker`, `heartbeat` and `matches` subscriptions for configured product IDs.
- Kraken Spot WebSocket v2: `wss://ws.kraken.com/v2`; public `trade` and `ticker` subscriptions for configured symbols.
- No API keys, account scopes, order placement, private user channels or withdrawal permissions are used.

### Canonical event pipeline
- Normalises provider events into versioned envelopes containing provider, venue, provider-native instrument ID, event type, exchange timestamp where supplied, local receive timestamp, sequence metadata, bounded structured event data and raw-message SHA-256.
- A bounded in-process asyncio queue applies backpressure. When full, the worker increments a drop counter instead of allowing unbounded memory growth.
- A Redis publisher writes events to the configurable Redis Stream (default `oriom7:market:events`) with approximate MAXLEN retention (default 100,000 entries).
- The worker uses WebSocket ping/pong, bounded message sizes/queues, reconnect loops and exponential backoff up to 60 seconds. A 60-second log reports queue depth and in-memory counters.
- Redis is required by the standalone worker. It fails at startup if `REDIS_URL` is absent or Redis cannot be reached; it does not silently discard events.

### Running the optional worker
From `services/api`:
1. Install core and development dependencies as appropriate, then `pip install -r requirements-streaming.txt`.
2. Set `REDIS_URL` to a Redis instance dedicated or provisioned for the ORIOM7 stream.
3. Optionally configure `ORIOM7_BINANCE_STREAM_SYMBOLS` (comma-separated, default `BTCUSDT`), `ORIOM7_COINBASE_STREAM_PRODUCTS` (default `BTC-USD`), `ORIOM7_KRAKEN_STREAM_SYMBOLS` (default `BTC/USD`), `ORIOM7_MARKET_REDIS_STREAM`, `ORIOM7_MARKET_REDIS_MAXLEN` and `ORIOM7_MARKET_STREAM_QUEUE_SIZE`.
4. Run `python market_stream_worker.py` as a separately supervised process.

### Explicit V3 boundaries
- This increment streams public trades, ticker/top-of-book updates and heartbeats. Binance `bookTicker` is best-bid/best-ask only, not a depth book.
- Full L2 order-book snapshots/deltas, checksums, snapshot reconciliation, sequence-gap recovery, trade-to-candle aggregation, durable dead-letter handling, consumer-group workers and production deployment/supervision are not included yet.
- Sequence diagnostics are implemented as a reusable utility and tested, but trade/ticker identifiers are not treated as contiguous book-update sequences. No false claim of order-book gap detection is made in this V3 increment.
- The worker has not been started against a live Redis instance or verified against live exchange connections in CI. Tests use deterministic provider message fixtures.
- Review each venue's current feed terms, geographic availability, rate limits and redistribution rights before commercial use.


## Market Data Fabric V3.1: Level 2 Order Book Intelligence

### Order-book engine
- Added `services/api/market_orderbook.py` with Decimal-based price/quantity handling, bounded depth, snapshot loading, absolute-size updates, zero-size deletion, crossed-book rejection and explicit validity state.
- Binance Spot: dedicated public depth WebSocket per configured symbol plus REST depth snapshot. Stream starts before snapshot retrieval; queued frames are then bridged against snapshot `lastUpdateId`. Updates older than the current ID are ignored; a non-bridging/gapped `U/u` range invalidates the book and triggers reconnect/rebuild.
- Coinbase Exchange: public `level2_batch` snapshot and `l2update` messages. Change sizes are treated as absolute level quantities, and zero removes the level.
- Kraken Spot WebSocket v2: public `book` channel snapshot and updates. Full-precision JSON numbers are decoded as Decimal, all updates in a frame are applied in order, depth is truncated to the subscribed range, and the official top-10 CRC32 checksum is verified after every frame. A mismatch invalidates the book and forces reconnection/snapshot.
- Reconnect invalidates prior Coinbase/Kraken book state until a new snapshot is received. Binance rebuilds a fresh REST snapshot and bridges the new depth stream.

### Market microstructure analytics
- Best bid/ask, bid/ask size, mid-price, absolute spread and spread in basis points.
- Top-level quantity imbalance and notional depth on both sides of the configured book.
- Indicative visible-book market-order simulation: filled/unfilled quantity, visible notional, VWAP and slippage against the best visible price.
- Published Redis events include analytics plus the top 25 price levels, while the worker retains up to 1,000 Binance levels and 25 Coinbase/Kraken levels.
- The output is research data, not an execution quote. It excludes hidden liquidity, latency, fees, queue priority, order matching and market movement.

### Limits and operating controls
- Binance L2 uses one WebSocket connection per configured symbol and is intentionally capped at five symbols in this worker. Coinbase is capped at five configured products in this worker. Tune and load-test before increasing.
- The worker publishes order-book events to Redis Streams; it does not expose a shared, low-latency in-memory book query endpoint in the API.
- Coinbase Level 2 and Kraken book updates are applied only after a fresh snapshot. Binance snapshot bridging and update-ID continuity are enforced.
- A queue overflow increments a drop counter; consumers must monitor telemetry and treat a dropped event as a data-quality incident. Redis write failures retry the current event with bounded exponential delay.
- No production deployment, live exchange session, Redis environment, database persistence of depth events, or end-to-end latency benchmark has been claimed. Tests use deterministic provider fixtures.
- No order execution, account access, private feed, or trading capability is added.

### Exchange protocol references
- Binance Spot depth stream and snapshot synchronisation: official Spot WebSocket stream documentation.
- Coinbase Exchange Level 2 and level2_batch channel: official Exchange WebSocket channel documentation.
- Kraken Spot WebSocket v2 book and CRC32 checksum: official Book (Level 2) and Spot WebSocket v2 Book Checksum guide.


## Market Intelligence V1: Liquidity, Flow, Volume and Regime Analytics

### API
- Added `services/api/market_intelligence.py` and registered `POST /v1/market-intelligence/analyse` in the FastAPI application.
- Endpoint is API-key authenticated and metered as `market_intelligence_analysis`.
- Caller supplies bounded order-book snapshots, trade prints with aggressor side, closing prices and venue books. This milestone analyses supplied data; it does not yet consume Redis Streams directly or maintain a durable time-series feature store.

### Analytics implemented
- Discrete order-book liquidity heatmap with bid/ask levels, distance from midpoint and notional value.
- Liquidity-wall candidates with size multiple, persistence and disappearance ratios. Persistence is based on the number of snapshots where size remains above a median-relative threshold, not merely price-level presence.
- Aggressor-flow notional, signed delta, buy/sell pressure and normalised order-flow imbalance.
- Absorption candidate: strong signed aggressive notional flow with limited price response (<=5 bps).
- Exhaustion candidate: strong signed aggressive notional flow with a large observed price move (>=50 bps).
- Price-bucketed trade volume profile and point of control.
- Rule-based 20-return-window regime labels: uptrend/downtrend/range and high/low volatility.
- Cross-venue midpoint divergence and a simple fragmentation index from caller-supplied venue books.
- Deterministic alert rules for aggressive-flow imbalance, absorption, exhaustion, ephemeral large liquidity, cross-venue divergence and high volatility.

### Interpretation and limitations
- These are deterministic, explainable research heuristics. They are not trained models, forecasts, investment advice or trading signals.
- A large wall that disappears is not proof of spoofing. Reliable spoofing research needs event-level order add/cancel/execute histories, exchange-specific rules, timestamps and trade matching; snapshots alone are insufficient.
- Absorption/exhaustion are candidate labels using fixed thresholds. They require book replenishment, aggressor classification quality and instrument/timeframe calibration.
- The heatmap is a sequence of discrete snapshots, not a continuous historical depth surface.
- Regime classification is a simple heuristic, not a statistical hidden-state model.
- Cross-venue comparison assumes caller has already established instrument equivalence and timestamp comparability. It does not account for fees, transfers, funding, regional access, or settlement.
- The response includes a rule-generated textual summary and LLM-ready context; it does not claim to call an LLM or generate forecasts.
- No Redis consumer, stream-to-feature pipeline, persistent historical market-intelligence store, notification delivery integration or live exchange verification is included in this increment.
- All output is research only; no account access, order routing or execution capability is added.
