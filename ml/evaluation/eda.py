"""Automatic, headless exploratory data analysis exports."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ml.config.settings import ARTIFACTS_DIR, EDA_REPORT_FILE


def generate_eda(frame: pd.DataFrame, output_dir: Path = ARTIFACTS_DIR / "eda") -> Path:
    """Export distribution, comparison, trend, correlation, and quality reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "rows": len(frame),
        "columns": list(frame.columns),
        "missing_values": frame.isna().sum().to_dict(),
        "duplicates": int(frame.duplicated().sum()),
    }
    if "price" in frame:
        frame["price"].plot.hist(bins=30, title="Price distribution")
        plt.savefig(output_dir / "price_distribution.png", bbox_inches="tight")
        plt.close()
        report["price_summary"] = frame["price"].describe().to_dict()
    for column, name in (("airline", "airline_comparison"), ("route", "route_comparison")):
        if column in frame and "price" in frame:
            frame.groupby(column)["price"].mean().sort_values().tail(20).plot.bar(title=name)
            plt.savefig(output_dir / f"{name}.png", bbox_inches="tight")
            plt.close()
    numeric = frame.select_dtypes(include="number")
    if not numeric.empty:
        plt.imshow(numeric.corr(), aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
        plt.colorbar()
        plt.title("Correlation matrix")
        plt.savefig(output_dir / "correlation_matrix.png", bbox_inches="tight")
        plt.close()
    EDA_REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return EDA_REPORT_FILE
