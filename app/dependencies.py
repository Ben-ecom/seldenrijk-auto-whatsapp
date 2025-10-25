"""
FastAPI Dependencies for Dependency Injection.
Provides access to app-level resources without circular imports.
"""
from fastapi import Request
from slowapi import Limiter


def get_limiter(request: Request) -> Limiter:
    """
    Get the rate limiter instance from app state.

    This allows endpoints to access the limiter without importing from main.py,
    avoiding circular import issues.

    Args:
        request: FastAPI request object with app state

    Returns:
        Limiter: The slowapi limiter instance

    Example:
        @router.post("/endpoint")
        async def endpoint(limiter: Limiter = Depends(get_limiter)):
            # Limiter is now available
    """
    return request.app.state.limiter
