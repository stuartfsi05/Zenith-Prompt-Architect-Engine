from typing import Optional
import logging
from supabase import create_client, Client
from fastapi import HTTPException, status
from src.core.config import Config

logger = logging.getLogger("AuthService")

class AuthService:
    """
    Service responsible for handling Authentication and Authorization
    using Supabase Auth.
    """

    def __init__(self, config: Config):
        self.config = config
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """
        Lazy initialization of the Supabase client for Auth.
        """
        if not self._client:
            try:
                self._client = create_client(self.config.SUPABASE_URL, self.config.SUPABASE_KEY)
            except Exception as e:
                logger.critical(f"Failed to initialize Supabase Auth Client: {e}")
                raise e
        return self._client

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verifies a JWT token with Supabase Auth.
        Returns the User object (dict/model) if valid, raises HTTPException otherwise.
        """
        try:
            user_response = self.client.auth.get_user(token)
            
            if not user_response or not user_response.user:
                 logger.warning("Token verification failed: No user found.")
                 raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user_response.user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected Auth Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
