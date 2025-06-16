import os
import logging
from typing import Optional, Annotated
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.status import HTTP_403_FORBIDDEN

logger = logging.getLogger(__name__)

API_KEYS = set(os.getenv("API_KEYS", "test-api-key-123").split(","))

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API key for authentication"
)

api_key_query = APIKeyQuery(
    name="api_key",
    auto_error=False,
    description="API key for authentication (query parameter)"
)


def get_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> str:
    api_key = api_key_header or api_key_query
    
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Please provide it in the X-API-Key header or api_key query parameter."
        )
    
    if api_key not in API_KEYS:
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key


APIKey = Annotated[str, Security(get_api_key)]


def require_api_key(api_key: APIKey) -> str:
    return api_key


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
        self.cleanup_interval = 300
        self.last_cleanup = 0
    
    def check_rate_limit(self, api_key: str) -> bool:
        import time
        current_time = time.time()
        
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
        
        if api_key not in self.requests:
            self.requests[api_key] = []
        
        self.requests[api_key] = [
            timestamp for timestamp in self.requests[api_key]
            if current_time - timestamp < self.window_seconds
        ]
        
        if len(self.requests[api_key]) >= self.max_requests:
            return False
        
        self.requests[api_key].append(current_time)
        return True
    
    def _cleanup_old_entries(self, current_time: float):
        import time
        for api_key in list(self.requests.keys()):
            self.requests[api_key] = [
                timestamp for timestamp in self.requests[api_key]
                if current_time - timestamp < self.window_seconds
            ]
            if not self.requests[api_key]:
                del self.requests[api_key]
        self.last_cleanup = current_time


rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
)


def check_rate_limit(api_key: APIKey) -> str:
    if not rate_limiter.check_rate_limit(api_key):
        logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    return api_key