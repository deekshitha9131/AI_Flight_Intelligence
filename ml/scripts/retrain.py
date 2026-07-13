"""Alias for the training pipeline, suitable for scheduled jobs."""
from datetime import datetime, timezone

from ml.config.settings import RAW_DATASET_CSV
from ml.scripts.run_pipeline import run

if __name__ == "__main__":
    run(str(RAW_DATASET_CSV), datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
