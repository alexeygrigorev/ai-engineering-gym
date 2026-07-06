"""Review + PWA smoke tests."""
from fastapi.testclient import TestClient
import app.main as main


def _client():
    c = TestClient(main.app)
    c.post("/login", data={"passphrase": "aislgym"})
    return c


def test_review_roundtrip():
    c = _client()
    r = c.post("/review/some-item", json={"verdict": "up", "comment": "keep this"})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert "keep this" in c.get("/reviews").text


def test_pwa_assets():
    c = _client()
    assert c.get("/manifest.webmanifest").status_code == 200
    assert c.get("/sw.js").status_code == 200
    assert c.get("/icon.svg").status_code == 200
    urls = c.get("/offline-urls").json()
    assert isinstance(urls, list) and "/" in urls and any(u.startswith("/stage/") for u in urls)
