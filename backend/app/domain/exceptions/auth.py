"""Auth-specific domain exceptions.

Subclasses of the base hierarchy in app/domain/exceptions/base.py, same
pattern as app/domain/exceptions/user.py.
"""

from app.domain.exceptions.base import BusinessValidationError, DomainError, UnauthorizedError


class InvalidOAuthStateError(BusinessValidationError):
    """Raised when the `state` query parameter on the OAuth callback doesn't
    match the value set on the login redirect — the standard CSRF guard
    for the authorization code flow. A mismatch means either the request
    didn't originate from our own /login redirect, or the state cookie
    expired (see OAUTH_STATE_COOKIE_MAX_AGE_SECONDS) before the user
    completed the consent screen."""

    code = "INVALID_OAUTH_STATE"
    # Explicit 400, not the inherited 422: this isn't a business-rule
    # validation failure on otherwise well-formed data (422's actual
    # meaning) — it's a request whose authenticity can't be trusted,
    # which is what 400 Bad Request is for.
    http_status = 400


class OAuthExchangeError(DomainError):
    """Raised when a call to Google's token or userinfo endpoint fails —
    an expired/reused code, a revoked client secret, or Google being
    unreachable. Mapped to 502 (not 500): the failure is in an upstream
    dependency, not this service's own logic."""

    code = "OAUTH_EXCHANGE_FAILED"
    http_status = 502


class SessionNotFoundError(UnauthorizedError):
    """Raised when the session cookie is missing, or points at a session
    that has expired or was never valid."""

    code = "SESSION_NOT_FOUND"
