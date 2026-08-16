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
    """Return ModelLoader from app.state, initializing a singleton if uninitialized."""
    loader = getattr(request.app.state, "model_loader", None)
    if loader is None:
        from app.ai.model_loader import get_model_loader as _get_singleton
        loader = _get_singleton()
        request.app.state.model_loader = loader
    return loader


def get_llm_provider(request: Request) -> LLMProvider:
    """Return LLMProvider from app.state, falling back to build_llm_provider."""
    provider = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        from app.ai.llm_provider import build_llm_provider
        provider = build_llm_provider()
        request.app.state.llm_provider = provider
    return provider


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
    request: Request,
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> AssistantService:
    from app.dependencies.amadeus import get_flight_provider
    from app.repositories.search_repository import SearchRepository
    from app.services.flight_service import FlightService

    provider = get_flight_provider(request)
    search_repo = SearchRepository(provider=provider, db=db)
    flight_service = FlightService(repository=search_repo)

    return AssistantService(
        chat_repo=ChatRepository(db=db),
        llm_provider=llm_provider,
        flight_service=flight_service,
    )


def get_insight_service(
    db: Session = Depends(get_db),
) -> InsightService:
    return InsightService(
        prediction_repo=PredictionRepository(db=db),
        preference_repo=PreferenceRepository(db=db),
    )
