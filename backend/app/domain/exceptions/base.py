"""Base domain exception hierarchy.

Domain exceptions carry an HTTP-status hint and a machine-readable code,
but the classes themselves have zero framework dependency — nothing here
imports FastAPI or Starlette. The presentation-layer exception handlers
(app/presentation/exception_handlers.py) are what translate these into
actual HTTP responses. This keeps the mapping in exactly one place: a
domain rule's "this is a conflict" doesn't need to know what a 409 is.

Concrete, entity-specific exceptions (e.g. a future `DraftAlreadySentError`)
subclass these once the corresponding entities exist — this module only
defines the shared base classes the rest of the domain will build on.
"""


class DomainError(Exception):
    """Base class for every business-rule violation raised by the domain layer.

    Attributes:
        code: A stable, machine-readable identifier (e.g. "NOT_FOUND")
            used as the `error.code` field in the API error envelope.
            Never change an existing code once a client may depend on it.
        message: A human-readable description, safe to return to an
            API consumer (must never contain internal/system detail).
        http_status: The HTTP status code the presentation layer should
            map this exception to.
    """

    code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist or is not visible to the caller."""

    code = "NOT_FOUND"
    http_status = 404


class ConflictError(DomainError):
    """Raised when an action is not valid given the entity's current state.

    Example (once the Draft entity exists): approving a draft that has
    already been sent — the request is well-formed, but the state
    transition it implies is illegal.
    """

    code = "CONFLICT"
    http_status = 409


class BusinessValidationError(DomainError):
    """Raised when input is well-formed but violates a business rule.

    Distinct from FastAPI/Pydantic's request-shape validation (handled
    separately in the presentation layer) — this is for rules that can
    only be evaluated with domain knowledge, e.g. "a draft body cannot
    be empty when approving," not "this field must be a string."
    """

    code = "BUSINESS_VALIDATION_ERROR"
    http_status = 422


class UnauthorizedError(DomainError):
    """Raised when the caller is not authenticated."""

    code = "UNAUTHORIZED"
    http_status = 401


class ForbiddenError(DomainError):
    """Raised when the caller is authenticated but not permitted to act on this entity.

    This is the tenant-isolation guard rail: a user_id mismatch between
    the caller and the resource they're trying to touch raises this,
    never a bare NotFoundError substituted for security-by-obscurity —
    being explicit here matters more than hiding existence, since the
    domain layer is not the place to make that trade-off silently.
    """

    code = "FORBIDDEN"
    http_status = 403
