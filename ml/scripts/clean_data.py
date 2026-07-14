"""Clean the configured raw dataset."""

import pandas as pd

from ml.config.settings import RAW_DATASET_CSV
from ml.data.cleaner import DataCleaner, save_cleaned

if __name__ == "__main__":
    save_cleaned(DataCleaner().clean(pd.read_csv(RAW_DATASET_CSV)))
