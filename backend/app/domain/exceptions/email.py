from app.domain.exceptions.base import BusinessValidationError, ConflictError, NotFoundError


class EmailNotFoundError(NotFoundError):
    
    code = "EMAIL_NOT_FOUND"


class EmailAlreadyExistsError(ConflictError):
    

    code = "EMAIL_ALREADY_EXISTS"


class InvalidSearchQueryError(BusinessValidationError):
    

    code = "INVALID_SEARCH_QUERY"