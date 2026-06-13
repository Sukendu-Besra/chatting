"""
app/middleware/logging_middleware.py
--------------------------------------
Request/response logging middleware.

Logs every incoming HTTP request with:
  - Method and path
  - Response status code
  - Processing duration in milliseconds
  - Client IP address

This gives you an access log without relying on Nginx/proxy logs.
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that wraps every request with structured logging.

    Exclude health check and docs endpoints to avoid log noise.
    """

    EXCLUDE_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noisy paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()

        # Log the incoming request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        # Process the request
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Log the response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
