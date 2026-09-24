"""Development-mode auth shim for LISA.

Local usage does not require API keys or approval gates.
"""

from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """No-op middleware: all local requests are allowed without an API key."""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)


def require_api_key(request: Request) -> Optional[str]:
    """Development helper that always allows requests without auth."""
    return None