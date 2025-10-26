"""
Redis client for caching and deduplication.
"""
import os
import redis
from typing import Optional

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create global Redis client instance.

    Returns:
        Redis client for caching and deduplication
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )

    return _redis_client
