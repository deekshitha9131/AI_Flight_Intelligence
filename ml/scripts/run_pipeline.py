"""Run cleaning, feature engineering, model selection, and artifact persistence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pandas as pd

from ml.config.settings import (
    CLEANED_DATASET_CSV,
    FEATURE_COLUMNS,
    RAW_DATASET_CSV,
    TARGET_COLUMN,
)
from ml.data.cleaner import DataCleaner, save_cleaned
from ml.data.validator import DataValidator
from ml.feature_engineering.engineer import FeatureEngineer
from ml.mlflow.tracker import track_training
from ml.preprocessing.pipeline import build_preprocessing_pipeline
from ml.training.trainer import ModelTrainer
from ml.utils.serialisation import save_metadata, save_model


def run(input_path: str, version: str) -> None:
    """Execute the reproducible training lifecycle for a historical dataset."""
    raw = pd.read_csv(input_path)
    report = DataValidator().validate(raw)
    report.save()
    cleaned = DataCleaner().clean(raw)
    save_cleaned(cleaned)
    engineer = FeatureEngineer()
    engineered = engineer.fit_transform(cleaned)
    columns = [column for column in FEATURE_COLUMNS if column != "price_per_minute"]
    x = engineered[columns]
    y = (
        engineered["price_usd"]
        if "price_usd" in engineered
        else engineered[TARGET_COLUMN]
    )
    numeric = [column for column in columns if not column.endswith("_encoded")]
    categorical = [column for column in columns if column.endswith("_encoded")]
    winner, _ = ModelTrainer().train_and_select(
        x, y, build_preprocessing_pipeline(numeric, categorical)
    )
    bundle = {
        "model": winner.model,
        "feature_engineer": engineer,
        "feature_columns": columns,
    }
    save_model(bundle, version)
    track_training(
        winner.model, winner.metrics, {"model_name": winner.name, "version": version}
    )
    save_metadata(
        {
            "version": version,
            "model_name": winner.name,
            "feature_columns": columns,
            "metrics": winner.metrics,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    print(f"Saved {winner.name} model v{version}; MAE={winner.metrics['mae']:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(RAW_DATASET_CSV))
    parser.add_argument(
        "--version", default=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )
    arguments = parser.parse_args()
    run(arguments.input, arguments.version)
