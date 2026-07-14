"""Configurable cross-validated model training."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeRegressor

from ml.config.settings import CV_FOLDS, RANDOM_SEED, TEST_SIZE
from ml.evaluation.evaluator import evaluate_model


@dataclass
class TrainingResult:
    name: str
    model: Any
    metrics: dict[str, float]
    training_time_seconds: float


class ModelTrainer:
    """Train supported estimators and choose the lowest-MAE model."""

    def __init__(
        self, *, test_size: float = TEST_SIZE, cv_folds: int = CV_FOLDS
    ) -> None:
        self.test_size = test_size
        self.cv_folds = cv_folds

    def train_and_select(
        self, x: pd.DataFrame, y: pd.Series, preprocessing: Any
    ) -> tuple[TrainingResult, list[TrainingResult]]:
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=self.test_size, random_state=RANDOM_SEED
        )
        results: list[TrainingResult] = []
        for name, estimator in self._estimators().items():
            pipeline = Pipeline(
                [("preprocessing", preprocessing), ("model", estimator)]
            )
            started = time.perf_counter()
            pipeline.fit(x_train, y_train)
            metrics = evaluate_model(pipeline, x_test, y_test)
            metrics["cross_validation_mae"] = float(
                -cross_val_score(
                    pipeline,
                    x_train,
                    y_train,
                    cv=self.cv_folds,
                    scoring="neg_mean_absolute_error",
                ).mean()
            )
            results.append(
                TrainingResult(name, pipeline, metrics, time.perf_counter() - started)
            )
        return min(results, key=lambda item: item.metrics["mae"]), results

    def tune(
        self,
        pipeline: Pipeline,
        parameters: dict[str, list[Any]],
        x: pd.DataFrame,
        y: pd.Series,
        *,
        randomized: bool = False,
        iterations: int = 20,
    ) -> Pipeline:
        """Tune a pipeline with GridSearchCV or RandomizedSearchCV."""
        search_class = RandomizedSearchCV if randomized else GridSearchCV
        kwargs: dict[str, Any] = {
            "cv": self.cv_folds,
            "scoring": "neg_mean_absolute_error",
            "n_jobs": -1,
        }
        if randomized:
            kwargs["n_iter"] = iterations
            kwargs["random_state"] = RANDOM_SEED
        search = search_class(pipeline, parameters, **kwargs)
        search.fit(x, y)
        return search.best_estimator_

    @staticmethod
    def _estimators() -> dict[str, Any]:
        estimators: dict[str, Any] = {
            "linear_regression": LinearRegression(),
            "decision_tree": DecisionTreeRegressor(random_state=RANDOM_SEED),
            "random_forest": RandomForestRegressor(
                n_estimators=200, random_state=RANDOM_SEED, n_jobs=-1
            ),
            "gradient_boosting": GradientBoostingRegressor(random_state=RANDOM_SEED),
            "extra_trees": ExtraTreesRegressor(
                n_estimators=200, random_state=RANDOM_SEED, n_jobs=-1
            ),
        }
        try:
            from xgboost import XGBRegressor

            estimators["xgboost"] = XGBRegressor(random_state=RANDOM_SEED, n_jobs=-1)
        except ImportError:
            pass
        try:
            from lightgbm import LGBMRegressor

            estimators["lightgbm"] = LGBMRegressor(
                random_state=RANDOM_SEED, n_jobs=-1, verbosity=-1
            )
        except ImportError:
            pass
        return estimators
