"""
ml/data/generate_dataset.py
----------------------------
Synthetic flight dataset generator for development and testing.

Generates a realistic CSV dataset with configurable size.
Prices are computed from a deterministic formula that captures:
  - Route distance proxy
  - Cabin class multiplier
  - Seasonality (month)
  - Booking urgency (days until departure)
  - Passenger count
  - Airline tier
  - Number of stops

Usage::

    python -m ml.data.generate_dataset --rows 10000 --output ml/data/raw/flights_raw.csv
"""

from __future__ import annotations

import argparse
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.config.settings import (
    AIRLINES,
    CABIN_CLASSES,
    CURRENCIES,
    IATA_CODES,
    RANDOM_SEED,
    RAW_DATASET_CSV,
    SYNTHETIC_DATASET_SIZE,
    TRIP_TYPES,
)
from ml.utils.logger import get_logger

logger = get_logger(__name__)

# Cabin class price multipliers
_CABIN_MULT = {"ECONOMY": 1.0, "PREMIUM_ECONOMY": 1.65, "BUSINESS": 3.3, "FIRST": 5.8}

# Airline tier multipliers (premium vs budget)
_AIRLINE_TIER: dict[str, float] = {
    "EK": 1.3,
    "QR": 1.3,
    "SQ": 1.25,
    "BA": 1.2,
    "LH": 1.15,
    "AF": 1.15,
    "AI": 1.0,
    "UA": 1.1,
    "AA": 1.1,
    "DL": 1.1,
    "6E": 0.75,
    "SG": 0.75,
    "UK": 0.8,
    "IX": 0.8,
    "WN": 0.8,
}

# Monthly seasonality index (1 = average)
_MONTH_FACTOR = [1.0, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 0.95, 0.9, 0.95, 1.3]

# Domestic route pairs (same region)
_DOMESTIC_ORIGINS = {"DEL", "BOM", "HYD", "BLR", "MAA", "CCU", "AMD", "PNQ"}


def generate_dataset(
    n_rows: int = SYNTHETIC_DATASET_SIZE, seed: int = RANDOM_SEED
) -> pd.DataFrame:
    """Generate a synthetic flight price dataset.

    Args:
        n_rows: Number of records to generate.
        seed:   Random seed for reproducibility.

    Returns:
        DataFrame with all raw columns.
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    logger.info("Generating synthetic dataset with %d rows (seed=%d)...", n_rows, seed)

    today = datetime.now(timezone.utc).date()
    rows: list[dict[str, Any]] = []

    for _ in range(n_rows):
        origin = rng.choice(IATA_CODES)
        destination = rng.choice([c for c in IATA_CODES if c != origin])
        airline = rng.choice(AIRLINES)
        cabin_class = rng.choices(CABIN_CLASSES, weights=[60, 15, 20, 5], k=1)[0]
        trip_type = rng.choices(TRIP_TYPES, weights=[55, 45], k=1)[0]
        currency = rng.choices(CURRENCIES, weights=[40, 20, 10, 15, 8, 4, 3], k=1)[0]
        adults = rng.choices([1, 2, 3, 4], weights=[50, 30, 12, 8], k=1)[0]
        children = rng.choices([0, 1, 2], weights=[70, 20, 10], k=1)[0]
        infants = rng.choices([0, 1], weights=[90, 10], k=1)[0]
        infants = min(infants, adults)
        stops = rng.choices([0, 1, 2], weights=[40, 45, 15], k=1)[0]

        days_ahead = rng.randint(1, 365)
        departure_date = today + timedelta(days=days_ahead)
        return_date = None
        if trip_type == "ROUND_TRIP":
            return_days = rng.randint(3, 30)
            return_date = departure_date + timedelta(days=return_days)

        departure_hour = rng.randint(0, 23)
        flight_duration_minutes = _estimate_duration(origin, destination, stops, rng)
        arrival_hour = (departure_hour + flight_duration_minutes // 60) % 24

        price = _compute_price(
            origin=origin,
            destination=destination,
            airline=airline,
            cabin_class=cabin_class,
            trip_type=trip_type,
            adults=adults,
            children=children,
            infants=infants,
            stops=stops,
            days_ahead=days_ahead,
            departure_month=departure_date.month,
            flight_duration_minutes=flight_duration_minutes,
            rng=rng,
        )

        rows.append(
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat() if return_date else None,
                "airline": airline,
                "cabin_class": cabin_class,
                "adults": adults,
                "children": children,
                "infants": infants,
                "stops": stops,
                "trip_type": trip_type,
                "currency": currency,
                "flight_duration_minutes": flight_duration_minutes,
                "departure_hour": departure_hour,
                "arrival_hour": arrival_hour,
                "price": round(price, 2),
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Dataset generated: %d rows, %d columns.", len(df), len(df.columns))
    return df


def _estimate_duration(
    origin: str, destination: str, stops: int, rng: random.Random
) -> int:
    """Estimate flight duration in minutes based on route hash and stops."""
    base = abs(hash(f"{origin}{destination}")) % 600 + 60  # 60–660 min
    stop_penalty = stops * rng.randint(60, 120)
    return base + stop_penalty


def _compute_price(
    *,
    origin: str,
    destination: str,
    airline: str,
    cabin_class: str,
    trip_type: str,
    adults: int,
    children: int,
    infants: int,
    stops: int,
    days_ahead: int,
    departure_month: int,
    flight_duration_minutes: int,
    rng: random.Random,
) -> float:
    """Compute a realistic price with noise."""
    # Base price from route hash (200–1200 USD)
    base = abs(hash(f"{origin}{destination}")) % 1000 + 200

    # Cabin multiplier
    cabin_mult = _CABIN_MULT.get(cabin_class, 1.0)

    # Airline tier
    airline_mult = _AIRLINE_TIER.get(airline, 1.0)

    # Seasonality
    season_mult = _MONTH_FACTOR[departure_month - 1]

    # Booking urgency: last-minute premium
    if days_ahead <= 7:
        urgency_mult = 1.5
    elif days_ahead <= 14:
        urgency_mult = 1.3
    elif days_ahead <= 30:
        urgency_mult = 1.1
    else:
        urgency_mult = 1.0

    # Stops discount (more stops = cheaper)
    stops_mult = 1.0 - stops * 0.08

    # Passenger count
    pax = adults + children * 0.75 + infants * 0.1

    # Round-trip factor
    trip_mult = 1.85 if trip_type == "ROUND_TRIP" else 1.0

    # Duration factor (longer = more expensive)
    duration_mult = 1.0 + (flight_duration_minutes / 600) * 0.3

    price = (
        base
        * cabin_mult
        * airline_mult
        * season_mult
        * urgency_mult
        * stops_mult
        * pax
        * trip_mult
        * duration_mult
    )

    # Add Gaussian noise (±8%)
    noise = rng.gauss(1.0, 0.08)
    price *= max(0.5, noise)

    return max(10.0, price)


def save_dataset(df: pd.DataFrame, path: Path = RAW_DATASET_CSV) -> None:
    """Save the dataset to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Dataset saved -> %s (%d rows)", path, len(df))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic flight dataset.")
    parser.add_argument("--rows", type=int, default=SYNTHETIC_DATASET_SIZE)
    parser.add_argument("--output", type=str, default=str(RAW_DATASET_CSV))
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    df = generate_dataset(n_rows=args.rows, seed=args.seed)
    save_dataset(df, Path(args.output))
    print(f"[OK] Dataset saved to {args.output} ({len(df)} rows)")



if __name__ == "__main__":
    main()
