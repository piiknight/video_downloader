import os

os.environ["API_KEY"] = "test-key"
os.environ["COBALT_URL"] = "http://localhost:9000"

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def headers():
    return {"X-API-Key": "test-key"}


async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_extract_missing_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/extract", json={"url": "https://tiktok.com/video/123"})
    assert resp.status_code == 401


async def test_extract_invalid_url(headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/extract", json={"url": "https://evil.com/hack"}, headers=headers)
    assert resp.status_code == 400


async def test_extract_http_rejected(headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/extract", json={"url": "http://tiktok.com/video/123"}, headers=headers)
    assert resp.status_code == 400


async def test_extract_success(headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/extract",
            json={"url": "https://www.tiktok.com/@user/video/123"},
            headers=headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "formats" in data
    assert len(data["formats"]) > 0


async def test_download_not_found(headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/download/nonexistent?format=720", headers=headers)
    assert resp.status_code == 404
