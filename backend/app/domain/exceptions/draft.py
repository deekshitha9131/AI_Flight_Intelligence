from app.domain.exceptions.base import BusinessValidationError, ConflictError, NotFoundError

class DraftNotFoundError(NotFoundError):
    code = "DRAFT_NOT_FOUND"

class DraftUnderstandingMissingError(ConflictError):
    code = "DRAFT_UNDERSTANDING_MISSING"

class DraftStatusError(BusinessValidationError):
    code = "DRAFT_STATUS_ERROR"