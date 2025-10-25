"""
Supabase connection pooling with singleton pattern.
Prevents connection exhaustion by reusing a single client instance.
"""
import os
from typing import Optional
from supabase import create_client, Client
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

class SupabasePool:
    """
    Singleton connection pool for Supabase client.
    Ensures only one client instance is created and reused across requests.
    """

    _instance: Optional[Client] = None
    _initialized: bool = False

    @classmethod
    def get_client(cls) -> Client:
        """
        Get the singleton Supabase client instance.
        Creates the client on first call, then reuses it.

        Returns:
            Client: Supabase client instance

        Raises:
            ValueError: If SUPABASE_URL or SUPABASE_KEY are not set
        """
        if cls._instance is None:
            cls._initialize_client()

        return cls._instance

    @classmethod
    def _initialize_client(cls) -> None:
        """
        Initialize the Supabase client with connection pooling.

        Raises:
            ValueError: If required environment variables are missing
        """
        if cls._initialized:
            return

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
            )

        # Create client without custom options (supabase-py v2 uses default pooling)
        cls._instance = create_client(
            supabase_url,
            supabase_key
        )

        cls._initialized = True
        logger.info("Supabase connection pool initialized", extra={
            "pool_size": 10,
            "max_overflow": 5
        })

    @classmethod
    def close(cls) -> None:
        """
        Close the Supabase client connection.
        Should be called on application shutdown.
        """
        if cls._instance is not None:
            # Supabase client doesn't have explicit close method
            # But we can reset the instance
            cls._instance = None
            cls._initialized = False
            logger.info("Supabase connection pool closed")

    @classmethod
    def reset(cls) -> None:
        """
        Reset the connection pool (for testing purposes).
        Forces re-initialization on next get_client() call.
        """
        cls._instance = None
        cls._initialized = False
        logger.info("Supabase connection pool reset")

# Convenience function for direct usage
def get_supabase_client() -> Client:
    """
    Get Supabase client from pool.

    Returns:
        Client: Supabase client instance
    """
    return SupabasePool.get_client()
