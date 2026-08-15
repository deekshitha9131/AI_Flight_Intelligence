"""
ml/config/settings.py
---------------------
Central configuration for the ML pipeline.

All paths, hyperparameters, feature lists, and MLflow settings live here.
Import this module anywhere in the pipeline instead of hard-coding values.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Root paths
# ---------------------------------------------------------------------------

ML_ROOT = Path(__file__).resolve().parents[1]  # ml/
REPO_ROOT = ML_ROOT.parent  # project root

DATA_DIR = ML_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DATASETS_DIR = DATA_DIR / "datasets"
MODELS_DIR = ML_ROOT / "models"
ARTIFACTS_DIR = ML_ROOT / "artifacts"
LOGS_DIR = ML_ROOT / "logs"

# Ensure directories exist at import time
for _d in (RAW_DIR, PROCESSED_DIR, DATASETS_DIR, MODELS_DIR, ARTIFACTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Dataset file names
# ---------------------------------------------------------------------------

RAW_DATASET_CSV = RAW_DIR / "flights_raw.csv"
CLEANED_DATASET_CSV = PROCESSED_DIR / "flights_cleaned.csv"
TRAIN_CSV = PROCESSED_DIR / "train.csv"
TEST_CSV = PROCESSED_DIR / "test.csv"

# ---------------------------------------------------------------------------
# Model artifact naming convention
# ---------------------------------------------------------------------------

MODEL_FILE_PREFIX = "flight_price_model"
PIPELINE_FILE_PREFIX = "preprocessing_pipeline"
ENCODERS_FILE_PREFIX = "label_encoders"
METADATA_FILE = ARTIFACTS_DIR / "model_metadata.json"
FEATURE_IMPORTANCE_FILE = ARTIFACTS_DIR / "feature_importance.csv"
EVALUATION_REPORT_FILE = ARTIFACTS_DIR / "evaluation_report.json"
EDA_REPORT_FILE = ARTIFACTS_DIR / "eda_report.json"

# ---------------------------------------------------------------------------
# Training settings
# ---------------------------------------------------------------------------

RANDOM_SEED: int = 42
TEST_SIZE: float = 0.20  # 80 / 20 split
CV_FOLDS: int = 5  # cross-validation folds
TARGET_COLUMN: str = "price"

# ---------------------------------------------------------------------------
# Feature lists
# ---------------------------------------------------------------------------

# Raw columns expected in the dataset
RAW_COLUMNS: list[str] = [
    "origin",
    "destination",
    "departure_date",
    "return_date",
    "airline",
    "cabin_class",
    "adults",
    "children",
    "infants",
    "stops",
    "trip_type",
    "currency",
    "flight_duration_minutes",
    "departure_hour",
    "arrival_hour",
    "price",
]

# Categorical columns that need label encoding
CATEGORICAL_COLUMNS: list[str] = [
    "origin",
    "destination",
    "airline",
    "cabin_class",
    "trip_type",
    "currency",
    "departure_time_bucket",
    "arrival_time_bucket",
    "route",
]

# Numerical columns that need scaling
NUMERICAL_COLUMNS: list[str] = [
    "days_until_departure",
    "adults",
    "children",
    "infants",
    "stops",
    "flight_duration_minutes",
    "departure_hour",
    "arrival_hour",
    "departure_month",
    "departure_day_of_week",
    "departure_week_of_year",
    "route_frequency",
    "airline_popularity",
]

# Final feature columns fed to the model (after engineering)
FEATURE_COLUMNS: list[str] = [
    "origin_encoded",
    "destination_encoded",
    "airline_encoded",
    "cabin_class_encoded",
    "trip_type_encoded",
    "currency_encoded",
    "departure_time_bucket_encoded",
    "arrival_time_bucket_encoded",
    "route_encoded",
    "days_until_departure",
    "adults",
    "children",
    "infants",
    "stops",
    "flight_duration_minutes",
    "departure_hour",
    "arrival_hour",
    "departure_month",
    "departure_day_of_week",
    "departure_week_of_year",
    "is_weekend",
    "is_round_trip",
    "is_domestic",
    "is_holiday_period",
    "route_frequency",
    "airline_popularity",
    "price_per_minute",
]

# ---------------------------------------------------------------------------
# Hyperparameter search spaces
# ---------------------------------------------------------------------------

HYPERPARAMS: dict = {
    "random_forest": {
        "n_estimators": [100, 200, 300],
        "max_depth": [None, 10, 20, 30],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    },
    "gradient_boosting": {
        "n_estimators": [100, 200],
        "learning_rate": [0.05, 0.1, 0.2],
        "max_depth": [3, 5, 7],
        "subsample": [0.8, 1.0],
    },
    "xgboost": {
        "n_estimators": [100, 200],
        "learning_rate": [0.05, 0.1],
        "max_depth": [4, 6, 8],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
    },
    "lightgbm": {
        "n_estimators": [100, 200],
        "learning_rate": [0.05, 0.1],
        "num_leaves": [31, 63, 127],
        "subsample": [0.8, 1.0],
    },
}

# ---------------------------------------------------------------------------
# MLflow settings
# ---------------------------------------------------------------------------

MLFLOW_TRACKING_URI: str = (ML_ROOT / "mlflow_tracking").as_uri()

MLFLOW_EXPERIMENT_NAME: str = "flight_price_prediction"
MLFLOW_MODEL_NAME: str = "flight_price_model"

OPTIONAL_MODEL_PACKAGES: tuple[str, ...] = ("xgboost", "lightgbm")

# ---------------------------------------------------------------------------
# Data generation (synthetic dataset for development)
# ---------------------------------------------------------------------------

SYNTHETIC_DATASET_SIZE: int = 10_000

IATA_CODES: list[str] = [
    "DEL",
    "BOM",
    "HYD",
    "BLR",
    "MAA",
    "CCU",
    "AMD",
    "PNQ",
    "DXB",
    "AUH",
    "DOH",
    "KWI",
    "BAH",
    "MCT",
    "LHR",
    "CDG",
    "FRA",
    "AMS",
    "MAD",
    "FCO",
    "ZRH",
    "JFK",
    "LAX",
    "ORD",
    "DFW",
    "MIA",
    "SFO",
    "SIN",
    "BKK",
    "KUL",
    "CGK",
    "MNL",
    "HKG",
    "NRT",
    "ICN",
    "SYD",
    "MEL",
    "DPS",
]

AIRLINES: list[str] = [
    "AI",
    "6E",
    "SG",
    "UK",
    "IX",  # Indian carriers
    "EK",
    "EY",
    "QR",
    "WY",
    "GF",  # Gulf carriers
    "BA",
    "LH",
    "AF",
    "KL",
    "IB",
    "LX",  # European carriers
    "AA",
    "UA",
    "DL",
    "WN",  # US carriers
    "SQ",
    "TG",
    "MH",
    "GA",
    "PR",  # Asian carriers
]

CABIN_CLASSES: list[str] = ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
CURRENCIES: list[str] = ["USD", "EUR", "GBP", "INR", "AED", "SGD", "AUD"]
TRIP_TYPES: list[str] = ["ONE_WAY", "ROUND_TRIP"]
