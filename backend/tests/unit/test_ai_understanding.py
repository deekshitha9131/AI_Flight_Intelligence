import pytest
from pydantic import ValidationError

from app.ai.schemas.ai_understanding import (
    AIUnderstandingResult,
    EmailCategory,
    EmailIntent,
    EmailSentiment,
    EmailUrgency,
    Entity,
)


def _valid_kwargs(**overrides) -> dict:
    defaults = dict(
        category=EmailCategory.TRAVEL,
        intent=EmailIntent.CANCELLATION,
        urgency=EmailUrgency.HIGH,
        sentiment=EmailSentiment.NEGATIVE,
        entities=[
            {"type": "organization", "value": "Delta Airlines"},
            {"type": "date", "value": "August 15"},
        ],
        summary="Flight booking was cancelled.",
        confidence=0.94,
    )
    defaults.update(overrides)
    return defaults


def test_valid_complete_result_constructs_successfully() -> None:
    result = AIUnderstandingResult(**_valid_kwargs())

    assert result.category == EmailCategory.TRAVEL
    assert result.intent == EmailIntent.CANCELLATION
    assert result.urgency == EmailUrgency.HIGH
    assert result.sentiment == EmailSentiment.NEGATIVE
    assert len(result.entities) == 2
    assert result.summary == "Flight booking was cancelled."
    assert result.confidence == 0.94


def test_result_accepts_every_declared_category() -> None:
    for category in EmailCategory:
        result = AIUnderstandingResult(**_valid_kwargs(category=category))
        assert result.category == category


def test_result_accepts_every_declared_intent() -> None:
    for intent in EmailIntent:
        result = AIUnderstandingResult(**_valid_kwargs(intent=intent))
        assert result.intent == intent


def test_result_accepts_every_declared_urgency() -> None:
    for urgency in EmailUrgency:
        result = AIUnderstandingResult(**_valid_kwargs(urgency=urgency))
        assert result.urgency == urgency


def test_result_accepts_every_declared_sentiment() -> None:
    for sentiment in EmailSentiment:
        result = AIUnderstandingResult(**_valid_kwargs(sentiment=sentiment))
        assert result.sentiment == sentiment


def test_result_accepts_empty_entities_list() -> None:
    result = AIUnderstandingResult(**_valid_kwargs(entities=[]))
    assert result.entities == []


def test_result_defaults_entities_to_empty_list_when_omitted() -> None:
    kwargs = _valid_kwargs()
    del kwargs["entities"]
    result = AIUnderstandingResult(**kwargs)
    assert result.entities == []


def test_confidence_boundary_values_are_accepted() -> None:
    assert AIUnderstandingResult(**_valid_kwargs(confidence=0.0)).confidence == 0.0
    assert AIUnderstandingResult(**_valid_kwargs(confidence=1.0)).confidence == 1.0


def test_entity_valid_construction() -> None:
    entity = Entity(type="person", value="John")
    assert entity.type == "person"
    assert entity.value == "John"


def test_entity_rejects_empty_type() -> None:
    with pytest.raises(ValidationError):
        Entity(type="", value="John")


def test_entity_rejects_empty_value() -> None:
    with pytest.raises(ValidationError):
        Entity(type="person", value="")


def test_entity_rejects_missing_type() -> None:
    with pytest.raises(ValidationError):
        Entity(value="John")  # type: ignore[call-arg]


def test_entity_rejects_missing_value() -> None:
    with pytest.raises(ValidationError):
        Entity(type="person")  # type: ignore[call-arg]


def test_result_rejects_malformed_entity_missing_value_key() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(entities=[{"type": "person"}]))


def test_result_rejects_entity_with_wrong_field_names() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(
            **_valid_kwargs(entities=[{"entity_type": "person", "entity_value": "John"}])
        )


def test_invalid_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(category="not-a-real-category"))


def test_invalid_intent_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(intent="not-a-real-intent"))


def test_invalid_urgency_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(urgency="not-a-real-urgency"))


def test_invalid_sentiment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(sentiment="not-a-real-sentiment"))


def test_confidence_below_zero_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(confidence=-0.01))


def test_confidence_above_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(confidence=1.01))


def test_confidence_far_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(confidence=50.0))


@pytest.mark.parametrize(
    "missing_field", ["category", "intent", "urgency", "sentiment", "summary", "confidence"]
)
def test_missing_required_field_is_rejected(missing_field: str) -> None:
    kwargs = _valid_kwargs()
    del kwargs[missing_field]

    with pytest.raises(ValidationError):
        AIUnderstandingResult(**kwargs)


def test_empty_summary_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(summary=""))


def test_summary_over_max_length_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(summary="x" * 1001))


def test_whitespace_only_summary_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(summary="   "))


def test_summary_of_only_tabs_and_newlines_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(summary="\t\n  \n\t"))


def test_confidence_of_1_point_5_is_rejected_not_clamped() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(confidence=1.5))


def test_confidence_of_negative_0_point_5_is_rejected_not_clamped() -> None:
    with pytest.raises(ValidationError):
        AIUnderstandingResult(**_valid_kwargs(confidence=-0.5))
