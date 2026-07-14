"""Compatibility entry point for model training."""

from ml.scripts.run_pipeline import run

if __name__ == "__main__":
    from ml.config.settings import RAW_DATASET_CSV

    run(str(RAW_DATASET_CSV), "1.0.0")
