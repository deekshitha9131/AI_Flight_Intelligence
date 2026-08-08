from app.domain.exceptions.base import NotFoundError


class ThreadNotFoundError(NotFoundError):
    

    code = "THREAD_NOT_FOUND"