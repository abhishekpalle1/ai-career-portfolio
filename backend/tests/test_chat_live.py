from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.core.config import Settings, get_settings
from app.main import app
from app.models.chat import ChatResponse
from app.services.rag_assistant import UNAVAILABLE_MESSAGE, AssistantUnavailableError
from tests.rag_fakes import live_settings


def _fake_live_answer(message: str) -> ChatResponse:
    return ChatResponse(
        answer=f"live: {message}",
        citations=[],
        suggested_questions=[],
        intent="PROFILE_SUMMARY",
        grounded=True,
        abstained=False,
        trace_id="t",
    )


def test_mock_is_served_when_live_flags_are_off(client: TestClient) -> None:
    body = client.post("/api/v1/chat", json={"message": "Where has Abhishek worked?"}).json()

    assert "[EMPLOYER_1_NAME_TO_BE_PROVIDED]" in body["answer"]


def test_mock_is_served_when_only_one_live_flag_is_on(client: TestClient) -> None:
    for overrides in ({"enable_live_rag": False}, {"enable_live_model_calls": False}):
        app.dependency_overrides[get_settings] = lambda o=overrides: live_settings(**o)
        body = client.post("/api/v1/chat", json={"message": "Where has Abhishek worked?"}).json()
        assert "[EMPLOYER_1_NAME_TO_BE_PROVIDED]" in body["answer"]


def test_live_assistant_is_used_when_both_flags_are_on(client: TestClient) -> None:
    settings = live_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[chat_module.get_assistant] = lambda: _fake_live_answer

    body = client.post("/api/v1/chat", json={"message": "hello"}).json()

    assert body["answer"] == "live: hello"


def test_dependency_failure_returns_generic_503(client: TestClient) -> None:
    def failing(message: str) -> ChatResponse:
        raise AssistantUnavailableError("internal detail")

    app.dependency_overrides[chat_module.get_assistant] = lambda: failing

    response = client.post("/api/v1/chat", json={"message": "Where has he worked?"})

    assert response.status_code == 503
    assert response.json() == {"detail": UNAVAILABLE_MESSAGE}
    assert "internal detail" not in response.text


def test_incomplete_live_configuration_returns_503_without_network(client: TestClient) -> None:
    incomplete = Settings(_env_file=None, enable_live_rag=True, enable_live_model_calls=True)
    app.dependency_overrides[get_settings] = lambda: incomplete

    response = client.post("/api/v1/chat", json={"message": "Where has he worked?"})

    assert response.status_code == 503
    assert response.json() == {"detail": UNAVAILABLE_MESSAGE}


def test_ready_reports_incomplete_live_configuration(client: TestClient) -> None:
    incomplete = Settings(_env_file=None, enable_live_rag=True, enable_live_model_calls=True)
    app.dependency_overrides[get_settings] = lambda: incomplete

    body = client.get("/ready").json()

    assert body["status"] == "not_ready"
    assert body["checks"]["live_rag_configuration_complete"] is False
