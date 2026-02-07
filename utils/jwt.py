import jwt
import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SECRET_KEY = os.getenv("BETTER_AUTH_SECRET")

if not SECRET_KEY:
    raise ValueError("BETTER_AUTH_SECRET environment variable is not set")


def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None

        return payload
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token

    Args:
        token: JWT token string

    Returns:
        User ID if valid token, None otherwise
    """
    payload = verify_jwt(token)
    if payload:
        return payload.get("sub")  # Subject is user ID
    return None
