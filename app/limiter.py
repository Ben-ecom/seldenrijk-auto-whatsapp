"""
Rate limiter instance shared across the application.
Separated into its own module to avoid circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize slowapi rate limiter
# This can be imported by both app.main and app.api.webhooks without circular dependency
limiter = Limiter(key_func=get_remote_address)
