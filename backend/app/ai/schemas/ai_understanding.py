from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EmailCategory(StrEnum):

    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    SOCIAL = "social"
    NOTIFICATION = "notification"
    OTHER = "other"


class EmailIntent(StrEnum):
    REQUEST = "request"
    QUESTION = "question"
    INFORMATION = "information"
    COMPLAINT = "complaint"
    CONFIRMATION = "confirmation"
    CANCELLATION = "cancellation"
    NOTIFICATION = "notification"
    OTHER = "other"


class EmailUrgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailSentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Entity(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=500)


class AIUnderstandingResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: EmailCategory
    intent: EmailIntent
    urgency: EmailUrgency
    sentiment: EmailSentiment
    entities: list[Entity] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0.0, le=1.0)
