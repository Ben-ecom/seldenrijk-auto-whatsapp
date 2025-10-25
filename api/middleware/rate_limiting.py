"""
Rate Limiting Middleware

Simple in-memory rate limiting to prevent abuse.
For production, use Redis-backed rate limiting (e.g., slowapi).
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.

    Limits:
    - 100 requests per minute per IP
    - 1000 requests per hour per IP
    """

    def __init__(self, app, requests_per_minute: int = 100, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests = defaultdict(list)  # {ip: [timestamp, ...]}
        self.hour_requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """
        Check rate limits before processing request.
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host

        # Current timestamp
        now = time.time()

        # Clean old entries (older than 1 hour)
        self._clean_old_entries(client_ip, now)

        # Check minute limit
        minute_count = len([t for t in self.minute_requests[client_ip] if now - t < 60])
        if minute_count >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
            )

        # Check hour limit
        hour_count = len([t for t in self.hour_requests[client_ip] if now - t < 3600])
        if hour_count >= self.requests_per_hour:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
            )

        # Add current request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(self.requests_per_minute - minute_count - 1)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(self.requests_per_hour - hour_count - 1)

        return response

    def _clean_old_entries(self, client_ip: str, now: float):
        """Remove entries older than 1 hour."""
        self.minute_requests[client_ip] = [
            t for t in self.minute_requests[client_ip]
            if now - t < 60
        ]
        self.hour_requests[client_ip] = [
            t for t in self.hour_requests[client_ip]
            if now - t < 3600
        ]
