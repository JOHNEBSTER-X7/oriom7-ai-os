"""Deterministic, long-only SMA crossover backtesting with explicit cost assumptions."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator

from commercial_api import record_usage, require_api_key

router = APIRouter(prefix="/v1/quant", tags=["quantitative-research"])


class BacktestBar(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class BacktestRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
    bars: list[BacktestBar] = Field(min_length=35, max_length=5000)
    fast_period: int = Field(default=10, ge=2, le=250)
    slow_period: int = Field(default=30, ge=3, le=500)
    fee_bps_per_side: float = Field(default=5.0, ge=0, le=1000)
    slippage_bps_per_side: float = Field(default=5.0, ge=0, le=1000)
    annualization_periods: int = Field(default=252, ge=1, le=100000)

    @model_validator(mode="after")
    def validate_bars_and_strategy(self):
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        if len(self.bars) < self.slow_period + 2:
            raise ValueError("bars must contain at least slow_period + 2 observations")
        stamps = [bar.timestamp for bar in self.bars]
        if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
            raise ValueError("Bars must be strictly chronological with unique timestamps")
        for bar in self.bars:
            if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
                raise ValueError("OHLC values are inconsistent")
        return self


def _sma(values: list[float], period: int) -> float:
    return sum(values[-period:]) / period


def run_sma_backtest(body: BacktestRequest) -> dict:
    """Signals at prior close; rebalance at next bar open; mark open-to-open."""
    bars = body.bars
    opens = [bar.open for bar in bars]
    closes = [bar.close for bar in bars]
    cost_rate = (body.fee_bps_per_side + body.slippage_bps_per_side) / 10000.0
    position = 0
    equity = 1.0
    peak = equity
    max_drawdown = 0.0
    period_returns: list[float] = []
    equity_curve = [{"timestamp": bars[body.slow_period].timestamp.isoformat(), "equity": equity}]
    trades: list[dict] = []
    turnover_total = 0.0

    for index in range(body.slow_period, len(bars) - 1):
        # Only closes strictly before the execution bar are used for the signal.
        history = closes[:index]
        fast_sma = _sma(history, body.fast_period)
        slow_sma = _sma(history, body.slow_period)
        target = 1 if fast_sma > slow_sma else 0
        turnover = abs(target - position)
        if turnover:
            trades.append({
                "timestamp": bars[index].timestamp.isoformat(),
                "side": "buy" if target else "sell",
                "reference_price": opens[index],
                "reason": "prior_close_sma_crossover",
                "fast_sma": round(fast_sma, 8),
                "slow_sma": round(slow_sma, 8),
            })
        gross_return = target * (opens[index + 1] / opens[index] - 1.0)
        net_return = gross_return - turnover * cost_rate
        equity *= max(0.0, 1.0 + net_return)
        period_returns.append(net_return)
        turnover_total += turnover
        position = target
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
        equity_curve.append({"timestamp": bars[index + 1].timestamp.isoformat(), "equity": round(equity, 10)})

    # Liquidate any open position at the final available open and charge one final side.
    if position:
        equity *= max(0.0, 1.0 - cost_rate)
        period_returns.append(-cost_rate)
        turnover_total += 1
        trades.append({
            "timestamp": bars[-1].timestamp.isoformat(),
            "side": "sell",
            "reference_price": opens[-1],
            "reason": "end_of_test_liquidation",
        })
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
        equity_curve[-1] = {"timestamp": bars[-1].timestamp.isoformat(), "equity": round(equity, 10)}

    count = len(period_returns)
    mean_return = sum(period_returns) / count if count else 0.0
    variance = sum((value - mean_return) ** 2 for value in period_returns) / (count - 1) if count > 1 else 0.0
    volatility = math.sqrt(variance)
    sharpe = (mean_return / volatility * math.sqrt(body.annualization_periods)) if volatility else None
    annualized_return = (equity ** (body.annualization_periods / count) - 1.0) * 100 if count and equity > 0 else (-100.0 if equity == 0 else 0.0)
    benchmark_return = (opens[-1] / opens[body.slow_period] - 1.0) * 100
    return {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "strategy": "long_only_sma_crossover",
        "parameters": {
            "fast_period": body.fast_period,
            "slow_period": body.slow_period,
            "fee_bps_per_side": body.fee_bps_per_side,
            "slippage_bps_per_side": body.slippage_bps_per_side,
            "annualization_periods": body.annualization_periods,
        },
        "execution_model": {
            "signal": "moving averages calculated from closes strictly before the execution bar",
            "fill": "next bar open",
            "return_interval": "open_to_next_open",
            "cost_model": "fee plus slippage in basis points per side, charged on position changes",
            "positioning": "long only, binary exposure, no leverage",
            "final_position": "liquidated at final available open",
        },
        "performance": {
            "initial_equity": 1.0,
            "final_equity": round(equity, 10),
            "total_return_pct": round((equity - 1.0) * 100, 6),
            "annualized_return_pct": round(annualized_return, 6),
            "annualized_volatility_pct": round(volatility * math.sqrt(body.annualization_periods) * 100, 6),
            "sharpe_ratio": round(sharpe, 6) if sharpe is not None else None,
            "maximum_drawdown_pct": round(max_drawdown * 100, 6),
            "benchmark_buy_and_hold_return_pct": round(benchmark_return, 6),
            "completed_position_changes": len(trades),
            "turnover_units": round(turnover_total, 6),
            "evaluated_periods": count,
        },
        "equity_curve": equity_curve,
        "trades": trades,
        "limitations": [
            "Historical simulation on caller-supplied OHLCV bars only; no live or licensed market feed is connected.",
            "Open prices are treated as executable reference prices; spread, market impact, queue position and latency are not modelled.",
            "Fee and slippage assumptions are user-supplied and may not match actual venue costs.",
            "No dividends, funding, borrow, corporate actions, delisted instruments or survivorship-bias correction.",
            "No walk-forward or out-of-sample validation is performed by this endpoint.",
            "This is a research simulation, not investment advice or an execution instruction.",
        ],
    }


@router.post("/backtest")
async def quant_backtest(
    body: BacktestRequest, request: Request,
    key: dict = Depends(require_api_key),
):
    result = run_sma_backtest(body)
    await record_usage(request, key, "quant_backtest", len(body.bars), 200, {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "strategy": "long_only_sma_crossover",
        "observations": len(body.bars),
    })
    return {"object": "oriom7_quant_backtest", **result}
