"""
backend/middleware.py — FastAPI middlewares for authentication, rate limiting, logging, and RBAC.
"""

import time
import jwt
import logging
from typing import Callable, Dict, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sampark.gateway")

from backend.config import settings

# 13.3 In-memory rate limiter mock (replaces Redis)
_rate_limit_cache: Dict[str, List[float]] = {}
RATE_LIMIT_MAX_REQ = 60
RATE_LIMIT_WINDOW = 60.0

class LoggingMiddleware(BaseHTTPMiddleware):
    """13.7 Request logging middleware (mocks Cloud Logging)."""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # We process the request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            latency_ms = (time.time() - start_time) * 1000
            user_id = getattr(request.state, "user_id", "anonymous")
            
            # Mocks writing to Cloud Logging
            logger.info(
                "Request: method=%s path=%s user_id=%s status=%s latency_ms=%.2f",
                request.method, request.url.path, user_id, status_code, latency_ms
            )
            
        return response

class AuthAndRateLimitMiddleware(BaseHTTPMiddleware):
    """13.2 JWT Auth and 13.3 Rate Limiting, 13.6 RBAC."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for public endpoints
        if request.url.path in ("/health", "/auth/login", "/docs", "/openapi.json"):
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Missing or invalid Authorization header"}, status_code=401)
            
        token = auth_header.split(" ")[1]
        try:
            # 13.2 Validate JWT signature and exp
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("user_id")
            if not user_id:
                return JSONResponse({"detail": "Token missing user_id"}, status_code=401)
                
            request.state.user_id = user_id
            request.state.role = payload.get("role", "citizen")
            request.state.ward_ids = payload.get("ward_ids", [])
            
        except jwt.ExpiredSignatureError:
            return JSONResponse({"detail": "Token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "Invalid token"}, status_code=401)
            
        # 13.3 Sliding-window rate limiter
        now = time.time()
        user_timestamps = _rate_limit_cache.get(user_id, [])
        # Prune old timestamps
        user_timestamps = [ts for ts in user_timestamps if now - ts < RATE_LIMIT_WINDOW]
        
        if len(user_timestamps) >= RATE_LIMIT_MAX_REQ:
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(int(RATE_LIMIT_WINDOW))}
            )
            
        user_timestamps.append(now)
        _rate_limit_cache[user_id] = user_timestamps
        
        # 13.6 RBAC Check
        # If the endpoint implies a ward (e.g. /analytics/ward/{ward_id}), verify access
        path_parts = request.url.path.split("/")
        if "ward" in path_parts:
            ward_idx = path_parts.index("ward")
            if len(path_parts) > ward_idx + 1:
                target_ward = path_parts[ward_idx + 1]
                if request.state.role in ("community_leader", "government_officer"):
                    if target_ward not in request.state.ward_ids and "*" not in request.state.ward_ids:
                        return JSONResponse({"detail": "Forbidden: out-of-scope ward"}, status_code=403)

        return await call_next(request)
