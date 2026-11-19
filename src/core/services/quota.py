import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from src.core.database import PersistenceLayer


class QuotaExceededError(Exception):
    """Raised when a user exhausts their daily Demo Mode request quota."""

    def __init__(self, limit: int, used: int):
        self.limit = limit
        self.used = used
        super().__init__(
            f"Daily demo quota exceeded ({used}/{limit} requests used today)."
        )


class DemoQuotaService:
    """Enforces per-user daily message limits for zero-friction Demo Mode."""

    def __init__(self, db: PersistenceLayer, daily_limit: int = 5):
        self.db = db
        self.daily_limit = daily_limit
        self._lock = threading.Lock()
        self._local_counts: Dict[Tuple[str, str], int] = {}

    @staticmethod
    def _today_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_used_today(
        self, user_id: str, db: Optional[PersistenceLayer] = None
    ) -> int:
        """Returns the highest known usage count today across memory and DB."""
        today = self._today_key()
        key = (user_id, today)
        local_count = self._local_counts.get(key, 0)
        active_db = db or self.db
        db_count = active_db.get_daily_request_count(user_id)
        return max(local_count, db_count)

    def get_remaining(self, user_id: str, db: Optional[PersistenceLayer] = None) -> int:
        """Returns remaining Demo Mode requests available today for the user."""
        with self._lock:
            used = self.get_used_today(user_id, db=db)
            return max(0, self.daily_limit - used)

    def check_and_consume(
        self, user_id: str, db: Optional[PersistenceLayer] = None
    ) -> int:
        """Checks quota atomically and reserves one request slot, returning remaining."""
        today = self._today_key()
        key = (user_id, today)
        with self._lock:
            used = self.get_used_today(user_id, db=db)
            if used >= self.daily_limit:
                raise QuotaExceededError(limit=self.daily_limit, used=used)
            new_used = used + 1
            self._local_counts[key] = new_used
            return self.daily_limit - new_used
