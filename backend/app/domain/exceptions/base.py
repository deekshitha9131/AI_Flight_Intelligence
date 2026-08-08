class DomainError(Exception):
   

    code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
   
    code = "NOT_FOUND"
    http_status = 404


class ConflictError(DomainError):
    

    code = "CONFLICT"
    http_status = 409


class BusinessValidationError(DomainError):
   

    code = "BUSINESS_VALIDATION_ERROR"
    http_status = 422


class UnauthorizedError(DomainError):
   
    code = "UNAUTHORIZED"
    http_status = 401


class ForbiddenError(DomainError):
    

    code = "FORBIDDEN"
    http_status = 403
