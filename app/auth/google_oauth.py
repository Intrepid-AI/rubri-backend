import os
from typing import Dict, Any, Optional
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import json

from app.logger import get_logger
from app.db_ops.db_config import load_app_config

logger = get_logger(__name__)

class GoogleOAuthConfig:
    """Google OAuth configuration manager"""
    
    def __init__(self):
        # Load configuration
        app_config = load_app_config()
        google_config = app_config.get('google_oauth', {})
        
        # Google OAuth settings
        self.client_id = os.getenv('GOOGLE_CLIENT_ID', google_config.get('client_id', ''))
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET', google_config.get('client_secret', ''))
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', google_config.get('redirect_uri', 'http://localhost:8000/auth/google/callback'))
        
        # OAuth scopes
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        
        # Validate configuration
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials not configured. Authentication will not work.")
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
    
    def get_client_config(self) -> Dict[str, Any]:
        """Get client configuration for OAuth flow"""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

class GoogleOAuthManager:
    """Google OAuth authentication manager"""
    
    def __init__(self):
        self.config = GoogleOAuthConfig()
    
    def create_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Create Google OAuth authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Tuple of (authorization_url, state)
        """
        if not self.config.is_configured():
            raise ValueError("Google OAuth is not configured")
        
        flow = Flow.from_client_config(
            self.config.get_client_config(),
            scopes=self.config.scopes
        )
        flow.redirect_uri = self.config.redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        logger.info(f"Created Google OAuth authorization URL with state: {state}")
        return authorization_url, state
    
    def exchange_code_for_token(self, authorization_code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens
        
        Args:
            authorization_code: Authorization code from Google
            state: State parameter for verification
            
        Returns:
            Token information and user profile data
        """
        if not self.config.is_configured():
            raise ValueError("Google OAuth is not configured")
        
        try:
            flow = Flow.from_client_config(
                self.config.get_client_config(),
                scopes=self.config.scopes,
                state=state
            )
            flow.redirect_uri = self.config.redirect_uri
            
            # Exchange code for token
            flow.fetch_token(code=authorization_code)
            
            # Get user info from ID token
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                requests.Request(),
                self.config.client_id
            )
            
            logger.info(f"Successfully authenticated user: {id_info.get('email')}")
            
            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "id_token": credentials.id_token,
                "user_info": {
                    "google_id": id_info.get("sub"),
                    "email": id_info.get("email"),
                    "name": id_info.get("name"),
                    "given_name": id_info.get("given_name"),
                    "family_name": id_info.get("family_name"),
                    "picture": id_info.get("picture"),
                    "email_verified": id_info.get("email_verified", False)
                }
            }
            
        except Exception as e:
            logger.error(f"Error exchanging Google OAuth code: {e}")
            raise ValueError(f"Failed to authenticate with Google: {str(e)}")
    
    def verify_id_token(self, id_token_str: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Google ID token
        
        Args:
            id_token_str: Google ID token to verify
            
        Returns:
            User info if token is valid, None otherwise
        """
        if not self.config.is_configured():
            return None
        
        try:
            id_info = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                self.config.client_id
            )
            
            return {
                "google_id": id_info.get("sub"),
                "email": id_info.get("email"),
                "name": id_info.get("name"),
                "given_name": id_info.get("given_name"),
                "family_name": id_info.get("family_name"),
                "picture": id_info.get("picture"),
                "email_verified": id_info.get("email_verified", False)
            }
            
        except Exception as e:
            logger.warning(f"Invalid Google ID token: {e}")
            return None

# Global OAuth manager instance
google_oauth = GoogleOAuthManager()