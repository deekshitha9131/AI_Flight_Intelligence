"""
ml/data/cleaner.py
-------------------
Data cleaning for the ML pipeline.

Handles:
  - Missing value imputation
  - Outlier removal (IQR method)
  - Duplicate removal
  - Date normalisation
  - Currency normalisation (USD conversion)
  - Category standardisation
  - Column type casting

Usage::

    from ml.data.cleaner import DataCleaner
    cleaned_df = DataCleaner().clean(raw_df)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config.settings import (
    CABIN_CLASSES,
    CLEANED_DATASET_CSV,
    CURRENCIES,
    IATA_CODES,
    TRIP_TYPES,
)
from ml.utils.logger import get_logger

logger = get_logger(__name__)

_VALID_IATA = set(IATA_CODES)
_VALID_CABIN = set(CABIN_CLASSES)
_VALID_TRIP = set(TRIP_TYPES)

# Approximate USD conversion rates (static; replace with live rates in production)
_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "INR": 0.012,
    "AED": 0.272,
    "SGD": 0.74,
    "AUD": 0.65,
}


class DataCleaner:
    """Clean a raw flight price DataFrame."""

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the full cleaning pipeline.

        Args:
            df: Raw DataFrame (output of data collection / generation).

        Returns:
            Cleaned DataFrame ready for feature engineering.
        """
        logger.info("DataCleaner: starting with %d rows.", len(df))
        df = df.copy()

        df = self._cast_types(df)
        df = self._standardise_categories(df)
        df = self._remove_invalid_iata(df)
        df = self._impute_missing(df)
        df = self._remove_duplicates(df)
        df = self._remove_outliers(df)
        df = self._normalise_currency(df)
        df = self._validate_passengers(df)
        df = df.reset_index(drop=True)

        logger.info("DataCleaner: finished with %d rows.", len(df))
        return df

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cast columns to their correct dtypes."""
        int_cols = [
            "adults",
            "children",
            "infants",
            "stops",
            "flight_duration_minutes",
            "departure_hour",
            "arrival_hour",
        ]
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")

        for date_col in ["departure_date", "return_date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        return df

    def _standardise_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Uppercase and strip categorical string columns."""
        str_cols = [
            "origin",
            "destination",
            "airline",
            "cabin_class",
            "trip_type",
            "currency",
        ]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()

        # Standardise cabin class aliases
        cabin_map = {
            "ECO": "ECONOMY",
            "ECON": "ECONOMY",
            "PREM": "PREMIUM_ECONOMY",
            "PREM_ECO": "PREMIUM_ECONOMY",
            "BIZ": "BUSINESS",
            "BUSI": "BUSINESS",
            "FST": "FIRST",
            "FIRST_CLASS": "FIRST",
        }
        if "cabin_class" in df.columns:
            df["cabin_class"] = df["cabin_class"].replace(cabin_map)
            df.loc[~df["cabin_class"].isin(_VALID_CABIN), "cabin_class"] = "ECONOMY"

        if "trip_type" in df.columns:
            df.loc[~df["trip_type"].isin(_VALID_TRIP), "trip_type"] = "ONE_WAY"

        return df

    def _remove_invalid_iata(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows with unrecognised IATA codes."""
        before = len(df)
        if "origin" in df.columns:
            df = df[df["origin"].isin(_VALID_IATA)]
        if "destination" in df.columns:
            df = df[df["destination"].isin(_VALID_IATA)]
        removed = before - len(df)
        if removed:
            logger.info("Removed %d rows with invalid IATA codes.", removed)
        return df

    def _impute_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values with sensible defaults."""
        defaults: dict[str, object] = {
            "adults": 1,
            "children": 0,
            "infants": 0,
            "stops": 0,
            "cabin_class": "ECONOMY",
            "trip_type": "ONE_WAY",
            "currency": "USD",
            "flight_duration_minutes": (
                df["flight_duration_minutes"].median()
                if "flight_duration_minutes" in df.columns
                else 180
            ),
            "departure_hour": 8,
            "arrival_hour": 10,
        }
        for col, val in defaults.items():
            if col in df.columns:
                df[col] = df[col].fillna(val)

        # Drop rows where price or departure_date is missing (non-imputable)
        before = len(df)
        df = df.dropna(subset=["price", "departure_date"])
        removed = before - len(df)
        if removed:
            logger.info(
                "Dropped %d rows with missing price or departure_date.", removed
            )

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove exact duplicate rows."""
        before = len(df)
        dup_cols = [
            c
            for c in [
                "origin",
                "destination",
                "departure_date",
                "airline",
                "cabin_class",
                "adults",
            ]
            if c in df.columns
        ]
        df = df.drop_duplicates(subset=dup_cols, keep="first")
        removed = before - len(df)
        if removed:
            logger.info("Removed %d duplicate rows.", removed)
        return df

    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove price outliers using the IQR method."""
        if "price" not in df.columns:
            return df
        before = len(df)
        q1 = df["price"].quantile(0.01)
        q3 = df["price"].quantile(0.99)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        df = df[(df["price"] >= max(1.0, lower)) & (df["price"] <= upper)]
        removed = before - len(df)
        if removed:
            logger.info(
                "Removed %d price outliers (bounds: %.2f – %.2f).",
                removed,
                lower,
                upper,
            )
        return df

    def _normalise_currency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert all prices to USD using static exchange rates.

        Adds a ``price_usd`` column and keeps the original ``price`` column.
        """
        if "price" not in df.columns or "currency" not in df.columns:
            return df

        def _to_usd(row: pd.Series) -> float:
            rate = _USD_RATES.get(str(row["currency"]), 1.0)
            return round(float(row["price"]) * rate, 2)

        df["price_usd"] = df.apply(_to_usd, axis=1)
        logger.info("Currency normalised: price_usd column added.")
        return df

    def _validate_passengers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clamp passenger counts to valid ranges."""
        if "adults" in df.columns:
            df["adults"] = df["adults"].clip(lower=1, upper=9)
        if "children" in df.columns:
            df["children"] = df["children"].clip(lower=0, upper=9)
        if "infants" in df.columns:
            df["infants"] = df["infants"].clip(lower=0)
            if "adults" in df.columns:
                df["infants"] = df[["infants", "adults"]].min(axis=1)
        return df


def save_cleaned(df: pd.DataFrame, path=CLEANED_DATASET_CSV) -> None:
    """Save the cleaned DataFrame to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Cleaned dataset saved -> %s (%d rows)", path, len(df))

