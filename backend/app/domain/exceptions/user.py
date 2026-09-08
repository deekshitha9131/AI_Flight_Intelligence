from app.domain.exceptions.base import ConflictError, NotFoundError


class UserNotFoundError(NotFoundError):

    code = "USER_NOT_FOUND"


class UserAlreadyExistsError(ConflictError):

    code = "USER_ALREADY_EXISTS"
