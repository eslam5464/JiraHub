import json

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import get_settings


class CacheService:
    """Redis cache layer for Jira data. Manual refresh only (no TTL)."""

    def __init__(self):
        settings = get_settings()
        self._redis_url = settings.redis_url

    def _get_client(self) -> aioredis.Redis:
        """Create a fresh Redis client each time to avoid event loop issues."""
        return aioredis.from_url(
            self._redis_url,
            decode_responses=True,
        )

    def _key(self, user_email: str, namespace: str, project_key: str | None = None) -> str:
        """Build a namespaced cache key, optionally scoped to a project."""
        if project_key:
            return f"jira:{user_email}:{project_key}:{namespace}"
        return f"jira:{user_email}:{namespace}"

    async def get_cached(
        self, user_email: str, namespace: str, project_key: str | None = None
    ) -> dict | list | None:
        """Get cached data. Returns None if not cached."""
        try:
            client = self._get_client()
            try:
                data = await client.get(self._key(user_email, namespace, project_key))
                if data:
                    return json.loads(data)
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Redis get failed (key={namespace}): {e}")
        return None

    async def set_cached(
        self,
        user_email: str,
        namespace: str,
        data: dict | list,
        *,
        project_key: str | None = None,
        ttl: int | None = None,
    ) -> None:
        """Cache data. No TTL by default (manual refresh)."""
        try:
            client = self._get_client()
            try:
                key = self._key(user_email, namespace, project_key)
                serialized = json.dumps(data, default=str)
                if ttl:
                    await client.setex(key, ttl, serialized)
                else:
                    await client.set(key, serialized)
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Redis set failed (key={namespace}): {e}")

    async def invalidate(
        self, user_email: str, namespace: str, project_key: str | None = None
    ) -> None:
        """Invalidate a specific cache key."""
        try:
            client = self._get_client()
            try:
                await client.delete(self._key(user_email, namespace, project_key))
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Redis delete failed (key={namespace}): {e}")

    async def invalidate_all(self, user_email: str) -> None:
        """Invalidate all cached data for a user."""
        try:
            client = self._get_client()
            try:
                pattern = f"jira:{user_email}:*"
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache keys for {user_email}")
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Redis invalidate_all failed: {e}")

    async def get_last_refresh(self, user_email: str, project_key: str | None = None) -> str | None:
        """Get the timestamp of the last data refresh."""
        try:
            client = self._get_client()
            try:
                return await client.get(self._key(user_email, "last_refresh", project_key))
            finally:
                await client.aclose()
        except Exception:
            return None

    async def set_last_refresh(
        self, user_email: str, timestamp: str, project_key: str | None = None
    ) -> None:
        """Store the timestamp of the last data refresh."""
        try:
            client = self._get_client()
            try:
                await client.set(self._key(user_email, "last_refresh", project_key), timestamp)
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Redis set last_refresh failed: {e}")


# Singleton
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
