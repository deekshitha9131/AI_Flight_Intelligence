from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.chat import ChatConversation, ChatMessage
from app.models.favorite_flight import FavoriteFlight
from app.models.flight_search import FlightSearch
from app.models.prediction_history import PredictionHistory
from app.models.recommendation_log import RecommendationLog
from app.models.refresh_token import RefreshToken

# Import all models so Alembic can discover them
from app.models.user import User
from app.models.user_preference import UserPreferenceProfile
