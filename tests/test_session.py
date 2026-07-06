"""Session flow smoke test: start → next → submit (design.md §2)."""

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main

FIXTURES = Path(__file__).parent / "fixtures"


def _client(auth: bool = True) -> TestClient:
    # rebuild the module store from fixtures so tests are isolated
    main.store = main.InMemoryStore()
    main.bootstrap(str(FIXTURES))
    client = TestClient(main.app, raise_server_exceptions=True)
    if auth:
        # session API is behind the passphrase gate; log in to get the cookie
        client.post("/login", data={"passphrase": "aislgym"})
    return client


def test_health():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["items"] == 5


def test_full_session_run():
    client = _client()

    start = client.post("/session", json={"skill": "rag"})
    assert start.status_code == 200
    session = start.json()
    assert session["state"] == "active"
    assert len(session["item_ids"]) >= 1
    sid = session["id"]

    # next returns the current item
    nxt = client.get(f"/session/{sid}/next")
    assert nxt.status_code == 200
    assert nxt.json()["done"] is False
    assert nxt.json()["item"]["type"] == "knowledge"

    # submit through the whole session
    total = nxt.json()["total"]
    for _ in range(total):
        resp = client.post(f"/session/{sid}/submit", json={"correct": True, "grade": 4})
        assert resp.status_code == 200

    done = client.get(f"/session/{sid}/next")
    assert done.json()["done"] is True
