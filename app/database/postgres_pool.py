"""
PostgreSQL connection pooling using SQLAlchemy.
For direct SQL queries not using Supabase client.
"""
import os
from typing import Optional
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

class PostgresPool:
    """
    Singleton connection pool for PostgreSQL using SQLAlchemy.
    """

    _engine: Optional[any] = None
    _session_factory: Optional[sessionmaker] = None
    _initialized: bool = False

    @classmethod
    def get_engine(cls):
        """
        Get the SQLAlchemy engine instance.

        Returns:
            Engine: SQLAlchemy engine
        """
        if cls._engine is None:
            cls._initialize()

        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker:
        """
        Get the session factory for creating database sessions.

        Returns:
            sessionmaker: SQLAlchemy session factory
        """
        if cls._session_factory is None:
            cls._initialize()

        return cls._session_factory

    @classmethod
    def _initialize(cls) -> None:
        """
        Initialize the connection pool.

        Raises:
            ValueError: If DATABASE_URL is not set
        """
        if cls._initialized:
            return

        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError("DATABASE_URL must be set in environment variables")

        # Create engine with connection pooling
        cls._engine = create_engine(
            database_url,
            # QueuePool settings
            poolclass=pool.QueuePool,
            pool_size=10,  # Maintain 10 connections
            max_overflow=5,  # Allow 5 extra connections
            pool_timeout=30,  # Wait 30s for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before using

            # Performance settings
            echo=False,  # Don't log SQL (use for debugging)
            echo_pool=False,  # Don't log pool events

            # Connection settings
            connect_args={
                "connect_timeout": 10,  # 10 second connection timeout
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }
        )

        # Create session factory
        cls._session_factory = sessionmaker(
            bind=cls._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        cls._initialized = True
        logger.info("PostgreSQL connection pool initialized", extra={
            "pool_size": 10,
            "max_overflow": 5
        })

    @classmethod
    def close(cls) -> None:
        """
        Close all connections in the pool.
        Should be called on application shutdown.
        """
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            cls._initialized = False
            logger.info("PostgreSQL connection pool closed")

    @classmethod
    def reset(cls) -> None:
        """
        Reset the connection pool (for testing purposes).
        """
        cls.close()

    @classmethod
    @contextmanager
    def get_session(cls):
        """
        Context manager for database sessions.
        Automatically commits on success or rolls back on error.

        Usage:
            with PostgresPool.get_session() as session:
                result = session.execute("SELECT * FROM users")

        Yields:
            Session: SQLAlchemy session
        """
        session_factory = cls.get_session_factory()
        session: Session = session_factory()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Convenience function
def get_db_session():
    """
    Get a database session context manager.

    Returns:
        Context manager for database session
    """
    return PostgresPool.get_session()
