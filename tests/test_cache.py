import asyncio

from app.cache import TTLCache


def test_cache_get_set_and_clear() -> None:
    async def run() -> None:
        cache = TTLCache()
        assert await cache.get("key") is None
        await cache.set("key", {"value": 1}, ttl=10)
        assert await cache.get("key") == {"value": 1}
        await cache.clear()
        assert await cache.get("key") is None

    asyncio.run(run())


def test_cache_expiration() -> None:
    async def run() -> None:
        cache = TTLCache()
        await cache.set("key", "value", ttl=-1)
        assert await cache.get("key") is None

    asyncio.run(run())
