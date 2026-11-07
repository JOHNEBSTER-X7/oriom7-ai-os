"""Historical multi-asset portfolio risk diagnostics; research-only, no execution."""
from __future__ import annotations

import math
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from commercial_api import record_usage, require_api_key
from quant_backtest import BacktestBar

router = APIRouter(prefix="/v1/quant/risk", tags=["quantitative-risk"])


class RiskAsset(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    weight: float = Field(ge=0, le=1)
    bars: list[BacktestBar] = Field(min_length=61, max_length=5000)


class StressScenario(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    shocks: dict[str, float] = Field(min_length=1, max_length=20)


class PortfolioRiskRequest(BaseModel):
    assets: list[RiskAsset] = Field(min_length=2, max_length=20)
    confidence_level: Literal[0.95, 0.99] = 0.95
    annualization_periods: int = Field(default=252, ge=1, le=100000)
    annual_risk_free_rate: float = Field(default=0.0, ge=-0.5, le=1.0)
    stress_scenarios: list[StressScenario] = Field(default=[], max_length=20)

    @model_validator(mode="after")
    def validate_portfolio(self):
        symbols = [asset.symbol.upper() for asset in self.assets]
        if len(set(symbols)) != len(symbols):
            raise ValueError("Asset symbols must be unique")
        if abs(sum(asset.weight for asset in self.assets) - 1.0) > 1e-6:
            raise ValueError("Long-only portfolio weights must sum to 1.0")
        reference = [bar.timestamp for bar in self.assets[0].bars]
        for asset in self.assets:
            stamps = [bar.timestamp for bar in asset.bars]
            if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
                raise ValueError(f"{asset.symbol}: bars must be strictly chronological with unique timestamps")
            if stamps != reference:
                raise ValueError("All assets must have identical aligned timestamps")
            for bar in asset.bars:
                if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
                    raise ValueError(f"{asset.symbol}: OHLC values are inconsistent")
        known = set(symbols)
        for scenario in self.stress_scenarios:
            if any(symbol.upper() not in known for symbol in scenario.shocks):
                raise ValueError("Stress scenario shocks must reference assets in the portfolio")
            if any(not math.isfinite(shock) or shock < -1 or shock > 5 for shock in scenario.shocks.values()):
                raise ValueError("Stress shocks must be finite returns between -100% and +500%")
        return self


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(right) != len(left):
        return None
    left_mean, right_mean = sum(left) / len(left), sum(right) / len(right)
    left_std, right_std = _sample_std(left), _sample_std(right)
    if left_std == 0 or right_std == 0:
        return None
    covariance = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right)) / (len(left) - 1)
    return covariance / (left_std * right_std)


def run_portfolio_risk(body: PortfolioRiskRequest) -> dict:
    symbols = [asset.symbol.upper() for asset in body.assets]
    weights = [asset.weight for asset in body.assets]
    asset_returns = {
        asset.symbol.upper(): [asset.bars[i].close / asset.bars[i - 1].close - 1.0 for i in range(1, len(asset.bars))]
        for asset in body.assets
    }
    period_count = len(next(iter(asset_returns.values())))
    portfolio_returns = [
        sum(weights[j] * asset_returns[symbols[j]][i] for j in range(len(symbols)))
        for i in range(period_count)
    ]
    mean_return = sum(portfolio_returns) / period_count
    volatility = _sample_std(portfolio_returns)
    quantile_return = _quantile(portfolio_returns, 1.0 - body.confidence_level)
    tail = [value for value in portfolio_returns if value <= quantile_return]
    expected_shortfall_return = sum(tail) / len(tail) if tail else quantile_return
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in portfolio_returns:
        equity *= max(0.0, 1.0 + value)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
    annualized_volatility = volatility * math.sqrt(body.annualization_periods)
    period_risk_free = (1 + body.annual_risk_free_rate) ** (1 / body.annualization_periods) - 1
    sharpe = ((mean_return - period_risk_free) / volatility * math.sqrt(body.annualization_periods)) if volatility else None
    variance = volatility ** 2
    contributions = {}
    for symbol, weight in zip(symbols, weights):
        covariance = sum((asset_returns[symbol][i] - sum(asset_returns[symbol]) / period_count) *
                        (portfolio_returns[i] - mean_return) for i in range(period_count)) / max(1, period_count - 1)
        contributions[symbol] = round(weight * covariance / variance, 8) if variance else None
    correlation = {
        left: {right: (round(_correlation(asset_returns[left], asset_returns[right]), 8)
                       if _correlation(asset_returns[left], asset_returns[right]) is not None else None)
               for right in symbols}
        for left in symbols
    }
    stress = []
    for scenario in body.stress_scenarios:
        pnl = sum(weight * scenario.shocks.get(symbol, scenario.shocks.get(symbol.lower(), 0.0))
                  for symbol, weight in zip(symbols, weights))
        stress.append({"name": scenario.name, "portfolio_return_pct": round(pnl * 100, 6),
                       "portfolio_loss_pct": round(max(0.0, -pnl) * 100, 6)})
    hhi = sum(weight ** 2 for weight in weights)
    return {
        "object": "oriom7_portfolio_risk",
        "methodology": "historical_close_to_close_weighted_returns",
        "assets": [{"symbol": symbol, "weight": weight} for symbol, weight in zip(symbols, weights)],
        "history": {"aligned_observations": period_count + 1, "return_periods": period_count,
                    "start": body.assets[0].bars[0].timestamp.isoformat(),
                    "end": body.assets[0].bars[-1].timestamp.isoformat()},
        "portfolio_performance": {
            "mean_period_return_pct": round(mean_return * 100, 8),
            "cumulative_return_pct": round((equity - 1) * 100, 8),
            "annualized_volatility_pct": round(annualized_volatility * 100, 8),
            "sharpe_ratio": round(sharpe, 8) if sharpe is not None else None,
            "maximum_drawdown_pct": round(max_drawdown * 100, 8),
        },
        "historical_tail_risk": {
            "confidence_level": body.confidence_level,
            "value_at_risk_loss_pct": round(max(0.0, -quantile_return) * 100, 8),
            "expected_shortfall_loss_pct": round(max(0.0, -expected_shortfall_return) * 100, 8),
            "tail_observations": len(tail),
            "quantile_return_pct": round(quantile_return * 100, 8),
        },
        "concentration": {"herfindahl_hirschman_index": round(hhi, 8),
                          "effective_number_of_positions": round(1 / hhi, 8) if hhi else None,
                          "largest_weight_pct": round(max(weights) * 100, 6)},
        "risk_contribution_fraction": contributions,
        "correlation_matrix": correlation,
        "stress_scenarios": stress,
        "warnings": [
            "Historical VaR and expected shortfall are empirical estimates and can understate losses outside the observed sample.",
            "Close-to-close returns omit intraperiod gaps, liquidity, spread, market impact, financing, taxes and execution costs.",
            "Weights are static long-only exposures; no rebalancing, leverage, shorting, derivatives or currency conversion is modelled.",
            "Stress shocks are user-supplied deterministic scenarios, not forecasts or probability-weighted outcomes.",
            "No licensed market feed, instrument validation, survivorship correction or live execution is connected.",
            "Research and risk diagnostics only; not investment advice or a guarantee of maximum loss.",
        ],
    }


@router.post("/portfolio")
async def portfolio_risk(body: PortfolioRiskRequest, request: Request,
                         key: dict = Depends(require_api_key)):
    result = run_portfolio_risk(body)
    observations = sum(len(asset.bars) for asset in body.assets)
    await record_usage(request, key, "quant_portfolio_risk", observations, 200, {
        "asset_count": len(body.assets), "return_periods": result["history"]["return_periods"],
        "confidence_level": body.confidence_level,
    })
    return result
