import asyncio

from app.rate_limit import SlidingWindowRateLimiter


def test_rate_limiter_blocks_after_limit() -> None:
    async def run() -> None:
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
        assert await limiter.allow("client")
        assert await limiter.allow("client")
        assert not await limiter.allow("client")

    asyncio.run(run())
