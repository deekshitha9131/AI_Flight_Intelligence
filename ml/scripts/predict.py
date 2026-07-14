"""Run a single prediction from a JSON feature object."""

import argparse
import json

from ml.inference.predictor import FlightPricePredictor

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("features", help="JSON object with raw flight features")
    args = parser.parse_args()
    print(
        json.dumps(FlightPricePredictor().predict(json.loads(args.features)).__dict__)
    )
