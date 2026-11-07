"""Evidence-aware quantitative research analytics; deliberately no order execution."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from commercial_api import require_api_key, record_usage

router = APIRouter(prefix="/v1/quant", tags=["quantitative-research"])


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class QuantAnalysisRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
    bars: list[OHLCVBar] = Field(min_length=30, max_length=5000)
    annualization_periods: int = Field(default=252, ge=1, le=100000)

    @model_validator(mode="after")
    def validate_bars(self):
        stamps = [bar.timestamp for bar in self.bars]
        if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
            raise ValueError("Bars must be strictly chronological with unique timestamps")
        for bar in self.bars:
            if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
                raise ValueError("OHLC values are inconsistent")
        return self


def _ema(values: list[float], period: int) -> float:
    alpha = 2.0 / (period + 1)
    value = sum(values[:period]) / period
    for sample in values[period:]:
        value = alpha * sample + (1 - alpha) * value
    return value


def analyse_bars(body: QuantAnalysisRequest) -> dict:
    closes = [bar.close for bar in body.bars]
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    volatility = math.sqrt(variance * body.annualization_periods) * 100
    gains, losses = [], []
    for previous, current in zip(closes[-15:-1], closes[-14:]):
        delta = current - previous
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain, avg_loss = sum(gains) / 14, sum(losses) / 14
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else 50.0 if avg_gain == avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss else 100.0
    peak, max_drawdown = closes[0], 0.0
    for close in closes:
        peak = max(peak, close)
        max_drawdown = max(max_drawdown, (peak - close) / peak)
    return {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "observations": len(body.bars),
        "latest_timestamp": body.bars[-1].timestamp.isoformat(),
        "latest_close": closes[-1],
        "indicators": {
            "ema_12": round(_ema(closes, 12), 8),
            "ema_26": round(_ema(closes, 26), 8),
            "rsi_14": round(rsi, 4),
            "annualized_realized_volatility_pct": round(volatility, 4),
            "max_observed_drawdown_pct": round(max_drawdown * 100, 4),
        },
        "methodology": {
            "return_type": "logarithmic",
            "volatility_estimator": "sample_standard_deviation_annualized",
            "rsi": "simple_14_period_gain_loss_average",
            "ema": "exponential_moving_average",
        },
        "limitations": [
            "Calculated only from caller-supplied OHLCV bars; no exchange feed is connected.",
            "No transaction costs, slippage, market impact, corporate actions or survivorship-bias correction.",
            "Indicators are descriptive research features, not trading signals or investment advice.",
            "No order routing, brokerage connection, leverage or automated execution is provided.",
        ],
    }


@router.post("/analyse")
async def quant_analyse(
    body: QuantAnalysisRequest, request: Request,
    key: dict = Depends(require_api_key),
):
    result = analyse_bars(body)
    await record_usage(request, key, "quant_research", len(body.bars), 200, {
        "symbol": body.symbol.upper(), "timeframe": body.timeframe,
        "observations": len(body.bars),
    })
    return {"object": "oriom7_quant_analysis", **result}
