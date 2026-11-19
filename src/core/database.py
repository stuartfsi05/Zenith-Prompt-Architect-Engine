from datetime import datetime, timezone
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

    def log_interaction(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> None: ...

    def get_history(
        self, session_id: str, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]: ...

    def get_sessions(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]: ...

    def delete_session(self, session_id: str, user_id: str) -> bool: ...

    def log_usage(
        self,
        user_id: str,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None: ...

    def get_daily_request_count(self, user_id: str) -> int: ...

    def get_user_memory(self, user_id: str) -> Dict[str, Any]: ...

    def save_user_memory(
        self, user_id: str, master_summary: str, user_profile: Dict[str, Any]
    ) -> None: ...


class SupabaseRepository:
    """
    Concrete implementation of PersistenceLayer using Supabase.
    """

    def __init__(self, config: Config, access_token: Optional[str] = None):
        self.config = config
        self.client = None

        if not self.config.SUPABASE_URL or not self.config.SUPABASE_KEY:
            logger.warning(
                "Supabase credentials missing! Database operations will be disabled."
            )
            return

        try:
            self.client = supabase.create_client(
                self.config.SUPABASE_URL, self.config.SUPABASE_KEY.get_secret_value()
            )
            if access_token:
                self.client.postgrest.auth(access_token)
            logger.info("Supabase client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            # We do NOT raise here, to allow the app to start without DB
            self.client = None

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _verify_session_ownership(self, session_id: str, user_id: str) -> bool:
        """Returns True if the given session exists and belongs to user_id."""
        if not self.client or not session_id or not user_id:
            return False
        try:
            response = (
                self.client.table("sessions")
                .select("id")
                .eq("id", session_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            logger.error(f"Ownership check failed for session {session_id}: {e}")
            return False

    def create_session(self, session_id: str, user_id: str) -> None:
        """Registers a new session or updates last_active if owned by user_id."""
        if not self.client or not session_id or not user_id:
            return
        try:
            existing = (
                self.client.table("sessions")
                .select("user_id")
                .eq("id", session_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                if existing.data[0].get("user_id") != user_id:
                    logger.warning(
                        f"Blocked cross-tenant create_session attempt on {session_id}"
                    )
                    return
                (
                    self.client.table("sessions")
                    .update({"last_active": self._utc_now_iso()})
                    .eq("id", session_id)
                    .eq("user_id", user_id)
                    .execute()
                )
                return

            data = {
                "id": session_id,
                "user_id": user_id,
                "last_active": self._utc_now_iso(),
            }
            self.client.table("sessions").insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to create/update session: {e}")

    def log_interaction(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Logs a single turn (User or Model) to the database with ownership check."""
        if not self.client or not session_id or not user_id:
            return
        try:
            existing = (
                self.client.table("sessions")
                .select("user_id")
                .eq("id", session_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                if existing.data[0].get("user_id") != user_id:
                    logger.warning(
                        f"Unauthorized log_interaction blocked for session {session_id}"
                    )
                    return
            else:
                self.create_session(session_id, user_id)

            now_iso = self._utc_now_iso()
            data = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": now_iso,
                "metadata": metadata if metadata else {},
            }

            self.client.table("interactions").insert(data).execute()

            self.client.table("sessions").update({"last_active": now_iso}).eq(
                "id", session_id
            ).eq("user_id", user_id).execute()

        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def get_history(
        self, session_id: str, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the chat history for a session owned by user_id.
        """
        history: List[Dict[str, Any]] = []
        if not self.client or not self._verify_session_ownership(session_id, user_id):
            return history

        try:
            response = (
                self.client.table("interactions")
                .select("role, content, metadata")
                .eq("session_id", session_id)
                .order("id", desc=True)
                .limit(limit)
                .execute()
            )

            rows = response.data or []
            rows.reverse()

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

    def get_sessions(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recent sessions for a user."""
        if not self.client or not user_id:
            return []
        try:
            response = (
                self.client.table("sessions")
                .select("id, last_active")
                .eq("user_id", user_id)
                .order("last_active", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch sessions: {e}")
            return []

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Deletes a session and its interactions after verifying ownership."""
        if not self.client or not self._verify_session_ownership(session_id, user_id):
            return False
        try:
            self.client.table("interactions").delete().eq(
                "session_id", session_id
            ).execute()
            self.client.table("sessions").delete().eq("id", session_id).eq(
                "user_id", user_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def log_usage(
        self,
        user_id: str,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None:
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
                "timestamp": self._utc_now_iso(),
            }
            self.client.table("usage_logs").insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")

    def get_daily_request_count(self, user_id: str) -> int:
        """Counts usage log entries recorded today (UTC) for user_id."""
        if not self.client or not user_id:
            return 0
        try:
            midnight_utc = (
                datetime.now(timezone.utc)
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat()
            )
            response = (
                self.client.table("usage_logs")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .gte("timestamp", midnight_utc)
                .limit(0)
                .execute()
            )
            return int(response.count or 0)
        except Exception as e:
            logger.error(f"Failed to query daily request count for {user_id}: {e}")
            return 0

    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """Retrieves per-user semantic memory summary and profile from Supabase."""
        default_mem: Dict[str, Any] = {"master_summary": "", "user_profile": {}}
        if not self.client or not user_id:
            return default_mem
        try:
            response = (
                self.client.table("user_memories")
                .select("master_summary, user_profile")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if response.data:
                row = response.data[0]
                return {
                    "master_summary": row.get("master_summary") or "",
                    "user_profile": row.get("user_profile") or {},
                }
        except Exception as e:
            logger.warning(f"Failed to load user memory for {user_id}: {e}")
        return default_mem

    def save_user_memory(
        self, user_id: str, master_summary: str, user_profile: Dict[str, Any]
    ) -> None:
        """Persists per-user semantic memory summary and profile to Supabase."""
        if not self.client or not user_id:
            return
        try:
            payload = {
                "user_id": user_id,
                "master_summary": master_summary,
                "user_profile": user_profile,
                "updated_at": self._utc_now_iso(),
            }
            self.client.table("user_memories").upsert(
                payload, on_conflict="user_id"
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to save user memory for {user_id}: {e}")

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Returns basic stats about usage."""
        stats: Dict[str, Any] = {}
        if not self.client:
            return stats
        try:
            res_interactions = (
                self.client.table("interactions")
                .select("*", count="exact")
                .limit(0)
                .execute()
            )
            stats["total_interactions"] = res_interactions.count

            res_sessions = (
                self.client.table("sessions")
                .select("*", count="exact")
                .limit(0)
                .execute()
            )
            stats["total_sessions"] = res_sessions.count
        except Exception as e:
            logger.error(f"Analytics failure: {e}")
        return stats
