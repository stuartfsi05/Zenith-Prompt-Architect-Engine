import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from supabase import Client, create_client

from src.core.config import Config

# Logger for Authentication events
logger = logging.getLogger("AuthService")


class AuthService:
    """
    Service responsible for orchestrating Authentication and Authorization
    via the Supabase Auth (GoTrue) ecosystem.

    Provides high-level methods for session management, token verification,
    and credential validation.
    """

    def __init__(self, config: Config):
        """
        Initializes the AuthService with application configuration.

        Args:
            config (Config): System-wide configuration settings.
        """
        self.config = config
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """
        Provides a lazy-loaded Supabase client instance.

        Returns:
            Client: The initialized Supabase client.

        Raises:
            RuntimeError: If the client fails to initialize.
        """
        if not self._client:
            try:
                self._client = create_client(
                    self.config.SUPABASE_URL, self.config.SUPABASE_KEY.get_secret_value()
                )
            except Exception as e:
                logger.critical(f"Auth Service Failure: Client initialization crashed: {e}")
                raise RuntimeError("Failed to connect to Authorization Provider.") from e
        return self._client

    def verify_token(self, token: str) -> Any:
        """
        Validates a JWT access token against the Auth Provider.

        Args:
            token (str): The raw JWT Bearer token.

        Returns:
            Any: The authorized User object if the token is valid.

        Raises:
            HTTPException: If the token is invalid, expired, or missing.
        """
        try:
            user_response = self.client.auth.get_user(token)

            if not user_response or not user_response.user:
                logger.warning("Access Denied: Token verification returned no valid user.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired session.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user_response.user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Internal Security Error: Token validation faulted: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security validation failed.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticates a user via email and password credentials.

        Args:
            email (str): User's registration email.
            password (str): User's password.

        Returns:
            Dict[str, Any]: A dictionary containing the 'access_token',
                'token_type', and 'user' metadata.

        Raises:
            HTTPException: If the credentials are incorrect or the account is locked.
        """
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if not response.session:
                raise ValueError("Auth Provider returned a null session.")

            return {
                "access_token": response.session.access_token,
                "token_type": response.session.token_type,
                "user": response.user,
            }
        except Exception as e:
            logger.warning(f"Login Failure for '{email}': {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Registers a new user via Supabase.

        Args:
            email (str): The email address for the new user.
            password (str): The chosen password for the user.

        Returns:
            Dict[str, Any]: A dictionary containing the session details.

        Raises:
            HTTPException: If registration fails.
        """
        try:
            response = self.client.auth.sign_up({"email": email, "password": password})
            
            # Note: Depending on Supabase configuration, users might need email confirmation.
            # If auto-confirm is enabled and email works without verification, a session will be returned.
            # If a session isn't returned, we notify the user.
            
            # Se for retornar a sessão diretamente para auto-login:
            if getattr(response, 'session', None):
                return {
                    "access_token": response.session.access_token,
                    "token_type": response.session.token_type,
                    "user": getattr(response, 'user', None),
                    "message": "Conta criada e autenticada com sucesso."
                }
            else:
                return {
                    "access_token": "",
                    "token_type": "Bearer",
                    "user": getattr(response, 'user', None),
                    "message": "Conta criada com sucesso. Verifique seu email para confirmar o acesso."
                }

        except Exception as e:
            logger.error(f"Registration Failure for '{email}': {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Falha ao criar conta. Talvez o email já esteja em uso ou a senha é muito fraca.",
            )

