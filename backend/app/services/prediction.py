import logging
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from pathlib import Path

from app.repositories.prediction import PredictionRepository
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

class PredictionService:
    def __init__(self, db: Session):
        self.prediction_repo = PredictionRepository(db)
        self.model = None
        # Use pathlib to create a robust path to the model file
        # that works regardless of the current working directory
        self.model_path = Path(__file__).resolve().parent.parent.parent / "models" / "flight_price_model.joblib"
        self._load_model()

    def _load_model(self):
        """Load the trained model pipeline from disk."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info(f"Model loaded successfully from {self.model_path}")
            else:
                logger.warning(f"Model file not found at {self.model_path}. Predictions will not be available.")
                self.model = None
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self.model = None

    def _prepare_features(self, request: PredictionRequest) -> pd.DataFrame:
        """
        Prepare features for the model from the prediction request.
        Converts application data to the format expected by the historical model.
        """
        # Map application data to historical dataset format

        # City mapping (IATA to city name)
        city_mapping = {
            "DEL": "Delhi",
            "BOM": "Mumbai",
            "BLR": "Bangalore",
            "CCU": "Kolkata",
            "HYD": "Hyderabad",
            "MAA": "Chennai"
        }

        # Validate origin and destination are supported cities
        if request.origin not in city_mapping:
            raise ValueError(f"Unsupported origin city: {request.origin}")
        if request.destination not in city_mapping:
            raise ValueError(f"Unsupported destination city: {request.destination}")

        origin_city = city_mapping[request.origin]
        destination_city = city_mapping[request.destination]

        # Cabin class mapping (application to historical)
        cabin_mapping = {
            "ECONOMY": "Economy",
            "BUSINESS": "Business"
        }

        if request.cabin_class not in cabin_mapping:
            raise ValueError(f"Unsupported cabin class: {request.cabin_class}")

        historical_cabin = cabin_mapping[request.cabin_class]

        # Stops mapping (integer to categorical)
        if request.stops == 0:
            historical_stops = "zero"
        elif request.stops == 1:
            historical_stops = "one"
        else:  # 2 or more
            historical_stops = "two_or_more"

        # Duration conversion (minutes to hours)
        duration_hours = request.duration_minutes / 60.0

        # Days left calculation
        # Ensure departure_date is timezone naive for calculation
        departure_date = request.departure_date
        if departure_date.tzinfo is not None:
            departure_date = departure_date.replace(tzinfo=None)

        # Use current UTC time for days_left calculation
        current_date = datetime.utcnow()
        days_left = (departure_date - current_date).days

        # Validate days_left is in reasonable range (based on training data: 1-49)
        if days_left < 1:
            raise ValueError(f"Departure date must be at least 1 day in the future. Got {days_left} days left.")
        # Note: We allow days_left > 49 but will warn the user it's outside training range

        # Time features - convert HH:MM to categorical time of day
        # Historical dataset uses: Evening, Early_Morning, Morning, Afternoon, Night, Late_Night
        def time_to_category(time_str: str) -> str:
            try:
                # Parse HH:MM format
                hours, minutes = map(int, time_str.split(':'))
                total_minutes = hours * 60 + minutes

                # Define time categories (in minutes from midnight)
                # Early_Morning: 00:00 - 06:00 (0-360)
                # Morning: 06:00 - 12:00 (360-720)
                # Afternoon: 12:00 - 18:00 (720-1080)
                # Evening: 18:00 - 21:00 (1080-1260)
                # Night: 21:00 - 00:00 (1260-1440) and 00:00-04:00? Actually let's adjust
                # Based on common definitions and the unique values we saw:
                # Evening, Early_Morning, Morning, Afternoon, Night, Late_Night

                if 0 <= total_minutes < 360:  # 00:00-06:00
                    return "Early_Morning"
                elif 360 <= total_minutes < 540:  # 06:00-09:00
                    return "Morning"
                elif 540 <= total_minutes < 720:  # 09:00-12:00
                    return "Morning"
                elif 720 <= total_minutes < 900:  # 12:00-15:00
                    return "Afternoon"
                elif 900 <= total_minutes < 1080:  # 15:00-18:00
                    return "Afternoon"
                elif 1080 <= total_minutes < 1260:  # 18:00-21:00
                    return "Evening"
                elif 1260 <= total_minutes < 1320:  # 21:00-22:00
                    return "Night"
                else:  # 1320 <= total_minutes < 1440 (22:00-24:00)
                    return "Late_Night"
            except Exception as e:
                logger.warning(f"Could not parse time {time_str}, defaulting to Afternoon: {str(e)}")
                return "Afternoon"

        historical_departure_time = time_to_category(request.departure_time)
        historical_arrival_time = time_to_category(request.arrival_time)

        # Create feature dataframe
        features = pd.DataFrame({
            'airline': [request.airline],
            'source_city': [origin_city],
            'destination_city': [destination_city],
            'departure_time': [historical_departure_time],
            'stops': [historical_stops],
            'arrival_time': [historical_arrival_time],
            'class': [historical_cabin],
            'duration': [duration_hours],
            'days_left': [days_left]
        })

        return features

    def predict_price(self, request: PredictionRequest, user_id: str, flight_search_id: str) -> PredictionResponse:
        """
        Predict flight price using the trained model.
        """
        if self.model is None:
            raise Exception("Model not loaded. Please train the model first.")

        # Prepare features
        features_df = self._prepare_features(request)

        # Make prediction
        try:
            predicted_price = float(self.model.predict(features_df)[0])

            # Ensure prediction is non-negative
            if predicted_price < 0:
                predicted_price = 0.0

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise Exception(f"Failed to generate price prediction: {str(e)}")

        # Persist prediction
        prediction_record = self.prediction_repo.create(
            user_id=user_id,
            flight_search_id=flight_search_id,
            predicted_price=predicted_price,
            currency=request.currency,
            model_version="v1.0.0"
        )

        # Return response
        return PredictionResponse(
            predicted_price=predicted_price,
            currency=request.currency,
            is_estimate=True,
            model_version="v1.0.0"
        )

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        if self.model is None:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "model_path": str(self.model_path),
            "model_type": type(self.model).__name__ if hasattr(self.model, '__class__') else "Unknown"
        }