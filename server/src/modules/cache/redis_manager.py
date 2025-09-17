import aioredis
import json
import hashlib
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        self.redis = None

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis = aioredis.from_url(
                "redis://localhost:6379",
                encoding="utf8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None
        try:
            cached = await self.redis.get(key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 600):
        """Set value in cache with TTL"""
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

    def hash_key(self, *args) -> str:
        """Create a hash key from arguments"""
        key_string = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()

# Global Redis instance
redis_manager = RedisManager()
