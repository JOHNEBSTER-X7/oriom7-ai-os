"""Chronological feature engineering and optional PyTorch forecasting baseline."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from commercial_api import record_usage, require_api_key
from quant_backtest import BacktestBar

router = APIRouter(prefix="/v1/quant/ml", tags=["quantitative-ml-research"])
FEATURE_NAMES = ["return_1", "return_5", "return_10", "return_20", "volatility_20", "price_vs_sma_20"]


class QuantMLRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
    bars: list[BacktestBar] = Field(min_length=100, max_length=5000)

    @model_validator(mode="after")
    def validate_history(self):
        stamps = [bar.timestamp for bar in self.bars]
        if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
            raise ValueError("Bars must be strictly chronological with unique timestamps")
        for bar in self.bars:
            if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
                raise ValueError("OHLC values are inconsistent")
        return self


class QuantMLTrainRequest(QuantMLRequest):
    epochs: int = Field(default=20, ge=1, le=100)
    learning_rate: float = Field(default=0.001, gt=0, le=0.1)
    seed: int = Field(default=42, ge=0, le=1000000)


def build_chronological_dataset(body: QuantMLRequest) -> dict:
    closes = [float(bar.close) for bar in body.bars]
    rows = []
    for index in range(20, len(closes) - 1):
        history = closes[:index + 1]
        def ret(period: int) -> float:
            return math.log(history[-1] / history[-period - 1])
        recent_returns = [math.log(history[i] / history[i - 1]) for i in range(len(history) - 20, len(history))]
        mean = sum(recent_returns) / len(recent_returns)
        variance = sum((x - mean) ** 2 for x in recent_returns) / (len(recent_returns) - 1)
        sma20 = sum(history[-20:]) / 20
        features = [ret(1), ret(5), ret(10), ret(20), math.sqrt(variance), history[-1] / sma20 - 1.0]
        target = math.log(closes[index + 1] / closes[index])
        rows.append({
            "timestamp": body.bars[index].timestamp.isoformat(),
            "target_timestamp": body.bars[index + 1].timestamp.isoformat(),
            "features": features,
            "target_next_log_return": target,
        })
    if len(rows) < 30:
        raise ValueError("At least 30 engineered samples are required")
    train_end = int(len(rows) * 0.70)
    validation_end = int(len(rows) * 0.85)
    if train_end < 10 or validation_end - train_end < 5 or len(rows) - validation_end < 5:
        raise ValueError("Insufficient samples for chronological train, validation and test partitions")
    train_rows = rows[:train_end]
    means = [sum(row["features"][j] for row in train_rows) / len(train_rows) for j in range(len(FEATURE_NAMES))]
    scales = []
    for j, mean in enumerate(means):
        variance = sum((row["features"][j] - mean) ** 2 for row in train_rows) / len(train_rows)
        scales.append(math.sqrt(variance) or 1.0)
    for row in rows:
        row["features"] = [(value - means[j]) / scales[j] for j, value in enumerate(row["features"])]
    return {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "feature_names": FEATURE_NAMES,
        "target": "next_bar_log_return",
        "sample_count": len(rows),
        "partitions": {
            "train": {"start": 0, "end_exclusive": train_end, "samples": train_end},
            "validation": {"start": train_end, "end_exclusive": validation_end, "samples": validation_end - train_end},
            "test": {"start": validation_end, "end_exclusive": len(rows), "samples": len(rows) - validation_end},
        },
        "scaler": {"method": "z_score", "fit_partition": "train_only", "means": means, "scales": scales},
        "rows": rows,
        "warnings": [
            "Features use only bars available at each feature timestamp; target is the following bar's close-to-close log return.",
            "Train, validation and test partitions are chronological and non-shuffled.",
            "Feature scaling statistics are fitted on the training partition only.",
            "Caller-supplied OHLCV quality, corporate actions, survivorship bias and market microstructure are not independently verified.",
            "Forecasts are experimental research outputs, not trading signals, investment advice or execution instructions.",
        ],
    }


def train_pytorch_baseline(dataset: dict, epochs: int, learning_rate: float, seed: int) -> dict:
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("Optional PyTorch runtime is not installed. Install services/api/requirements-ml.txt.") from exc

    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    rows = dataset["rows"]
    partitions = dataset["partitions"]
    def tensors(name: str):
        part = partitions[name]
        selected = rows[part["start"]:part["end_exclusive"]]
        x = torch.tensor([row["features"] for row in selected], dtype=torch.float32)
        y = torch.tensor([[row["target_next_log_return"]] for row in selected], dtype=torch.float32)
        return x, y
    x_train, y_train = tensors("train")
    x_val, y_val = tensors("validation")
    x_test, y_test = tensors("test")
    model = nn.Sequential(nn.Linear(len(FEATURE_NAMES), 16), nn.ReLU(), nn.Linear(16, 8), nn.ReLU(), nn.Linear(8, 1))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.MSELoss()
    history = []
    best_state = None
    best_validation = float("inf")
    best_epoch = 0
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        loss = loss_fn(model(x_train), y_train)
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            validation_loss = float(loss_fn(model(x_val), y_val).item())
        history.append({"epoch": epoch + 1, "training_mse": float(loss.item()), "validation_mse": validation_loss})
        if validation_loss < best_validation:
            best_validation = validation_loss
            best_epoch = epoch + 1
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        predictions = model(x_test).flatten()
        test_mse = float(loss_fn(predictions, y_test.flatten()).item())
        actual = y_test.flatten()
        direction_accuracy = float(((predictions >= 0) == (actual >= 0)).float().mean().item())
        mean_prediction = float(predictions.mean().item())
    return {
        "model": "pytorch_mlp_regressor",
        "architecture": [len(FEATURE_NAMES), 16, 8, 1],
        "optimizer": "Adam",
        "loss": "mean_squared_error",
        "seed": seed,
        "epochs_requested": epochs,
        "best_validation_epoch": best_epoch,
        "best_validation_mse": best_validation,
        "test": {
            "mse": test_mse,
            "directional_accuracy": direction_accuracy,
            "mean_predicted_log_return": mean_prediction,
            "samples": int(y_test.shape[0]),
        },
        "training_history": history,
        "warnings": [
            "Validation data selects the best epoch; the test partition is evaluated only after model selection.",
            "Single chronological holdout and a small MLP do not establish predictive validity or statistical significance.",
            "No hyperparameter search, walk-forward model retraining, calibrated uncertainty, transaction-cost model or portfolio evaluation is included.",
            "Model weights are not persisted; this request-scoped baseline is not a deployable production model.",
            "Research output only; no trading signals or live execution.",
        ],
    }


@router.post("/dataset")
async def quant_ml_dataset(body: QuantMLRequest, request: Request, key: dict = Depends(require_api_key)):
    try:
        result = build_chronological_dataset(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await record_usage(request, key, "quant_ml_dataset", len(body.bars), 200, {
        "symbol": body.symbol.upper(), "samples": result["sample_count"],
    })
    return {"object": "oriom7_quant_ml_dataset", **result}


@router.post("/train")
async def quant_ml_train(body: QuantMLTrainRequest, request: Request, key: dict = Depends(require_api_key)):
    try:
        dataset = build_chronological_dataset(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        result = train_pytorch_baseline(dataset, body.epochs, body.learning_rate, body.seed)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    await record_usage(request, key, "quant_ml_train", dataset["sample_count"], 200, {
        "symbol": body.symbol.upper(), "samples": dataset["sample_count"],
        "epochs": body.epochs, "model": result["model"],
    })
    return {"object": "oriom7_quant_ml_training", "symbol": body.symbol.upper(),
            "timeframe": body.timeframe, "dataset": dataset["partitions"], **result}
