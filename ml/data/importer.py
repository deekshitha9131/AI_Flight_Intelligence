"""Incremental, validated imports for historical flight-price datasets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import httpx
import pandas as pd

from ml.config.settings import RAW_DIR
from ml.data.validator import DataValidator, ValidationReport
from ml.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetImporter:
    """Import CSV, JSON, or API data into one de-duplicated raw dataset."""

    def __init__(self, validator: DataValidator | None = None) -> None:
        self._validator = validator or DataValidator()

    def import_file(self, source: Path) -> tuple[pd.DataFrame, ValidationReport]:
        """Read a CSV/JSON source, normalise it, and return its validation report."""
        suffix = source.suffix.lower()
        if suffix == ".csv":
            frame = pd.read_csv(source)
        elif suffix in {".json", ".jsonl"}:
            frame = pd.read_json(source, lines=suffix == ".jsonl")
        else:
            raise ValueError("Only CSV, JSON, and JSONL files are supported.")
        return self._normalise(frame)

    def import_api(
        self, url: str, *, params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[pd.DataFrame, ValidationReport]:
        """Fetch a JSON array or a JSON object containing a ``data`` array."""
        response = httpx.get(url, params=params, headers=headers, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        records: Iterable[dict[str, Any]] = payload.get("data", []) if isinstance(payload, dict) else payload
        return self._normalise(pd.DataFrame(records))

    def append_incremental(
        self, frame: pd.DataFrame, *, dataset_name: str = "flights_raw.csv",
    ) -> Path:
        """Append only unseen rows and retain rejected records for auditability."""
        target = RAW_DIR / dataset_name
        existing = pd.read_csv(target) if target.exists() else pd.DataFrame()
        unified = pd.concat([existing, frame], ignore_index=True, sort=False)
        unified = unified.drop_duplicates().reset_index(drop=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        unified.to_csv(target, index=False)
        logger.info("Unified dataset saved to %s (%d rows).", target, len(unified))
        return target

    def _normalise(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
        frame = frame.copy()
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        for column in ("origin", "destination", "airline", "cabin_class", "trip_type", "currency"):
            if column in frame:
                frame[column] = frame[column].astype("string").str.strip().str.upper()
        report = self._validator.validate(frame)
        if report.invalid_rows:
            (RAW_DIR / "failed_records.json").write_text(
                json.dumps(report.to_dict(), indent=2), encoding="utf-8"
            )
        return frame.drop_duplicates().reset_index(drop=True), report
