import time
import logging
from collections import defaultdict
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        client_id = self.get_client_id(request)
        
        current_time = time.time()
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if current_time - req_time < self.window_size
        ]
        
        if len(self.requests[client_id]) >= self.requests_per_minute:
            logger.warning(f"[RATE_LIMIT] Client {client_id} exceeded rate limit")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."},
                headers={"Retry-After": "60"},
            )
        
        self.requests[client_id].append(current_time)
        
        response = await call_next(request)
        
        remaining = self.requests_per_minute - len(self.requests[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))
        
        return response
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from auth import verify_token
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"user_{user_id}"
            except:
                pass
        
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"
