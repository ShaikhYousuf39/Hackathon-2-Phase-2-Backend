from fastapi import Request, HTTPException, status
from utils.jwt import verify_jwt


async def verify_jwt_middleware(request: Request):
    """
    Middleware to verify JWT token in Authorization header

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>"
        )

    token = parts[1]
    payload = verify_jwt(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Attach user info to request state
    request.state.user_id = payload.get("sub")
    request.state.user_email = payload.get("email")
