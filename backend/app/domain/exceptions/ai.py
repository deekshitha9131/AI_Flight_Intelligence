from app.domain.exceptions.base import BusinessValidationError, DomainError


class AIConfigurationError(DomainError):

    code = "AI_CONFIGURATION_ERROR"
    http_status = 500


class AIProviderError(DomainError):
    code = "AI_PROVIDER_ERROR"
    http_status = 502


class InvalidAIResponseError(BusinessValidationError):
    code = "AI_INVALID_RESPONSE"


class EmbeddingProviderError(DomainError):
    code = "EMBEDDING_PROVIDER_ERROR"
    http_status = 502
