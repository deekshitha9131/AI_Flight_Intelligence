from datetime import date, timedelta

import pandas as pd

from ml.data.cleaner import DataCleaner
from ml.data.validator import DataValidator
from ml.feature_engineering.engineer import FeatureEngineer


def _frame() -> pd.DataFrame:
    return pd.DataFrame([{
        "origin": "HYD", "destination": "DXB", "departure_date": str(date.today() + timedelta(days=30)),
        "return_date": None, "airline": "EK", "cabin_class": "ECONOMY", "adults": 1,
        "children": 0, "infants": 0, "stops": 0, "trip_type": "ONE_WAY", "currency": "USD",
        "flight_duration_minutes": 240, "departure_hour": 9, "arrival_hour": 12, "price": 350,
    }])


def test_clean_validate_and_engineer() -> None:
    raw = _frame()
    assert DataValidator().validate(raw).passed
    clean = DataCleaner().clean(raw)
    features = FeatureEngineer().fit_transform(clean)
    assert "days_until_departure" in features
    assert "origin_encoded" in features
