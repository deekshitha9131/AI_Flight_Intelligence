"""
ml/utils/serialisation.py
--------------------------
Utilities for saving and loading ML model artifacts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from ml.config.settings import MODELS_DIR, ARTIFACTS_DIR, MODEL_FILE_PREFIX, PIPELINE_FILE_PREFIX, ENCODERS_FILE_PREFIX
from ml.utils.logger import get_logger

logger = get_logger(__name__)


def save_model(model: Any, version: str) -> Path:
    """Serialise a trained model to ``ml/models/``.

    Args:
        model:   Trained scikit-learn compatible estimator.
        version: Semantic version string (e.g. "1.2.0").

    Returns:
        Path to the saved artifact.
    """
    path = MODELS_DIR / f"{MODEL_FILE_PREFIX}_v{version}.joblib"
    joblib.dump(model, path)
    logger.info("Model saved → %s", path)
    return path


def save_pipeline(pipeline: Any, version: str) -> Path:
    """Serialise the preprocessing pipeline."""
    path = ARTIFACTS_DIR / f"{PIPELINE_FILE_PREFIX}_v{version}.joblib"
    joblib.dump(pipeline, path)
    logger.info("Pipeline saved → %s", path)
    return path


def save_encoders(encoders: dict[str, Any], version: str) -> Path:
    """Serialise label encoders dict."""
    path = ARTIFACTS_DIR / f"{ENCODERS_FILE_PREFIX}_v{version}.joblib"
    joblib.dump(encoders, path)
    logger.info("Encoders saved → %s", path)
    return path


def save_metadata(metadata: dict[str, Any]) -> Path:
    """Write model metadata JSON to artifacts/."""
    from ml.config.settings import METADATA_FILE
    metadata["saved_at"] = datetime.now(timezone.utc).isoformat()
    METADATA_FILE.write_text(json.dumps(metadata, indent=2, default=str))
    logger.info("Metadata saved → %s", METADATA_FILE)
    return METADATA_FILE


def load_model(version: str | None = None) -> Any:
    """Load a trained model from ``ml/models/``.

    If version is None, loads the lexicographically latest artifact.
    """
    path = _resolve_artifact(MODELS_DIR, MODEL_FILE_PREFIX, version)
    model = joblib.load(path)
    logger.info("Model loaded ← %s", path)
    return model


def load_pipeline(version: str | None = None) -> Any:
    """Load the preprocessing pipeline from ``ml/artifacts/``."""
    path = _resolve_artifact(ARTIFACTS_DIR, PIPELINE_FILE_PREFIX, version)
    pipeline = joblib.load(path)
    logger.info("Pipeline loaded ← %s", path)
    return pipeline


def load_encoders(version: str | None = None) -> dict[str, Any]:
    """Load label encoders from ``ml/artifacts/``."""
    path = _resolve_artifact(ARTIFACTS_DIR, ENCODERS_FILE_PREFIX, version)
    encoders = joblib.load(path)
    logger.info("Encoders loaded ← %s", path)
    return encoders


def load_metadata() -> dict[str, Any]:
    """Load model metadata JSON."""
    from ml.config.settings import METADATA_FILE
    if not METADATA_FILE.exists():
        return {}
    return json.loads(METADATA_FILE.read_text())


def get_latest_version() -> str | None:
    """Return the version string of the latest saved model, or None."""
    candidates = sorted(MODELS_DIR.glob(f"{MODEL_FILE_PREFIX}_v*.joblib"))
    if not candidates:
        return None
    stem = candidates[-1].stem
    parts = stem.split("_v")
    return parts[-1] if len(parts) > 1 else None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_artifact(directory: Path, prefix: str, version: str | None) -> Path:
    """Resolve the artifact path for a given prefix and optional version."""
    if version is not None:
        path = directory / f"{prefix}_v{version}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return path

    candidates = sorted(directory.glob(f"{prefix}_v*.joblib"))
    if not candidates:
        raise FileNotFoundError(
            f"No artifacts found in {directory} with prefix '{prefix}'."
        )
    return candidates[-1]
