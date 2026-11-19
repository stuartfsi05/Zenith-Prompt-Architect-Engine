import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

# Ensure Settings never fails in CI/local runs without .env
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-google-api-key-000000000000")

from src.core.config import Config  # noqa: E402


class FakeResponse:
    def __init__(self, data: Any = None, count: Optional[int] = None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, tables: Dict[str, List[Dict[str, Any]]], table_name: str):
        self.tables = tables
        self.table_name = table_name
        self.op = "select"
        self.filters: List[tuple[str, str, Any]] = []
        self.payload: Any = None
        self.on_conflict: Optional[str] = None
        self.order_col: Optional[str] = None
        self.order_desc = False
        self.limit_val: Optional[int] = None
        self.want_count = False

    def select(self, _cols: str = "*", count: Optional[str] = None):
        self.op = "select"
        self.want_count = count == "exact"
        return self

    def insert(self, data: Dict[str, Any]):
        self.op = "insert"
        self.payload = dict(data)
        return self

    def update(self, data: Dict[str, Any]):
        self.op = "update"
        self.payload = dict(data)
        return self

    def upsert(self, data: Dict[str, Any], on_conflict: Optional[str] = None):
        self.op = "upsert"
        self.payload = dict(data)
        self.on_conflict = on_conflict
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col: str, val: Any):
        self.filters.append(("eq", col, val))
        return self

    def gte(self, col: str, val: Any):
        self.filters.append(("gte", col, val))
        return self

    def order(self, col: str, desc: bool = False):
        self.order_col = col
        self.order_desc = desc
        return self

    def limit(self, val: int):
        self.limit_val = val
        return self

    def _matches(self, row: Dict[str, Any]) -> bool:
        for kind, col, val in self.filters:
            if kind == "eq" and row.get(col) != val:
                return False
            if kind == "gte" and str(row.get(col, "")) < str(val):
                return False
        return True

    def execute(self) -> FakeResponse:
        rows = self.tables.setdefault(self.table_name, [])

        if self.op == "insert":
            row = dict(self.payload)
            if "id" not in row and self.table_name == "interactions":
                row["id"] = len(rows) + 1
            rows.append(row)
            return FakeResponse(data=[row])

        if self.op == "upsert":
            conflict_key = self.on_conflict or "id"
            val = self.payload.get(conflict_key)
            for idx, existing in enumerate(rows):
                if existing.get(conflict_key) == val:
                    rows[idx] = {**existing, **self.payload}
                    return FakeResponse(data=[rows[idx]])
            rows.append(dict(self.payload))
            return FakeResponse(data=[self.payload])

        if self.op == "update":
            updated = []
            for idx, row in enumerate(rows):
                if self._matches(row):
                    rows[idx] = {**row, **self.payload}
                    updated.append(rows[idx])
            return FakeResponse(data=updated)

        if self.op == "delete":
            kept = []
            deleted = []
            for row in rows:
                if self._matches(row):
                    deleted.append(row)
                else:
                    kept.append(row)
            self.tables[self.table_name] = kept
            return FakeResponse(data=deleted)

        matched = [dict(r) for r in rows if self._matches(r)]
        if self.order_col:
            matched.sort(
                key=lambda r: r.get(self.order_col, ""), reverse=self.order_desc
            )
        total_count = len(matched)
        if self.limit_val is not None:
            matched = matched[: self.limit_val] if self.limit_val > 0 else []
        return FakeResponse(
            data=matched, count=total_count if self.want_count else None
        )


class FakeSupabaseClient:
    """In-memory mock matching the Supabase Python client query interface."""

    def __init__(self):
        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "sessions": [],
            "interactions": [],
            "usage_logs": [],
            "user_memories": [],
        }

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.tables, name)


class InMemoryPersistence:
    """In-memory PersistenceLayer implementation for unit and API tests."""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.interactions: List[Dict[str, Any]] = []
        self.usage_logs: List[Dict[str, Any]] = []
        self.memories: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, user_id: str) -> None:
        if (
            session_id in self.sessions
            and self.sessions[session_id]["user_id"] != user_id
        ):
            return
        self.sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "last_active": datetime.now(timezone.utc).isoformat(),
        }

    def log_interaction(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        if (
            session_id in self.sessions
            and self.sessions[session_id]["user_id"] != user_id
        ):
            return
        self.create_session(session_id, user_id)
        self.interactions.append(
            {
                "id": len(self.interactions) + 1,
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            }
        )

    def get_history(
        self, session_id: str, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        if not session or session["user_id"] != user_id:
            return []
        items = [i for i in self.interactions if i["session_id"] == session_id][-limit:]
        return [
            {"role": i["role"], "parts": [i["content"]], "metadata": i["metadata"]}
            for i in items
        ]

    def get_sessions(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        rows = [s for s in self.sessions.values() if s["user_id"] == user_id]
        rows.sort(key=lambda r: r["last_active"], reverse=True)
        return [{"id": r["id"], "last_active": r["last_active"]} for r in rows[:limit]]

    def delete_session(self, session_id: str, user_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session or session["user_id"] != user_id:
            return False
        self.sessions.pop(session_id, None)
        self.interactions = [
            i for i in self.interactions if i["session_id"] != session_id
        ]
        return True

    def log_usage(
        self,
        user_id: str,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None:
        self.usage_logs.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_daily_request_count(self, user_id: str) -> int:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return sum(
            1
            for log in self.usage_logs
            if log["user_id"] == user_id and str(log["timestamp"]).startswith(today)
        )

    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        return self.memories.get(user_id, {"master_summary": "", "user_profile": {}})

    def save_user_memory(
        self, user_id: str, master_summary: str, user_profile: Dict[str, Any]
    ) -> None:
        self.memories[user_id] = {
            "master_summary": master_summary,
            "user_profile": dict(user_profile),
        }


@pytest.fixture
def test_config() -> Config:
    return Config(
        GOOGLE_API_KEY="test-dummy-google-api-key-000000000000",
        DEMO_DAILY_LIMIT=5,
        ALLOWED_ORIGINS="http://localhost:5173,https://zenith.example.com",
    )


@pytest.fixture
def fake_db() -> InMemoryPersistence:
    return InMemoryPersistence()
