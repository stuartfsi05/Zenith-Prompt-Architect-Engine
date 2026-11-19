import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    RequestLLMContext,
    get_agent,
    get_config,
    get_current_user,
    get_db,
    get_llm_context,
    get_quota_service,
    get_user_db,
)
from src.api.server import app
from src.core.services.quota import DemoQuotaService


class FakeStreamAgent:
    def __init__(self, mode: str, model: str, remaining_quota=None):
        self.mode = mode
        self.active_model_name = model
        self.remaining_quota = remaining_quota

    async def run_analysis_async(self, user_input: str, user_id: str, session_id: str):
        yield {
            "type": "meta",
            "content": "",
            "metadata": {
                "mode": self.mode,
                "model": self.active_model_name,
                "remaining_quota": self.remaining_quota,
            },
        }
        yield {"type": "chunk", "content": f"Echo: {user_input}"}


@pytest.fixture
def api_client(test_config, fake_db):
    current_user = SimpleNamespace(id="user-a", email="a@example.com", role="user")
    quota_service = DemoQuotaService(db=fake_db, daily_limit=2)

    def override_llm_ctx(x_google_api_key: str | None = None):
        return RequestLLMContext(
            mode="demo",
            api_key="server-key",
            primary_model=test_config.AUX_MODEL_NAME,
            primary_thinking_level="low",
        )

    app.dependency_overrides[get_config] = lambda: test_config
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_user_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_quota_service] = lambda: quota_service
    app.dependency_overrides[get_llm_context] = override_llm_ctx

    with TestClient(app) as client:
        yield client, fake_db, current_user, test_config

    app.dependency_overrides.clear()


def test_health_and_cors_headers(api_client):
    client, _, _, _ = api_client
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"

    preflight_prod = client.options(
        "/token",
        headers={
            "Origin": "https://zenith-interface-ten.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight_prod.status_code == 200
    assert (
        preflight_prod.headers.get("access-control-allow-origin")
        == "https://zenith-interface-ten.vercel.app"
    )

    preflight_blocked = client.options(
        "/token",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight_blocked.status_code == 400
    assert preflight_blocked.headers.get("access-control-allow-origin") is None

    blocked = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert blocked.headers.get("access-control-allow-origin") is None


def test_quota_and_chat_enforce_demo_limit_and_allow_byok(api_client):
    client, _, _, test_config = api_client

    # Initial demo quota is 2
    q_res = client.get("/quota")
    assert q_res.status_code == 200
    assert q_res.json() == {
        "mode": "demo",
        "model": "gemini-3.5-flash-lite",
        "daily_limit": 5,
        "remaining": 2,
    }

    app.dependency_overrides[get_agent] = lambda: FakeStreamAgent(
        mode="demo", model="gemini-3.5-flash-lite"
    )

    for _ in range(2):
        r = client.post("/chat", json={"message": "Oi", "session_id": "s1"})
        assert r.status_code == 200
        lines = [json.loads(line) for line in r.text.strip().splitlines()]
        assert lines[0]["type"] == "meta"
        assert lines[1]["content"] == "Echo: Oi"

    # 3rd message in demo mode hits 429
    r_429 = client.post("/chat", json={"message": "Oi 3", "session_id": "s1"})
    assert r_429.status_code == 429
    assert "Google API Key" in r_429.json()["detail"]

    # Switching to BYOK bypasses server demo quota
    app.dependency_overrides[get_llm_context] = lambda: RequestLLMContext(
        mode="byok",
        api_key="user-key",
        primary_model=test_config.MODEL_NAME,
        primary_thinking_level="medium",
    )
    app.dependency_overrides[get_agent] = lambda: FakeStreamAgent(
        mode="byok", model="gemini-3.8-flash"
    )

    q_byok = client.get("/quota")
    assert q_byok.json()["mode"] == "byok"
    assert q_byok.json()["remaining"] is None

    r_byok = client.post("/chat", json={"message": "Com BYOK", "session_id": "s1"})
    assert r_byok.status_code == 200


def test_sessions_messages_and_delete_ownership(api_client):
    client, fake_db, _, _ = api_client

    fake_db.create_session("sess-owned", "user-a")
    fake_db.log_interaction("sess-owned", "user-a", "user", "Minha pergunta")
    fake_db.create_session("sess-other", "user-b")
    fake_db.log_interaction("sess-other", "user-b", "user", "Segredo do B")

    list_res = client.get("/sessions")
    assert list_res.status_code == 200
    assert [s["id"] for s in list_res.json()["sessions"]] == ["sess-owned"]

    own_msgs = client.get("/sessions/sess-owned/messages")
    assert own_msgs.status_code == 200
    assert own_msgs.json()["messages"][0]["parts"] == ["Minha pergunta"]

    other_msgs = client.get("/sessions/sess-other/messages")
    assert other_msgs.status_code == 200
    assert other_msgs.json()["messages"] == []

    del_other = client.delete("/sessions/sess-other")
    assert del_other.status_code == 404

    del_own = client.delete("/sessions/sess-owned")
    assert del_own.status_code == 200
    assert client.get("/sessions/sess-owned/messages").json()["messages"] == []
