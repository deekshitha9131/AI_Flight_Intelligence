"""Redis client factory.

Redis serves three distinct roles in this system (cache, Celery
broker/result-backend, pub/sub for websocket fan-out — per the frozen
architecture) but the API process only ever needs a client for the
cache/pub-sub roles; Celery manages its own broker connection
separately via its app configuration (later phase). This module builds
that single client.

A note on the `# type: ignore[type-arg]` comments below: redis-py's
type stubs declare `Redis` as generic (`Redis[str]` vs `Redis[bytes]`,
depending on `decode_responses`), so mypy wants every usage
parameterized. The installed redis-py version (5.3.1) does not actually
implement `Redis` as a runtime-generic class, though — subscripting it
(`redis.Redis[str]`) raises `TypeError: <class '...Redis'> is not a
generic class` the moment Python evaluates that expression. This
matters specifically because FastAPI's dependency resolution calls
`inspect.signature(fn, eval_str=True)` on every `Depends()` target,
which forces even *string-quoted* annotations to be evaluated — so
quoting the annotation instead of parameterizing it does not avoid the
crash for any function used as a FastAPI dependency (directly or
transitively, e.g. via app/core/di_container.py). The only fix that is
correct both statically and at runtime is: leave the annotation bare
(`redis.Redis`, no subscript) and suppress mypy's resulting
`[type-arg]` complaint explicitly, here and everywhere else in the
codebase using a `redis.Redis` type annotation.
"""

import redis.asyncio as redis

from app.core.config import Settings


def create_redis_client(settings: Settings) -> redis.Redis:  # type: ignore[type-arg]
    """Build the async Redis client from settings.

    `decode_responses=True` so callers get `str` back instead of `bytes`
    — nearly everything cached here (session data, notification
    payloads) is JSON text, and decoding it at every call site would be
    needless repetition.
    """
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
    )


async def close_redis_client(client: redis.Redis) -> None:  # type: ignore[type-arg]
    """Cleanly close the Redis connection pool on application shutdown.

    `aclose` exists at runtime on redis-py 5.x (confirmed directly —
    `hasattr(Redis, 'aclose')` is True) but is missing from the
    installed type stub, hence the ignore below.
    """
    await client.aclose()  # type: ignore[attr-defined]


async def ping_redis(client: redis.Redis) -> bool:  # type: ignore[type-arg]
    """Check Redis connectivity — used by the readiness health check.

    Deliberately catches `Exception` broadly, not just `redis.RedisError`.
    A connection-level failure (DNS resolution, a socket timeout before
    the Redis protocol is even reached) can surface as a plain
    `ConnectionError`, `TimeoutError`, or `OSError` rather than a
    redis-specific exception type — and a readiness check that can
    itself crash on an unexpected exception type defeats the entire
    point of a readiness check. This mirrors the same broad-catch
    pattern the database check uses in
    app/presentation/api/v1/routers/health.py.
    """
    try:
        return await client.ping()
    except Exception:  # noqa: BLE001 — see docstring: broad by design
        return False
