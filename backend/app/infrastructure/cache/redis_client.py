import redis.asyncio as redis

from app.core.config import Settings


def create_redis_client(settings: Settings) -> redis.Redis:
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
    )


async def close_redis_client(client: redis.Redis) -> None:
    await client.aclose()


async def ping_redis(client: redis.Redis) -> bool:
    try:
        return bool(await client.ping())
    except Exception:  # noqa: BLE001 — see docstring: broad by design
        return False
