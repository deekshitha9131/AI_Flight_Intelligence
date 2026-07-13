"""Print persisted model metadata and metrics."""
import json
from ml.utils.serialisation import load_metadata

if __name__ == "__main__":
    print(json.dumps(load_metadata(), indent=2))
