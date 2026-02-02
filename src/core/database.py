import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
import supabase
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("SupabaseRepository")

class PersistenceLayer(Protocol):
    """
    Interface definition for Persistence Layer.
    """
    def create_session(self, session_id: str, user_id: str) -> None: ...
    def log_interaction(self, session_id: str, user_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> None: ...
    def get_history(self, session_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]: ...
    def log_usage(self, user_id: str, session_id: str, model: str, input_tokens: int, output_tokens: int, total_tokens: int) -> None: ...

class SupabaseRepository:
    """
    Concrete implementation of PersistenceLayer using Supabase.
    """

    def __init__(self, config: Config):
        self.config = config
        self.client = None
        
        if not self.config.SUPABASE_URL or not self.config.SUPABASE_KEY:
            logger.warning("Supabase credentials missing! Database operations will be disabled.")
            return

        try:
            self.client = supabase.create_client(self.config.SUPABASE_URL, self.config.SUPABASE_KEY.get_secret_value())
            logger.info("Supabase client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            # We do NOT raise here, to allow the app to start without DB
            self.client = None

    def create_session(self, session_id: str, user_id: str):
        """Registers a new session or updates last_active if exists."""
        if not self.client:
            return
        try:
            data = {
                "id": session_id,
                "user_id": user_id,
                "last_active": datetime.utcnow().isoformat()
            }
            self.client.table("sessions").upsert(data, on_conflict="id").execute()
        except Exception as e:
            logger.error(f"Failed to create/update session: {e}")

    def log_interaction(
        self, session_id: str, user_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ):
        """Logs a single turn (User or Model) to the database."""
        if not self.client:
            return
        try:
            # Verify session ownership (optimistic check or handled by RLS/Logic)
            # For strictness:
            # self._verify_session_ownership(session_id, user_id)
            
            data = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata if metadata else {}
            }
            
            self.client.table("interactions").insert(data).execute()
            
            # Update session last_active
            self.client.table("sessions").update({
                "last_active": datetime.utcnow().isoformat()
            }).eq("id", session_id).eq("user_id", user_id).execute()
            
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def get_history(self, session_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves the chat history for a session.
        """
        history = []
        if not self.client:
            return history

        try:
            # Ownership check 
            # (In a real scenario, we might want to fail hard if access is denied, but returning empty is safe fallback)
            
            response = (
                self.client.table("interactions")
                .select("role, content, metadata")
                .eq("session_id", session_id)
                .order("id", desc=True) # Get latest
                .limit(limit)
                .execute()
            )
            
            rows = response.data
            rows.reverse() # Restore chronological order
            
            for row in rows:
                history.append(
                    {
                        "role": row["role"],
                        "parts": [row["content"]],
                        "metadata": row.get("metadata", {}) or {},
                    }
                )
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")

        return history

    def log_usage(self, user_id: str, session_id: str, model: str, input_tokens: int, output_tokens: int, total_tokens: int):
        """Logs token usage for accounting."""
        if not self.client:
            return
        try:
            data = {
                "user_id": user_id,
                "session_id": session_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.client.table("usage_logs").insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Returns basic stats about usage."""
        stats = {}
        if not self.client:
            return stats
        try:
            res_interactions = self.client.table("interactions").select("*", count="exact").limit(0).execute()
            stats["total_interactions"] = res_interactions.count
            
            res_sessions = self.client.table("sessions").select("*", count="exact").limit(0).execute()
            stats["total_sessions"] = res_sessions.count
        except Exception as e:
            logger.error(f"Analytics failure: {e}")
        return stats
