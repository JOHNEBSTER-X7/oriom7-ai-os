from datetime import datetime, timedelta, timezone

import quant_ml


def make_request(count=240):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = []
    for i in range(count):
        close = 100 * (1 + 0.0015) ** i * (1 + 0.015 * ((i % 11) / 11))
        open_price = close * 0.999
        bars.append({
            "timestamp": (start + timedelta(days=i)).isoformat(),
            "open": open_price, "high": close * 1.01,
            "low": open_price * 0.99, "close": close, "volume": 1000 + i,
        })
    return quant_ml.QuantMLRequest(symbol="TEST", timeframe="1d", bars=bars)


def test_dataset_is_chronological_and_splits_without_shuffle():
    dataset = quant_ml.build_chronological_dataset(make_request())
    partitions = dataset["partitions"]
    assert partitions["train"]["end_exclusive"] == partitions["validation"]["start"]
    assert partitions["validation"]["end_exclusive"] == partitions["test"]["start"]
    assert partitions["test"]["end_exclusive"] == dataset["sample_count"]
    assert dataset["rows"][0]["target_timestamp"] > dataset["rows"][0]["timestamp"]
    assert dataset["feature_names"] == quant_ml.FEATURE_NAMES


def test_scaler_is_fit_only_on_training_partition():
    dataset = quant_ml.build_chronological_dataset(make_request())
    train_end = dataset["partitions"]["train"]["end_exclusive"]
    for column in range(len(quant_ml.FEATURE_NAMES)):
        values = [row["features"][column] for row in dataset["rows"][:train_end]]
        mean = sum(values) / len(values)
        assert abs(mean) < 1e-9


def test_features_are_finite_and_target_is_next_bar_return():
    dataset = quant_ml.build_chronological_dataset(make_request())
    for row in dataset["rows"]:
        assert all(value == value and abs(value) < 100 for value in row["features"])
        assert abs(row["target_next_log_return"]) < 1


def test_rejects_nonchronological_history():
    request = make_request()
    values = [bar.model_dump() for bar in request.bars]
    values[10], values[11] = values[11], values[10]
    try:
        quant_ml.QuantMLRequest(symbol="TEST", timeframe="1d", bars=values)
        assert False, "unordered history must fail"
    except ValueError as exc:
        assert "chronological" in str(exc)


def test_training_returns_clear_optional_dependency_error_when_torch_absent(monkeypatch):
    # Training itself is exercised in a separate optional-ML environment.
    import builtins
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise ImportError("torch deliberately hidden in this test")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    try:
        quant_ml.train_pytorch_baseline(quant_ml.build_chronological_dataset(make_request()), 2, 0.001, 42)
        assert False, "missing torch should produce an actionable error"
    except RuntimeError as exc:
        assert "requirements-ml.txt" in str(exc)
