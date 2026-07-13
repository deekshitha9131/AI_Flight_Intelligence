"""Optional MLflow tracker that never prevents a local training run."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ml.config.settings import MLFLOW_EXPERIMENT_NAME, MLFLOW_MODEL_NAME, MLFLOW_TRACKING_URI
from ml.utils.logger import get_logger

logger = get_logger(__name__)


def track_training(model: Any, metrics: dict[str, float], params: dict[str, Any]) -> None:
    """Log an experiment and register its model when MLflow is installed."""
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError:
        logger.warning("MLflow is not installed; skipping experiment tracking.")
        return
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run():
        mlflow.log_params({key: str(value) for key, value in params.items()})
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=MLFLOW_MODEL_NAME)
