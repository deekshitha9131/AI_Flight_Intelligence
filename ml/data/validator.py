"""
ml/data/validator.py
---------------------
Dataset validation for the ML pipeline.

Validates:
  - Required columns present
  - Missing values
  - Invalid IATA airport codes
  - Negative or zero prices
  - Invalid dates
  - Duplicate records
  - Invalid cabin classes
  - Currency inconsistencies

Usage::

    from ml.data.validator import DataValidator
    report = DataValidator().validate(df)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ml.config.settings import (
    AIRLINES,
    ARTIFACTS_DIR,
    CABIN_CLASSES,
    CURRENCIES,
    IATA_CODES,
    RAW_COLUMNS,
    TRIP_TYPES,
)
from ml.utils.logger import get_logger

logger = get_logger(__name__)

_VALID_IATA = set(IATA_CODES)
_VALID_CABIN = set(CABIN_CLASSES)
_VALID_CURRENCY = set(CURRENCIES)
_VALID_TRIP_TYPE = set(TRIP_TYPES)


@dataclass
class ValidationReport:
    """Structured validation report."""

    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    issues: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    passed: bool = False
    validated_at: str = ""

    def add_issue(self, category: str, message: str) -> None:
        self.issues.setdefault(category, []).append(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "issues": self.issues,
            "warnings": self.warnings,
            "passed": self.passed,
            "validated_at": self.validated_at,
        }

    def save(self, path: Path | None = None) -> Path:
        out = path or (ARTIFACTS_DIR / "validation_report.json")
        out.write_text(json.dumps(self.to_dict(), indent=2))
        logger.info("Validation report saved -> %s", out)
        return out


class DataValidator:
    """Validates a flight price DataFrame against business rules."""

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """Run all validation checks and return a report.

        Args:
            df: Raw flight price DataFrame.

        Returns:
            ValidationReport with all findings.
        """
        report = ValidationReport(
            total_rows=len(df),
            validated_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info("DataValidator: validating %d rows...", len(df))

        invalid_mask = pd.Series([False] * len(df), index=df.index)

        # 1. Required columns
        missing_cols = [c for c in RAW_COLUMNS if c not in df.columns]
        if missing_cols:
            report.add_issue("missing_columns", f"Missing columns: {missing_cols}")
            logger.error("Missing required columns: %s", missing_cols)

        # 2. Missing values
        for col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                pct = null_count / len(df) * 100
                if pct > 50:
                    report.add_issue(
                        "missing_values",
                        f"Column '{col}' has {null_count} missing values ({pct:.1f}%)",
                    )
                else:
                    report.warnings.append(
                        f"Column '{col}' has {null_count} missing values ({pct:.1f}%)"
                    )

        # 3. Invalid IATA codes
        if "origin" in df.columns:
            bad_origin = ~df["origin"].isin(_VALID_IATA)
            if bad_origin.any():
                report.add_issue(
                    "invalid_iata",
                    f"{bad_origin.sum()} rows have invalid origin IATA codes.",
                )
                invalid_mask |= bad_origin

        if "destination" in df.columns:
            bad_dest = ~df["destination"].isin(_VALID_IATA)
            if bad_dest.any():
                report.add_issue(
                    "invalid_iata",
                    f"{bad_dest.sum()} rows have invalid destination IATA codes.",
                )
                invalid_mask |= bad_dest

        # 4. Negative or zero prices
        if "price" in df.columns:
            bad_price = df["price"] <= 0
            if bad_price.any():
                report.add_issue(
                    "invalid_price",
                    f"{bad_price.sum()} rows have non-positive prices.",
                )
                invalid_mask |= bad_price

        # 5. Invalid dates
        if "departure_date" in df.columns:
            try:
                parsed = pd.to_datetime(df["departure_date"], errors="coerce")
                bad_dates = parsed.isna()
                if bad_dates.any():
                    report.add_issue(
                        "invalid_dates",
                        f"{bad_dates.sum()} rows have unparseable departure_date.",
                    )
                    invalid_mask |= bad_dates
            except Exception as exc:
                report.add_issue("invalid_dates", f"Date parsing error: {exc}")

        # 6. Duplicate records
        if len(df) > 0:
            dup_cols = [
                c
                for c in [
                    "origin",
                    "destination",
                    "departure_date",
                    "airline",
                    "cabin_class",
                ]
                if c in df.columns
            ]
            if dup_cols:
                dup_count = df.duplicated(subset=dup_cols).sum()
                if dup_count > 0:
                    report.warnings.append(
                        f"{dup_count} duplicate records detected (same route/date/airline/cabin)."
                    )

        # 7. Invalid cabin classes
        if "cabin_class" in df.columns:
            bad_cabin = ~df["cabin_class"].isin(_VALID_CABIN)
            if bad_cabin.any():
                report.add_issue(
                    "invalid_cabin",
                    f"{bad_cabin.sum()} rows have invalid cabin_class values.",
                )
                invalid_mask |= bad_cabin

        # 8. Invalid trip types
        if "trip_type" in df.columns:
            bad_trip = ~df["trip_type"].isin(_VALID_TRIP_TYPE)
            if bad_trip.any():
                report.add_issue(
                    "invalid_trip_type",
                    f"{bad_trip.sum()} rows have invalid trip_type values.",
                )
                invalid_mask |= bad_trip

        # 9. Currency inconsistencies
        if "currency" in df.columns:
            bad_currency = ~df["currency"].isin(_VALID_CURRENCY)
            if bad_currency.any():
                report.warnings.append(
                    f"{bad_currency.sum()} rows have unrecognised currency codes."
                )

        # 10. Passenger sanity
        if all(c in df.columns for c in ["adults", "children", "infants"]):
            bad_pax = (df["adults"] < 1) | (df["infants"] > df["adults"])
            if bad_pax.any():
                report.add_issue(
                    "invalid_passengers",
                    f"{bad_pax.sum()} rows have invalid passenger counts.",
                )
                invalid_mask |= bad_pax

        report.invalid_rows = int(invalid_mask.sum())
        report.valid_rows = report.total_rows - report.invalid_rows
        report.passed = len(report.issues) == 0

        logger.info(
            "Validation complete: %d valid, %d invalid, passed=%s",
            report.valid_rows,
            report.invalid_rows,
            report.passed,
        )
        return report
