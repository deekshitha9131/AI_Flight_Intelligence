from app.domain.exceptions.base import BusinessValidationError, DomainError, UnauthorizedError


class OAuthNotConfiguredError(DomainError):

    code = "OAUTH_NOT_CONFIGURED"
    http_status = 503


class InvalidOAuthStateError(BusinessValidationError):

    code = "INVALID_OAUTH_STATE"

    http_status = 400


class OAuthExchangeError(DomainError):

    code = "OAUTH_EXCHANGE_FAILED"
    http_status = 502


class SessionNotFoundError(UnauthorizedError):

    code = "SESSION_NOT_FOUND"
