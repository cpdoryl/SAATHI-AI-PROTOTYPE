"""JWT authentication middleware for protected routes."""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt_handler import decode_token

security = HTTPBearer()


async def verify_jwt(credentials: HTTPAuthorizationCredentials = None):
    """Dependency: verify JWT token and return payload."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload
