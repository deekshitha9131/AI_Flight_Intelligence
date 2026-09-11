import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.database.session import Base
from app.models import user, conversation, message, flight_search, prediction, preference

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)

def test_tables_exist(db):
    """Test that all expected tables are created."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected_tables = {
        "users",
        "conversations",
        "messages",
        "flight_searches",
        "predictions",
        "preferences",
    }
    assert expected_tables.issubset(set(tables))

def test_user_model(db):
    """Test the User model."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("users")}
    assert "id" in columns
    assert "email" in columns
    assert columns["email"]["nullable"] is False
    assert "password_hash" in columns
    assert "first_name" in columns
    assert "last_name" in columns
    assert "is_active" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

def test_conversation_model(db):
    """Test the Conversation model."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("conversations")}
    assert "id" in columns
    assert "user_id" in columns
    assert columns["user_id"]["nullable"] is False
    assert "title" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

    foreign_keys = inspector.get_foreign_keys("conversations")
    assert len(foreign_keys) == 1
    fk = foreign_keys[0]
    assert fk["constrained_columns"] == ["user_id"]
    assert fk["referred_table"] == "users"
    assert fk["referred_columns"] == ["id"]

def test_message_model(db):
    """Test the Message model."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("messages")}
    assert "id" in columns
    assert "conversation_id" in columns
    assert columns["conversation_id"]["nullable"] is False
    assert "role" in columns
    assert columns["role"]["nullable"] is False
    assert "content" in columns
    assert columns["content"]["nullable"] is False
    assert "created_at" in columns

    foreign_keys = inspector.get_foreign_keys("messages")
    assert len(foreign_keys) == 1
    fk = foreign_keys[0]
    assert fk["constrained_columns"] == ["conversation_id"]
    assert fk["referred_table"] == "conversations"
    assert fk["referred_columns"] == ["id"]

def test_flight_search_model(db):
    """Test the FlightSearch model."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("flight_searches")}
    assert "id" in columns
    assert "user_id" in columns
    assert columns["user_id"]["nullable"] is False
    assert "origin" in columns
    assert columns["origin"]["nullable"] is False
    assert "destination" in columns
    assert columns["destination"]["nullable"] is False
    assert "departure_date" in columns
    assert columns["departure_date"]["nullable"] is False
    assert "return_date" in columns
    assert "passengers" in columns
    assert columns["passengers"]["nullable"] is False
    assert "cabin_class" in columns
    assert columns["cabin_class"]["nullable"] is False
    assert "created_at" in columns

    foreign_keys = inspector.get_foreign_keys("flight_searches")
    assert len(foreign_keys) == 1
    fk = foreign_keys[0]
    assert fk["constrained_columns"] == ["user_id"]
    assert fk["referred_table"] == "users"
    assert fk["referred_columns"] == ["id"]

def test_prediction_model(db):
    """Test the Prediction model."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("predictions")}
    assert "id" in columns
    assert "user_id" in columns
    assert columns["user_id"]["nullable"] is False
    assert "flight_search_id" in columns
    assert columns["flight_search_id"]["nullable"] is False
    assert "predicted_price" in columns
    assert columns["predicted_price"]["nullable"] is False
    assert "currency" in columns
    assert columns["currency"]["nullable"] is False
    assert "created_at" in columns

    foreign_keys = inspector.get_foreign_keys("predictions")
    assert len(foreign_keys) == 2
    fk_user = next(fk for fk in foreign_keys if fk["constrained_columns"] == ["user_id"])
    assert fk_user["referred_table"] == "users"
    assert fk_user["referred_columns"] == ["id"]
    fk_flight_search = next(fk for fk in foreign_keys if fk["constrained_columns"] == ["flight_search_id"])
    assert fk_flight_search["referred_table"] == "flight_searches"
    assert fk_flight_search["referred_columns"] == ["id"]

def test_preference_model(db):
    """Test the Preference model."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("preferences")}
    assert "id" in columns
    assert "user_id" in columns
    assert columns["user_id"]["nullable"] is False
    # Check for unique constraint on user_id
    unique_constraints = inspector.get_unique_constraints("preferences")
    # We expect at least one unique constraint that includes the user_id column
    assert any(
        "user_id" in uc["column_names"]
        for uc in unique_constraints
    )
    assert "preferred_cabin" in columns
    assert "preferred_currency" in columns
    assert "preferred_airport" in columns
    assert "preferred_time" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

    foreign_keys = inspector.get_foreign_keys("preferences")
    assert len(foreign_keys) == 1
    fk = foreign_keys[0]
    assert fk["constrained_columns"] == ["user_id"]
    assert fk["referred_table"] == "users"
    assert fk["referred_columns"] == ["id"]