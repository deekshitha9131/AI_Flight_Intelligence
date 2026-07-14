"""
ml/feature_engineering/engineer.py
------------------------------------
Feature engineering for the flight price prediction pipeline.

Creates:
  - Temporal features (days_until_departure, month, weekday, week_of_year)
  - Time-of-day buckets (morning / afternoon / evening / night)
  - Boolean flags (is_weekend, is_round_trip, is_domestic, is_holiday_period)
  - Route and airline aggregation features (frequency, popularity)
  - Price-per-minute (for training data only)
  - Label-encoded categorical columns

Usage::

    from ml.feature_engineering.engineer import FeatureEngineer
    fe = FeatureEngineer()
    df_features = fe.fit_transform(df_train)
    df_test_features = fe.transform(df_test)
    encoders = fe.encoders
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from ml.config.settings import CATEGORICAL_COLUMNS, FEATURE_COLUMNS
from ml.utils.logger import get_logger

logger = get_logger(__name__)

# Holiday months (approximate peak travel periods)
_HOLIDAY_MONTHS = {1, 4, 6, 7, 8, 10, 12}

# Domestic route origins (Indian subcontinent)
_DOMESTIC_ORIGINS = {"DEL", "BOM", "HYD", "BLR", "MAA", "CCU", "AMD", "PNQ"}


def _time_bucket(hour: int) -> str:
    """Map an hour (0–23) to a time-of-day bucket."""
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


class FeatureEngineer:
    """Fit-transform feature engineering for the ML pipeline.

    Maintains label encoders so the same encoding is applied consistently
    to training and inference data.
    """

    def __init__(self) -> None:
        self._encoders: dict[str, LabelEncoder] = {}
        self._route_freq: dict[str, int] = {}
        self._airline_pop: dict[str, int] = {}
        self._fitted: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit on training data and return the engineered feature DataFrame."""
        df = df.copy()
        df = self._add_temporal_features(df)
        df = self._add_flag_features(df)
        df = self._add_aggregation_features(df, fit=True)
        df = self._add_price_per_minute(df)
        df = self._encode_categoricals(df, fit=True)
        self._fitted = True
        logger.info(
            "FeatureEngineer.fit_transform: %d rows, %d columns.",
            len(df),
            len(df.columns),
        )
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform new data using the fitted encoders."""
        if not self._fitted:
            raise RuntimeError(
                "FeatureEngineer must be fitted before calling transform()."
            )
        df = df.copy()
        df = self._add_temporal_features(df)
        df = self._add_flag_features(df)
        df = self._add_aggregation_features(df, fit=False)
        df = self._encode_categoricals(df, fit=False)
        return df

    @property
    def encoders(self) -> dict[str, LabelEncoder]:
        """Return the fitted label encoders."""
        return self._encoders

    def get_feature_columns(self) -> list[str]:
        """Return the ordered list of feature columns for the model."""
        return [c for c in FEATURE_COLUMNS if c != "price_per_minute"]

    # ------------------------------------------------------------------
    # Private steps
    # ------------------------------------------------------------------

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add date-derived features."""
        today = datetime.now(timezone.utc).date()

        if "departure_date" in df.columns:
            dep = pd.to_datetime(df["departure_date"], errors="coerce")
            df["departure_month"] = dep.dt.month.fillna(6).astype(int)
            df["departure_day_of_week"] = dep.dt.dayofweek.fillna(0).astype(int)
            df["departure_week_of_year"] = (
                dep.dt.isocalendar().week.fillna(1).astype(int)
            )

            # Days until departure (from today)
            today_ts = pd.Timestamp(today)
            df["days_until_departure"] = (
                (dep - today_ts).dt.days.fillna(30).clip(lower=0).astype(int)
            )
        else:
            df["departure_month"] = 6
            df["departure_day_of_week"] = 0
            df["departure_week_of_year"] = 1
            df["days_until_departure"] = 30

        return df

    def _add_flag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add boolean indicator features."""
        # Weekend flag
        if "departure_day_of_week" in df.columns:
            df["is_weekend"] = df["departure_day_of_week"].isin([5, 6]).astype(int)
        else:
            df["is_weekend"] = 0

        # Round-trip flag
        if "trip_type" in df.columns:
            df["is_round_trip"] = (df["trip_type"] == "ROUND_TRIP").astype(int)
        elif "return_date" in df.columns:
            df["is_round_trip"] = df["return_date"].notna().astype(int)
        else:
            df["is_round_trip"] = 0

        # Domestic flag
        if "origin" in df.columns and "destination" in df.columns:
            df["is_domestic"] = (
                df["origin"].isin(_DOMESTIC_ORIGINS)
                & df["destination"].isin(_DOMESTIC_ORIGINS)
            ).astype(int)
        else:
            df["is_domestic"] = 0

        # Holiday period flag
        if "departure_month" in df.columns:
            df["is_holiday_period"] = (
                df["departure_month"].isin(_HOLIDAY_MONTHS).astype(int)
            )
        else:
            df["is_holiday_period"] = 0

        # Time-of-day buckets
        if "departure_hour" in df.columns:
            df["departure_time_bucket"] = df["departure_hour"].apply(_time_bucket)
        else:
            df["departure_time_bucket"] = "morning"

        if "arrival_hour" in df.columns:
            df["arrival_time_bucket"] = df["arrival_hour"].apply(_time_bucket)
        else:
            df["arrival_time_bucket"] = "morning"

        # Route composite key
        if "origin" in df.columns and "destination" in df.columns:
            df["route"] = df["origin"] + "-" + df["destination"]
        else:
            df["route"] = "UNK-UNK"

        return df

    def _add_aggregation_features(self, df: pd.DataFrame, *, fit: bool) -> pd.DataFrame:
        """Add route frequency and airline popularity features."""
        if fit:
            if "route" in df.columns:
                self._route_freq = df["route"].value_counts().to_dict()
            if "airline" in df.columns:
                self._airline_pop = df["airline"].value_counts().to_dict()

        if "route" in df.columns:
            df["route_frequency"] = (
                df["route"].map(self._route_freq).fillna(1).astype(int)
            )
        else:
            df["route_frequency"] = 1

        if "airline" in df.columns:
            df["airline_popularity"] = (
                df["airline"].map(self._airline_pop).fillna(1).astype(int)
            )
        else:
            df["airline_popularity"] = 1

        return df

    def _add_price_per_minute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-per-minute feature (training data only)."""
        if "price" in df.columns and "flight_duration_minutes" in df.columns:
            duration = df["flight_duration_minutes"].replace(0, np.nan)
            df["price_per_minute"] = (df["price"] / duration).fillna(0).round(4)
        return df

    def _encode_categoricals(self, df: pd.DataFrame, *, fit: bool) -> pd.DataFrame:
        """Label-encode categorical columns."""
        for col in CATEGORICAL_COLUMNS:
            if col not in df.columns:
                df[f"{col}_encoded"] = 0
                continue

            encoded_col = f"{col}_encoded"
            df[col] = df[col].astype(str).fillna("UNKNOWN")

            if fit:
                le = LabelEncoder()
                le.fit(df[col])
                self._encoders[col] = le
                df[encoded_col] = le.transform(df[col])
            else:
                le = self._encoders.get(col)
                if le is None:
                    df[encoded_col] = 0
                else:
                    # Handle unseen labels gracefully
                    known = set(le.classes_)
                    df[col] = df[col].apply(
                        lambda x: x if x in known else le.classes_[0]
                    )
                    df[encoded_col] = le.transform(df[col])

        return df
