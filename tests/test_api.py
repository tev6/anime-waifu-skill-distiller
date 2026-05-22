import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app

TRAITS_JSON = json.dumps({
    "name": "TestChar",
    "core_personality": "tsundere, cold outside but caring inside",
    "speech_style": "uses ~ at end of sentences",
    "catchphrases": ["baka", "hmph"],
    "emotional_patterns": "blushes when praised, gets angry at bugs",
    "coding_attitude": "perfectionist, treats code like cleaning",
    "visual_brief": "short blue hair, maid outfit",
})

SKILL_MD = """---
name: testchar-coding-companion
description: tsundere coding assistant
---

## Skill: testchar-coding-companion

Test skill content."""

PREVIEW_TEXT = "User: Help me fix this bug\nAssistant: Hmph, you can't even fix that? Fine, let me show you."


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_llm():
    with patch("services.llm._call_llm") as mock:
        mock.side_effect = [TRAITS_JSON, SKILL_MD, PREVIEW_TEXT]
        yield mock


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_generate_returns_skill_and_traits(client, mock_llm):
    resp = await client.post("/api/generate", json={
        "corpus": "test corpus",
        "intensity": "full",
        "provider": "anthropic",
        "api_key": "test-key",
        "model": "test-model",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["skill_md"] == SKILL_MD
    assert data["trait"]["name"] == "TestChar"
    assert data["preview"] == PREVIEW_TEXT
    assert mock_llm.call_count == 3


@pytest.mark.anyio
async def test_generate_missing_corpus(client):
    resp = await client.post("/api/generate", json={
        "corpus": "",
        "provider": "anthropic",
        "api_key": "test-key",
    })

    assert resp.status_code == 400
    assert resp.json()["detail"] == "corpus is required"


@pytest.mark.anyio
async def test_generate_oversized_body(client):
    resp = await client.post("/api/generate", headers={
        "content-length": "200000",
    })

    assert resp.status_code == 413


@pytest.mark.anyio
async def test_chat_missing_skill_md(client):
    resp = await client.post("/api/chat", json={
        "skill_md": "",
        "message": "hello",
        "provider": "anthropic",
        "api_key": "test-key",
    })

    assert resp.status_code == 400
    assert "skill_md" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_chat_missing_message(client):
    resp = await client.post("/api/chat", json={
        "skill_md": "test skill",
        "message": "",
        "provider": "anthropic",
        "api_key": "test-key",
    })

    assert resp.status_code == 400
    assert "message" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_install_writes_skill_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr("main.SKILLS_DIR", tmp_path)

    resp = await client.post("/api/install", json={
        "skill_md": "---\nname: mychar\n---\n\n## Skill: mychar",
        "scope": "project",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "mychar"
    assert data["scope"] == "project"

    installed = tmp_path / "mychar.md"
    assert installed.exists()
    assert "mychar" in installed.read_text(encoding="utf-8")
