from __future__ import annotations

import logging
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Relative to the repository root (three levels above backend/app/ai)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ML_MODELS_DIR = _REPO_ROOT / "ml" / "models"

# Ensure repo root is in sys.path so ml package classes (e.g. FeatureEngineer) can be unpickled
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Supported serialisation formats in preference order
_EXTENSIONS = (".joblib", ".pkl", ".pickle")

_MODEL_FILE_PREFIX = "flight_price_model"



class ModelLoader:
    """Loads and wraps the trained ML model for inference.

    Usage::

        loader = ModelLoader()
        loader.load()                          # call once at startup
        price = loader.predict(features)       # dict → float
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._pipeline: Any = None
        self._feature_engineer: Any = None
        self._feature_columns: list[str] | None = None
        self._model_version: str = "fallback-1.0.0"
        self._model_path: str = "none"
        self._is_fallback: bool = True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Discover and load the latest model artifact.

        Falls back to the statistical estimator if no artifact is found or
        if the required serialisation library is unavailable.
        """
        artifact = self._find_latest_artifact()
        if artifact is None:
            logger.warning(
                "ModelLoader: no trained model found in %s — using statistical fallback.",
                _ML_MODELS_DIR,
            )
            self._is_fallback = True
            return

        try:
            (
                self._model,
                self._pipeline,
                self._feature_engineer,
                self._feature_columns,
            ) = self._load_artifact(artifact)
            self._model_version = self._extract_version(artifact)
            self._model_path = str(artifact)
            self._is_fallback = False
            logger.info(
                "ModelLoader: loaded model v%s from %s",
                self._model_version,
                artifact.name,
            )
        except Exception as exc:
            logger.error(
                "ModelLoader: failed to load artifact %s — using fallback. Error: %s",
                artifact,
                exc,
            )
            self._is_fallback = True

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, features: dict[str, Any]) -> tuple[float, float | None]:
        """Return (predicted_price, confidence_score).

        confidence_score is None when the model does not support it.
        """
        start = time.monotonic()

        if self._is_fallback or self._model is None:
            price = self._statistical_fallback(features)
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.debug(
                "ModelLoader.predict | fallback price=%.2f elapsed=%.1fms",
                price,
                elapsed_ms,
            )
            return price, None

        try:
            feature_vector: Any = self._build_feature_vector(features)
            if self._feature_engineer is not None and self._feature_columns is not None:
                import pandas as pd

                feature_vector = self._feature_engineer.transform(
                    pd.DataFrame([features])
                )
                feature_vector = feature_vector[self._feature_columns]
            elif self._pipeline is not None:
                feature_vector = self._pipeline.transform([feature_vector])
            else:
                feature_vector = [feature_vector]

            raw = self._model.predict(feature_vector)
            price = float(raw[0])

            if price <= 0:
                logger.warning(
                    "ModelLoader.predict | model returned non-positive price (%.2f) — using statistical fallback.",
                    price,
                )
                price = self._statistical_fallback(features)

            # Attempt confidence via predict_proba or std (ensemble models)
            confidence: float | None = None
            if hasattr(self._model, "predict_proba"):
                try:
                    proba = self._model.predict_proba(feature_vector)
                    confidence = float(max(proba[0]))
                except Exception:
                    pass

            elapsed_ms = (time.monotonic() - start) * 1000
            logger.debug(
                "ModelLoader.predict | model price=%.2f confidence=%s elapsed=%.1fms",
                price,
                confidence,
                elapsed_ms,
            )
            return price, confidence

        except Exception as exc:
            logger.error(
                "ModelLoader.predict | model inference failed: %s — using fallback.",
                exc,
            )
            price = self._statistical_fallback(features)
            return price, None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def is_fallback(self) -> bool:
        return self._is_fallback

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_latest_artifact(self) -> Path | None:
        """Return the lexicographically latest model file, or None."""
        if not _ML_MODELS_DIR.exists():
            return None

        candidates = [
            f
            for f in _ML_MODELS_DIR.iterdir()
            if f.is_file()
            and f.name.startswith(_MODEL_FILE_PREFIX)
            and f.suffix in _EXTENSIONS
        ]
        if not candidates:
            return None

        return sorted(candidates)[-1]

    def _load_artifact(self, path: Path) -> tuple[Any, Any, Any, list[str] | None]:
        """Deserialise a model artifact.  Returns (model, pipeline)."""
        if path.suffix == ".joblib":
            import joblib  # type: ignore[import]

            obj = joblib.load(path)
        else:
            import pickle

            with open(path, "rb") as fh:
                obj = pickle.load(fh)  # noqa: S301

        # Support both bare model and {"model": ..., "pipeline": ...} dicts
        if isinstance(obj, dict):
            feature_columns = obj.get("feature_columns")
            return (
                obj.get("model"),
                obj.get("pipeline"),
                obj.get("feature_engineer"),
                feature_columns,
            )
        return obj, None, None, None

    @staticmethod
    def _extract_version(path: Path) -> str:
        """Extract version string from filename, e.g. 'v2.1.0'."""
        stem = path.stem  # e.g. flight_price_model_v2.1.0
        parts = stem.split("_v")
        return parts[-1] if len(parts) > 1 else "1.0.0"

    @staticmethod
    def _build_feature_vector(features: dict[str, Any]) -> list[Any]:
        """Convert the features dict to an ordered list for the model."""
        # This ordering must match the training pipeline's feature order.
        # Extend as the model evolves.
        return [
            features.get("origin_encoded", 0),
            features.get("destination_encoded", 0),
            features.get("days_until_departure", 30),
            features.get("is_round_trip", 0),
            features.get("adults", 1),
            features.get("children", 0),
            features.get("infants", 0),
            features.get("cabin_class_encoded", 0),
            features.get("stops", 0),
            features.get("departure_month", 6),
            features.get("departure_day_of_week", 0),
            features.get("airline_encoded", 0),
        ]

    @staticmethod
    def _statistical_fallback(features: dict[str, Any]) -> float:
        """Lightweight rule-based price estimator used when no model is loaded.

        Produces plausible prices based on cabin class, passenger count, and
        a simple distance proxy derived from the IATA codes.
        """
        cabin_multipliers = {
            "ECONOMY": 1.0,
            "PREMIUM_ECONOMY": 1.6,
            "BUSINESS": 3.2,
            "FIRST": 5.5,
        }
        cabin = str(features.get("cabin_class", "ECONOMY")).upper()
        multiplier = cabin_multipliers.get(cabin, 1.0)

        adults = int(features.get("adults", 1))
        children = int(features.get("children", 0))
        infants = int(features.get("infants", 0))
        total_pax = adults + children * 0.75 + infants * 0.1

        is_round_trip = int(features.get("is_round_trip", 0))
        trip_factor = 1.85 if is_round_trip else 1.0

        # Rough base price derived from origin/destination hash distance
        origin = str(features.get("origin", "AAA"))
        destination = str(features.get("destination", "BBB"))
        digest = sha256(f"{origin}{destination}".encode("utf-8")).hexdigest()
        route_seed = int(digest[:8], 16) % 800 + 200

        days_until = int(features.get("days_until_departure", 30))
        urgency_factor = (
            1.0 + max(0.0, (14 - days_until) / 14) * 0.4
        )  # up to +40% last 2 weeks

        base = route_seed * multiplier * trip_factor * urgency_factor * total_pax
        return round(base, 2)


# ---------------------------------------------------------------------------
# Module-level singleton — replaced by app.state.model_loader in production
# ---------------------------------------------------------------------------

_loader: ModelLoader | None = None


def get_model_loader() -> ModelLoader:
    """Return the module-level ModelLoader singleton (for testing only).

    In production the loader is stored on ``app.state.model_loader`` and
    injected via FastAPI dependency injection.
    """
    global _loader
    if _loader is None:
        _loader = ModelLoader()
        _loader.load()
    return _loader
