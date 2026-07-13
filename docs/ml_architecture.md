# ML and AI architecture

Historical CSV, JSON, and API records enter `ml.data.importer.DatasetImporter`.
They are validated, cleaned, feature engineered, and passed into a selected
scikit-learn regression pipeline. A versioned joblib bundle contains the model,
the fitted feature engineer, and its ordered feature list. FastAPI loads the
latest bundle at startup; it safely uses a deterministic fallback until an
artifact is deployed.

Run `python -m ml.scripts.run_pipeline --input ml/data/raw/flights_raw.csv`
to create an artifact. The API exposes prediction, trend, insights,
recommendations, and a provider-abstracted travel assistant under `/api/v1`.
Prediction inputs and model version are persisted for audit and trend analysis.
