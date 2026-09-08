import contextvars
import uuid

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def generate_request_id() -> str:

    return str(uuid.uuid4())


def set_request_id(request_id: str) -> None:

    _request_id_var.set(request_id)


def get_request_id() -> str:

    return _request_id_var.get() or generate_request_id()
