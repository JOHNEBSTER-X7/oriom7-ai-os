"""Leakage-aware walk-forward evaluation for the ORIOM7 SMA research baseline."""
from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator

from commercial_api import record_usage, require_api_key
from quant_backtest import BacktestBar, BacktestRequest, run_sma_backtest

router = APIRouter(prefix="/v1/quant", tags=["quantitative-research"])


class WalkForwardRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
    bars: list[BacktestBar] = Field(min_length=100, max_length=5000)
    train_bars: int = Field(default=500, ge=60, le=4000)
    test_bars: int = Field(default=100, ge=10, le=1000)
    step_bars: int = Field(default=100, ge=1, le=1000)
    embargo_bars: int = Field(default=5, ge=0, le=250)
    fast_candidates: list[int] = Field(default=[5, 10, 15], min_length=1, max_length=8)
    slow_candidates: list[int] = Field(default=[20, 30, 50], min_length=1, max_length=8)
    fee_bps_per_side: float = Field(default=5.0, ge=0, le=1000)
    slippage_bps_per_side: float = Field(default=5.0, ge=0, le=1000)
    annualization_periods: int = Field(default=252, ge=1, le=100000)

    @model_validator(mode="after")
    def validate_dataset_and_windows(self):
        stamps = [bar.timestamp for bar in self.bars]
        if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
            raise ValueError("Bars must be strictly chronological with unique timestamps")
        for bar in self.bars:
            if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
                raise ValueError("OHLC values are inconsistent")
        if len(set(self.fast_candidates)) != len(self.fast_candidates) or len(set(self.slow_candidates)) != len(self.slow_candidates):
            raise ValueError("Candidate periods must be unique")
        if any(value < 2 or value > 250 for value in self.fast_candidates):
            raise ValueError("fast_candidates must be between 2 and 250")
        if any(value < 3 or value > 500 for value in self.slow_candidates):
            raise ValueError("slow_candidates must be between 3 and 500")
        if not any(fast < slow for fast in self.fast_candidates for slow in self.slow_candidates):
            raise ValueError("At least one fast candidate must be smaller than a slow candidate")
        if self.train_bars < max(self.slow_candidates) + 2:
            raise ValueError("train_bars must be at least max(slow_candidates) + 2")
        if self.train_bars + self.embargo_bars + self.test_bars > len(self.bars):
            raise ValueError("Dataset is too short for one train, embargo and test window")
        return self


def _evaluate_test_window(bars: list[BacktestBar], start: int, end: int, fast: int, slow: int,
                          fee_bps: float, slippage_bps: float, annualization_periods: int) -> dict:
    """Run only the held-out window; pre-window closes are signal warm-up, not scored returns."""
    position = 0
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    returns: list[float] = []
    trades = 0
    turnover = 0
    cost = (fee_bps + slippage_bps) / 10000.0
    for index in range(start, end - 1):
        prior_closes = [bar.close for bar in bars[:index]]
        fast_sma = sum(prior_closes[-fast:]) / fast
        slow_sma = sum(prior_closes[-slow:]) / slow
        target = 1 if fast_sma > slow_sma else 0
        changed = abs(target - position)
        gross = target * (bars[index + 1].open / bars[index].open - 1.0)
        net = gross - changed * cost
        equity *= max(0.0, 1.0 + net)
        returns.append(net)
        if changed:
            trades += 1
            turnover += changed
        position = target
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
    if position:
        equity *= max(0.0, 1.0 - cost)
        trades += 1
        turnover += 1
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
    count = len(returns)
    mean = sum(returns) / count if count else 0.0
    variance = sum((value - mean) ** 2 for value in returns) / (count - 1) if count > 1 else 0.0
    volatility = math.sqrt(variance)
    sharpe = mean / volatility * math.sqrt(annualization_periods) if volatility else None
    annualized = (equity ** (annualization_periods / count) - 1) * 100 if count and equity > 0 else (-100.0 if equity == 0 else 0.0)
    return {
        "final_equity": round(equity, 10),
        "total_return_pct": round((equity - 1) * 100, 6),
        "annualized_return_pct": round(annualized, 6),
        "annualized_volatility_pct": round(volatility * math.sqrt(annualization_periods) * 100, 6),
        "sharpe_ratio": round(sharpe, 6) if sharpe is not None else None,
        "maximum_drawdown_pct": round(max_drawdown * 100, 6),
        "trade_count": trades,
        "turnover_units": turnover,
        "scored_periods": count,
    }


def run_walk_forward(body: WalkForwardRequest) -> dict:
    bars = body.bars
    max_slow = max(body.slow_candidates)
    folds = []
    train_start = 0
    train_end = body.train_bars
    while train_end + body.embargo_bars + body.test_bars <= len(bars):
        test_start = train_end + body.embargo_bars
        test_end = test_start + body.test_bars
        best = None
        candidates = []
        # Hyperparameters are selected only from the training slice.
        training_bars = bars[train_start:train_end]
        for fast in sorted(body.fast_candidates):
            for slow in sorted(body.slow_candidates):
                if fast >= slow or len(training_bars) < slow + 2:
                    continue
                training_request = BacktestRequest(
                    symbol=body.symbol, timeframe=body.timeframe, bars=training_bars,
                    fast_period=fast, slow_period=slow,
                    fee_bps_per_side=body.fee_bps_per_side,
                    slippage_bps_per_side=body.slippage_bps_per_side,
                    annualization_periods=body.annualization_periods,
                )
                metrics = run_sma_backtest(training_request)["performance"]
                candidate = {"fast_period": fast, "slow_period": slow,
                             "training_return_pct": metrics["total_return_pct"]}
                candidates.append(candidate)
                # Deterministic tie-break: lower fast, then lower slow period.
                rank = (candidate["training_return_pct"], -fast, -slow)
                if best is None or rank > best[0]:
                    best = (rank, candidate)
        if best is None:
            raise ValueError("No valid parameter pair can be evaluated")
        selected = best[1]
        test_metrics = _evaluate_test_window(
            bars, test_start, test_end, selected["fast_period"], selected["slow_period"],
            body.fee_bps_per_side, body.slippage_bps_per_side, body.annualization_periods,
        )
        folds.append({
            "fold": len(folds) + 1,
            "train_start": bars[train_start].timestamp.isoformat(),
            "train_end_exclusive": bars[train_end - 1].timestamp.isoformat(),
            "embargo_start": bars[train_end].timestamp.isoformat() if body.embargo_bars else None,
            "test_start": bars[test_start].timestamp.isoformat(),
            "test_end": bars[test_end - 1].timestamp.isoformat(),
            "training_observations": train_end - train_start,
            "embargo_observations": body.embargo_bars,
            "test_observations": body.test_bars,
            "selected_parameters": {"fast_period": selected["fast_period"], "slow_period": selected["slow_period"]},
            "training_selection_return_pct": selected["training_return_pct"],
            "test_performance": test_metrics,
            "candidate_count": len(candidates),
        })
        train_end += body.step_bars
    if not folds:
        raise ValueError("No complete walk-forward folds could be constructed")
    test_returns = [fold["test_performance"]["total_return_pct"] for fold in folds]
    mean_return = sum(test_returns) / len(test_returns)
    dispersion = math.sqrt(sum((value - mean_return) ** 2 for value in test_returns) / len(test_returns))
    total_equity = math.prod(fold["test_performance"]["final_equity"] for fold in folds)
    return {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "method": "expanding_train_rolling_test_with_embargo",
        "selection_objective": "maximum in-sample training total return after configured fee and slippage assumptions",
        "fold_count": len(folds),
        "aggregate_out_of_sample": {
            "compounded_test_return_pct": round((total_equity - 1) * 100, 6),
            "mean_fold_return_pct": round(mean_return, 6),
            "fold_return_population_stddev_pct": round(dispersion, 6),
            "positive_fold_count": sum(value > 0 for value in test_returns),
            "negative_fold_count": sum(value < 0 for value in test_returns),
            "total_test_trade_count": sum(fold["test_performance"]["trade_count"] for fold in folds),
        },
        "configuration": {
            "train_bars": body.train_bars, "test_bars": body.test_bars,
            "step_bars": body.step_bars, "embargo_bars": body.embargo_bars,
            "fast_candidates": sorted(body.fast_candidates),
            "slow_candidates": sorted(body.slow_candidates),
            "fee_bps_per_side": body.fee_bps_per_side,
            "slippage_bps_per_side": body.slippage_bps_per_side,
        },
        "folds": folds,
        "warnings": [
            "Parameter selection uses only each fold's training window; test returns are not used to select that fold's parameters.",
            "Embargo bars are excluded from the training fit and scored test window; they may still be part of historical signal warm-up.",
            "Overlapping test windows can occur when step_bars is smaller than test_bars; aggregate compounded return then double-counts overlapping dates.",
            "Small candidate grids and fold counts do not establish statistical significance or eliminate multiple-testing bias.",
            "Caller-supplied OHLCV, open-price reference fills and simplified fee/slippage assumptions remain limitations.",
            "This is historical research, not investment advice, a trading signal or live execution.",
        ],
    }


@router.post("/walk-forward")
async def quant_walk_forward(body: WalkForwardRequest, request: Request,
                             key: dict = Depends(require_api_key)):
    result = run_walk_forward(body)
    await record_usage(request, key, "quant_walk_forward", len(body.bars), 200, {
        "symbol": body.symbol.upper(), "timeframe": body.timeframe,
        "observations": len(body.bars), "folds": result["fold_count"],
    })
    return {"object": "oriom7_quant_walk_forward", **result}
