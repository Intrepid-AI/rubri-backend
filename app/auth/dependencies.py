from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.db_ops.database import get_db
from app.db_ops import crud
from app.db_ops.models import User, UserSession
from app.auth.jwt_utils import decode_token, hash_token
from app.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("user_id")
    if not user_id:
        return None
    
    # Get user from database
    user = crud.get_user_by_id(db, user_id)
    if not user:
        logger.warning(f"User not found for token: {user_id}")
        return None
    
    # Verify token is in active sessions
    token_hash = hash_token(token)
    session = crud.get_user_session_by_token_hash(db, token_hash)
    if not session:
        logger.warning(f"Token not found in active sessions: {user_id}")
        return None
    
    # Update last accessed time
    crud.update_user_session_last_accessed(db, session.session_id)
    
    logger.debug(f"Authenticated user: {user.email}")
    return user

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Require authentication - raises 401 if not authenticated
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: 401 if not authenticated
    """
    user = await get_current_user(credentials, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, but don't require authentication
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    return await get_current_user(credentials, db)