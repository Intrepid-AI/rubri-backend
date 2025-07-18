from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets
from datetime import datetime

from app.api.v1.datamodels import ErrorResponse
from app.db_ops.database import get_db
from app.db_ops import crud
from app.db_ops.db_config import load_app_config
from app.auth.google_oauth import google_oauth
from app.auth.jwt_utils import create_token_pair, hash_token, decode_token
from app.auth.dependencies import require_auth, get_optional_user
from app.logger import get_logger

# Initialize router
router = APIRouter()

# Initialize logger
logger = get_logger(__name__)

@router.get("/google/login", tags=["Authentication"])
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow
    
    Returns a redirect URL to Google's OAuth authorization page.
    """
    try:
        if not google_oauth.config.is_configured():
            raise HTTPException(
                status_code=500,
                detail="Google OAuth is not configured on the server"
            )
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in session or return it for client-side storage
        authorization_url, _ = google_oauth.create_authorization_url(state)
        
        logger.info("Generated Google OAuth authorization URL")
        
        return {
            "authorization_url": authorization_url,
            "state": state
        }
        
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate Google authentication: {str(e)}"
        )

@router.get("/google/callback", tags=["Authentication"])
async def google_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback
    
    Exchanges the authorization code for tokens and user information,
    then creates or updates the user account and returns JWT tokens.
    """
    if error:
        logger.warning(f"Google OAuth error: {error}")
        raise HTTPException(
            status_code=400,
            detail=f"Google authentication failed: {error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=400,
            detail="Authorization code not provided"
        )
    
    try:
        # Exchange code for tokens and user info
        oauth_result = google_oauth.exchange_code_for_token(code, state)
        user_info = oauth_result["user_info"]
        
        if not user_info.get("email_verified"):
            raise HTTPException(
                status_code=400,
                detail="Email address not verified with Google"
            )
        
        # Check if user exists
        existing_user = crud.get_user_by_google_id(db, user_info["google_id"])
        
        if existing_user:
            # Update existing user's info and login time
            existing_user.name = user_info["name"]
            existing_user.given_name = user_info.get("given_name")
            existing_user.family_name = user_info.get("family_name")
            existing_user.picture_url = user_info.get("picture")
            crud.update_user_login_time(db, existing_user.user_id)
            user = existing_user
            logger.info(f"User logged in: {user.email}")
        else:
            # Create new user
            user = crud.create_user(
                db=db,
                google_id=user_info["google_id"],
                email=user_info["email"],
                name=user_info["name"],
                given_name=user_info.get("given_name"),
                family_name=user_info.get("family_name"),
                picture_url=user_info.get("picture")
            )
            logger.info(f"New user registered: {user.email}")
        
        # Create JWT tokens
        tokens = create_token_pair(
            user_id=user.user_id,
            email=user.email,
            name=user.name
        )
        
        # Create session record
        access_token_hash = hash_token(tokens["access_token"])
        refresh_token_hash = hash_token(tokens["refresh_token"])
        
        user_agent = request.headers.get("User-Agent") if request else None
        ip_address = request.client.host if request and hasattr(request, 'client') else None
        
        crud.create_user_session(
            db=db,
            user_id=user.user_id,
            access_token_hash=access_token_hash,
            refresh_token_hash=refresh_token_hash,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Redirect to frontend question generation page with tokens as URL parameters
        app_config = load_app_config()
        frontend_url = app_config.get('frontend_url', 'http://localhost:3000')
        redirect_url = f"{frontend_url}/generator?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error processing Google OAuth callback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/logout", tags=["Authentication"])
async def logout(
    user = Depends(require_auth),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Logout current user
    
    Invalidates the current session and JWT token.
    """
    try:
        # Get the current token from the Authorization header
        auth_header = request.headers.get("Authorization") if request else None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            token_hash = hash_token(token)
            
            # Find and delete the session
            session = crud.get_user_session_by_token_hash(db, token_hash)
            if session:
                crud.delete_user_session(db, session.session_id)
                logger.info(f"User logged out: {user.email}")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=500,
            detail="Logout failed"
        )

@router.get("/me", tags=["Authentication"])
async def get_current_user_profile(user = Depends(require_auth)):
    """
    Get current user profile
    
    Returns the authenticated user's profile information.
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "picture_url": user.picture_url,
        "email_notifications_enabled": user.email_notifications_enabled == "true",
        "preferred_llm_provider": user.preferred_llm_provider,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at
    }

@router.put("/me/preferences", tags=["Authentication"])
async def update_user_preferences(
    preferences: dict,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update user preferences
    
    Allows users to update their notification and LLM provider preferences.
    """
    try:
        email_notifications = preferences.get("email_notifications_enabled")
        llm_provider = preferences.get("preferred_llm_provider")
        
        updated_user = crud.update_user_preferences(
            db=db,
            user_id=user.user_id,
            email_notifications_enabled=email_notifications,
            preferred_llm_provider=llm_provider
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        logger.info(f"Updated preferences for user: {user.email}")
        
        return {
            "message": "Preferences updated successfully",
            "user": {
                "email_notifications_enabled": updated_user.email_notifications_enabled == "true",
                "preferred_llm_provider": updated_user.preferred_llm_provider
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update preferences"
        )

@router.post("/refresh", tags=["Authentication"])
async def refresh_access_token(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Generates a new access token using a valid refresh token.
    """
    try:
        # Extract refresh token from request body
        refresh_token = request.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=422,
                detail="refresh_token is required"
            )
        
        # Decode and validate refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token payload"
            )
        
        # Get user
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        # Verify refresh token exists in session
        refresh_token_hash = hash_token(refresh_token)
        session = db.query(crud.models.UserSession).filter(
            crud.models.UserSession.user_id == user_id,
            crud.models.UserSession.refresh_token_hash == refresh_token_hash
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Refresh token not found in active sessions"
            )
        
        # Create new access token
        new_tokens = create_token_pair(
            user_id=user.user_id,
            email=user.email,
            name=user.name
        )
        
        # Update session with new token hashes
        session.access_token_hash = hash_token(new_tokens["access_token"])
        session.refresh_token_hash = hash_token(new_tokens["refresh_token"])
        session.last_accessed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Refreshed tokens for user: {user.email}")
        
        return new_tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=500,
            detail="Token refresh failed"
        )