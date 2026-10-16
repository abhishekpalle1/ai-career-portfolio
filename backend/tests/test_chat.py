from fastapi.testclient import TestClient

from app.core.config import DEFAULT_MAX_INPUT_CHARACTERS


def test_chat_returns_full_contract(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "Where has Abhishek worked?"})
    assert response.status_code == 200

    body = response.json()
    assert set(body) == {
        "answer",
        "citations",
        "suggested_questions",
        "intent",
        "grounded",
        "abstained",
        "trace_id",
    }
    assert body["intent"] == "PROFESSIONAL_EXPERIENCE"
    assert body["abstained"] is False
    assert len(body["citations"]) >= 1


def test_chat_citation_fields_are_complete(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "Which technologies does he use?"})
    citation = response.json()["citations"][0]

    assert set(citation) == {
        "citation_id",
        "chunk_id",
        "source_id",
        "source_name",
        "source_type",
        "section",
        "experience_type",
        "source_url",
        "excerpt",
    }
    assert citation["source_url"].startswith(("/", "http://", "https://"))


def test_chat_is_deterministic_apart_from_trace_id(client: TestClient) -> None:
    payload = {"message": "What is his educational background?"}
    first = client.post("/api/v1/chat", json=payload).json()
    second = client.post("/api/v1/chat", json=payload).json()

    first.pop("trace_id")
    second.pop("trace_id")
    assert first == second


def test_chat_abstains_for_unknown_question(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "What is his favourite colour?"})
    body = response.json()

    assert body["abstained"] is True
    assert body["grounded"] is False
    assert body["citations"] == []


def test_chat_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_rejects_oversized_message(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat", json={"message": "a" * (DEFAULT_MAX_INPUT_CHARACTERS + 1)}
    )
    assert response.status_code == 422


def test_chat_accepts_message_at_the_limit(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "a" * DEFAULT_MAX_INPUT_CHARACTERS})
    assert response.status_code == 200


def test_chat_rejects_oversized_request_body(client: TestClient) -> None:
    oversized_body = b'{"message":"hello","padding":"' + b"x" * 20_000 + b'"}'
    response = client.post(
        "/api/v1/chat",
        content=oversized_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
