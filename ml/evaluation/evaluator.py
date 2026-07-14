"""Metrics, model comparisons, and optional explainability reports."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)

from ml.config.settings import (
    ARTIFACTS_DIR,
    EVALUATION_REPORT_FILE,
    FEATURE_IMPORTANCE_FILE,
)


def evaluate_model(model: Any, x_test: Any, y_test: Any) -> dict[str, float]:
    """Return standard regression metrics and mean single-row prediction latency."""
    started = time.perf_counter()
    prediction = np.asarray(model.predict(x_test), dtype=float)
    elapsed = time.perf_counter() - started
    size = max(len(prediction), 1)
    return {
        "mae": float(mean_absolute_error(y_test, prediction)),
        "mse": float(mean_squared_error(y_test, prediction)),
        "rmse": float(mean_squared_error(y_test, prediction) ** 0.5),
        "r2": float(r2_score(y_test, prediction)),
        "mape": float(mean_absolute_percentage_error(y_test, prediction)),
        "prediction_latency_ms": elapsed * 1000 / size,
    }


def save_comparison(
    results: dict[str, dict[str, float]], path: Path = EVALUATION_REPORT_FILE
) -> Path:
    """Persist a machine-readable comparison report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return path


def export_feature_importance(
    model: Any, x_test: Any, y_test: Any, feature_names: list[str]
) -> Path:
    """Export native or permutation importance without requiring SHAP."""
    estimator = getattr(model, "named_steps", {}).get("model", model)
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(estimator.feature_importances_)
    elif hasattr(estimator, "coef_"):
        values = np.abs(np.asarray(estimator.coef_).ravel())
    else:
        values = permutation_importance(
            model, x_test, y_test, n_repeats=5, random_state=42
        ).importances_mean
    pd.DataFrame({"feature": feature_names, "importance": values}).sort_values(
        "importance", ascending=False
    ).to_csv(FEATURE_IMPORTANCE_FILE, index=False)
    return FEATURE_IMPORTANCE_FILE
