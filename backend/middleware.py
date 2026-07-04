"""
backend/middleware.py — FastAPI middlewares for auth, rate limiting, and logging.

Updated for Google ADK conversion:
- Removed bcrypt/JWT dependencies (replaced by Firebase Auth or demo mode)
- Added structured Cloud Logging integration
- Simplified RBAC for demo mode
"""

import time
import logging
from typing import Callable, Dict, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sampark.gateway")

from backend.config import settings

# In-memory rate limiter
_rate_limit_cache: Dict[str, List[float]] = {}
RATE_LIMIT_MAX_REQ = 60
RATE_LIMIT_WINDOW = 60.0


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware with structured log format."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            latency_ms = (time.time() - start_time) * 1000
            user_id = getattr(request.state, "user_id", "anonymous")
            logger.info(
                "Request: method=%s path=%s user_id=%s status=%s latency_ms=%.2f",
                request.method, request.url.path, user_id, status_code, latency_ms
            )
        return response


class AuthAndRateLimitMiddleware(BaseHTTPMiddleware):
    """Authentication and rate limiting middleware.

    In production mode, validates Firebase ID tokens.
    In demo mode, accepts demo tokens (admin/leader_w1).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for public endpoints
        public_paths = {
            "/health", "/auth/login", "/docs", "/openapi.json",
            "/chat/stream", "/analytics/dashboard/stream",
        }
        if request.url.path in public_paths or request.url.path.startswith("/chat/stream/") or request.url.path.startswith("/analytics/dashboard/stream"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Missing or invalid Authorization header"}, status_code=401)

        token = auth_header.split(" ")[1]

        if settings.APP_MODE == "production":
            # Firebase Auth validation (production)
            try:
                import firebase_admin
                from firebase_admin import auth
                decoded = auth.verify_id_token(token)
                request.state.user_id = decoded["uid"]
                request.state.role = decoded.get("role", "citizen")
                request.state.ward_ids = decoded.get("ward_ids", [])
            except Exception:
                return JSONResponse({"detail": "Invalid Firebase token"}, status_code=401)
        else:
            # Demo mode: simple token validation
            demo_tokens = {
                "demo_admin_token": {"user_id": "admin_1", "role": "government_officer", "ward_ids": ["*"]},
                "demo_leader_token": {"user_id": "leader_1", "role": "community_leader", "ward_ids": ["w1"]},
            }
            user_info = demo_tokens.get(token)
            if not user_info:
                return JSONResponse({"detail": "Invalid demo token"}, status_code=401)
            request.state.user_id = user_info["user_id"]
            request.state.role = user_info["role"]
            request.state.ward_ids = user_info["ward_ids"]

        # Rate limiting (sliding window)
        now = time.time()
        user_timestamps = _rate_limit_cache.get(request.state.user_id, [])
        user_timestamps = [ts for ts in user_timestamps if now - ts < RATE_LIMIT_WINDOW]
        if len(user_timestamps) >= RATE_LIMIT_MAX_REQ:
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(int(RATE_LIMIT_WINDOW))}
            )
        user_timestamps.append(now)
        _rate_limit_cache[request.state.user_id] = user_timestamps

        # RBAC check
        path_parts = request.url.path.split("/")
        if "ward" in path_parts:
            ward_idx = path_parts.index("ward")
            if len(path_parts) > ward_idx + 1:
                target_ward = path_parts[ward_idx + 1]
                if "*" not in request.state.ward_ids and target_ward not in request.state.ward_ids:
                    return JSONResponse({"detail": "Forbidden: out-of-scope ward"}, status_code=403)

        return await call_next(request)
