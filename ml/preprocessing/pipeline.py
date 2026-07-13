"""
ml/preprocessing/pipeline.py
------------------------------
Scikit-learn preprocessing pipeline for the ML training workflow.

Builds a ColumnTransformer that:
  - Scales numerical features with StandardScaler
  - Passes encoded categorical features through unchanged

Usage::

    from ml.preprocessing.pipeline import build_preprocessing_pipeline
    pipeline = build_preprocessing_pipeline(numerical_cols, categorical_encoded_cols)
    X_train_transformed = pipeline.fit_transform(X_train)
    X_test_transformed = pipeline.transform(X_test)
"""
from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.utils.logger import get_logger

logger = get_logger(__name__)


def build_preprocessing_pipeline(
    numerical_cols: list[str],
    categorical_encoded_cols: list[str],
) -> ColumnTransformer:
    """Build a ColumnTransformer preprocessing pipeline.

    Args:
        numerical_cols:           Columns to scale with StandardScaler.
        categorical_encoded_cols: Already-encoded integer columns (passthrough).

    Returns:
        Fitted-ready ColumnTransformer.
    """
    transformers = []

    if numerical_cols:
        transformers.append(
            ("num", StandardScaler(), numerical_cols)
        )

    if categorical_encoded_cols:
        transformers.append(
            ("cat", "passthrough", categorical_encoded_cols)
        )

    pipeline = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False,
    )

    logger.info(
        "Preprocessing pipeline built: %d numerical, %d categorical columns.",
        len(numerical_cols),
        len(categorical_encoded_cols),
    )
    return pipeline
