"""
Flight Price Prediction Model Training Script

This script trains a regression model to predict flight prices based on historical data.
The model is trained on the Kaggle historical flight-price dataset and outputs
estimates in Indian Rupees (INR).

IMPORTANT: This model produces estimates and should not be used for actual bookings or
as a replacement for real-time flight provider pricing.
"""

import pandas as pd
import numpy as np
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_training_data(filepath: str) -> pd.DataFrame:
    """
    Load training data from CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        DataFrame containing the training data
    """
    logger.info(f"Loading training data from {filepath}")
    df = pd.read_csv(filepath)
    logger.info(f"Loaded {len(df)} training samples")
    return df

def prepare_features_and_target(df: pd.DataFrame) -> tuple:
    """
    Prepare features and target variable for training.

    Args:
        df: DataFrame containing the training data

    Returns:
        Tuple of (X, y) where X is features and y is target
    """
    logger.info("Preparing features and target...")

    # Define feature columns based on the historical dataset
    # Exclude Unnamed: 0 (index) and flight (identifier) as they are not useful for generalization
    # Exclude price as it's the target
    feature_columns = [
        'airline',
        'source_city',
        'destination_city',
        'departure_time',
        'stops',
        'arrival_time',
        'class',
        'duration',
        'days_left'
    ]

    target_column = 'price'

    # Verify all required columns exist
    missing_cols = [col for col in feature_columns + [target_column] if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in dataset: {missing_cols}")

    X = df[feature_columns]
    y = df[target_column]

    logger.info(f"Features: {list(X.columns)}")
    logger.info(f"Target: {target_column}")
    logger.info(f"Feature shape: {X.shape}")
    logger.info(f"Target shape: {y.shape}")

    return X, y

def create_preprocessing_pipeline() -> ColumnTransformer:
    """
    Create preprocessing pipeline for categorical and numeric features.

    Returns:
        ColumnTransformer preprocessing pipeline
    """
    logger.info("Creating preprocessing pipeline...")

    # Categorical features to one-hot encode
    categorical_features = [
        'airline',
        'source_city',
        'destination_city',
        'departure_time',
        'stops',
        'arrival_time',
        'class'
    ]

    # Numeric features to scale
    numeric_features = [
        'duration',
        'days_left'
    ]

    # Create transformers
    categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    numeric_transformer = StandardScaler()

    # Combine transformers
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='drop'  # Drop any columns not specified (shouldn't be any)
    )

    logger.info(f"Categorical features: {categorical_features}")
    logger.info(f"Numeric features: {numeric_features}")

    return preprocessor

def train_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """
    Train the flight price prediction model.

    Args:
        X: Feature DataFrame
        y: Target Series

    Returns:
        Trained Pipeline (preprocessing + model)
    """
    logger.info("Splitting data into train and test sets...")

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    logger.info(f"Training set size: {X_train.shape}")
    logger.info(f"Test set size: {X_test.shape}")

    # Create preprocessing pipeline
    preprocessor = create_preprocessing_pipeline()

    # Create the model
    # Using RandomForestRegressor as a good baseline for this type of problem
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        n_jobs=-1  # Use all available cores
    )

    # Create the full pipeline
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', model)
    ])

    # Train the model
    logger.info("Training model...")
    pipeline.fit(X_train, y_train)

    # Evaluate the model
    logger.info("Evaluating model...")
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    logger.info(f"Model Evaluation:")
    logger.info(f"  MAE: {mae:.2f} INR")
    logger.info(f"  MSE: {mse:.2f}")
    logger.info(f"  RMSE: {rmse:.2f} INR")
    logger.info(f"  R²: {r2:.4f}")

    # Print feature importance (top 10 features)
    try:
        # Get feature names after preprocessing
        if hasattr(pipeline.named_steps['preprocessor'], 'get_feature_names_out'):
            feature_names = pipeline.named_steps['preprocessor'].get_feature_names_out()
        else:
            # Fallback for older sklearn versions
            feature_names = pipeline.named_steps['preprocessor'].get_feature_names()

        # Get feature importances
        importances = pipeline.named_steps['regressor'].feature_importances_

        # Get top 10 features
        indices = np.argsort(importances)[::-1][:10]
        logger.info(f"\nTop 10 Features by Importance:")
        for i in indices:
            logger.info(f"  {feature_names[i]}: {importances[i]:.6f}")
    except Exception as e:
        logger.warning(f"Could not extract feature names for importance ranking: {str(e)}")

    return pipeline

def save_model(model: Pipeline, filepath: str) -> None:
    """
    Save the trained model to disk.

    Args:
        model: Trained Pipeline to save
        filepath: Path to save the model
    """
    # Create directory if it doesn't exist
    dirname = os.path.dirname(filepath)
    if dirname:  # Only create directory if there is a directory component
        os.makedirs(dirname, exist_ok=True)

    # Save the model
    joblib.dump(model, filepath)
    logger.info(f"Model saved to {filepath}")

def main():
    """Main training function."""
    logger.info("=" * 60)
    logger.info("Flight Price Prediction Model Training")
    logger.info("=" * 60)
    logger.info("IMPORTANT: This model is trained on historical data and")
    logger.info("produces estimates. It does NOT represent real-time")
    logger.info("flight pricing and should not be used for actual bookings.")
    logger.info("=" * 60)

    # Load training data
    data_path = "clean_dataset.csv"
    df = load_training_data(data_path)

    # Prepare features and target
    X, y = prepare_features_and_target(df)

    # Train model
    model = train_model(X, y)

    # Save model
    model_path = "flight_price_model.joblib"
    save_model(model, model_path)

    logger.info("=" * 60)
    logger.info("Training complete!")
    logger.info(f"Model saved to: {model_path}")
    logger.info("=" * 60)
    logger.info("REMINDER: This model predicts historical price equivalents")
    logger.info("and should be clearly labeled as an estimate in the application.")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()