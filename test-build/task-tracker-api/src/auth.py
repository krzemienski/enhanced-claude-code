import os
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# In production, store API keys securely (e.g., in a database or secret manager)
VALID_API_KEYS = set(os.getenv("API_KEYS", "").split(",")) if os.getenv("API_KEYS") else {"demo-api-key-123"}


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    
    Args:
        api_key (Optional[str]): API key from X-API-Key header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": f"ApiKey realm=\"{API_KEY_NAME}\""}
        )
    
    if api_key not in VALID_API_KEYS:
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": f"ApiKey realm=\"{API_KEY_NAME}\""}
        )
    
    logger.debug(f"API key validated successfully: {api_key[:8]}...")
    return api_key


class APIKeyAuth:
    """
    API Key authentication dependency class.
    Can be extended for more complex authentication logic.
    """
    
    def __init__(self, required_scopes: Optional[list] = None):
        """
        Initialize API key authentication.
        
        Args:
            required_scopes (Optional[list]): List of required scopes (for future use)
        """
        self.required_scopes = required_scopes or []
    
    async def __call__(self, api_key: str = Security(verify_api_key)) -> str:
        """
        Validate API key and check required scopes.
        
        Args:
            api_key (str): Validated API key
            
        Returns:
            str: The validated API key
        """
        # Future: Add scope validation logic here
        # For now, just return the validated API key
        return api_key


# Convenience dependency instances
require_api_key = Security(verify_api_key)
api_key_auth = APIKeyAuth()