from __future__ import annotations

from app.ai.llm_provider import LLMProvider
from app.ai.model_loader import ModelLoader
from app.database.session import get_db
from app.repositories.chat_repository import ChatRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.search_history_repository import SearchHistoryRepository
from app.services.assistant_service import AssistantService
from app.services.insight_service import InsightService
from app.services.prediction_service import PredictionService
from app.services.preference_service import PreferenceService
from app.services.price_trend_service import PriceTrendService
from app.services.recommendation_service import RecommendationService
from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_model_loader(request: Request) -> ModelLoader:
    """Return the ModelLoader stored on app.state at startup."""
    return getattr(request.app.state, "model_loader", None)


def get_llm_provider(request: Request) -> LLMProvider:
    """Return the LLMProvider stored on app.state at startup."""
    return getattr(request.app.state, "llm_provider", None)


def get_prediction_service(
    db: Session = Depends(get_db),
    model_loader: ModelLoader = Depends(get_model_loader),
) -> PredictionService:
    return PredictionService(
        repository=PredictionRepository(db=db),
        model_loader=model_loader,
    )


def get_price_trend_service(
    db: Session = Depends(get_db),
) -> PriceTrendService:
    return PriceTrendService(repository=PredictionRepository(db=db))


def get_preference_service(
    db: Session = Depends(get_db),
) -> PreferenceService:
    return PreferenceService(
        preference_repo=PreferenceRepository(db=db),
        search_history_repo=SearchHistoryRepository(db=db),
    )


def get_recommendation_service(
    db: Session = Depends(get_db),
    model_loader: ModelLoader = Depends(get_model_loader),
) -> RecommendationService:
    return RecommendationService(
        preference_repo=PreferenceRepository(db=db),
        recommendation_repo=RecommendationRepository(db=db),
        model_loader=model_loader,
    )


def get_assistant_service(
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> AssistantService:
    return AssistantService(
        chat_repo=ChatRepository(db=db),
        llm_provider=llm_provider,
    )


def get_insight_service(
    db: Session = Depends(get_db),
) -> InsightService:
    return InsightService(
        prediction_repo=PredictionRepository(db=db),
        preference_repo=PreferenceRepository(db=db),
    )
