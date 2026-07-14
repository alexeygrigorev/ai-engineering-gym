from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app import oidc
from app.main import app


def configure(monkeypatch):
    monkeypatch.setenv("AUTH_BASE_URL", "https://auth.example.test")
    monkeypatch.setenv("AUTH_CLIENT_ID", "gym-client")
    monkeypatch.setenv("AUTH_CALLBACK_URL", "https://gym.example.test/auth/callback")
    monkeypatch.setenv("AUTH_LOGOUT_URL", "https://gym.example.test/")
    monkeypatch.setenv("AUTH_ISSUER", "https://issuer.example.test/pool")
    monkeypatch.setenv("AUTH_JWKS_URL", "https://issuer.example.test/pool/.well-known/jwks.json")


def test_oidc_login_uses_pkce_and_verified_callback_creates_session(monkeypatch):
    configure(monkeypatch)
    client = TestClient(app)
    start = client.get("/login?return_to=/reviews", follow_redirects=False)
    assert start.status_code == 303
    authorize = urlparse(start.headers["location"])
    query = parse_qs(authorize.query)
    assert authorize.path == "/oauth2/authorize"
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    monkeypatch.setattr(oidc, "_exchange", lambda code, verifier: {"id_token": "signed-token"})
    monkeypatch.setattr(
        oidc,
        "_verify",
        lambda token: {
            "sub": "person-1",
            "email": "Person@DataTalks.Club",
            "email_verified": True,
            "nonce": query["nonce"][0],
        },
    )
    callback = client.get(
        f"/auth/callback?code=valid-code&state={query['state'][0]}",
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert callback.headers["location"] == "/reviews"
    assert client.get("/reviews").status_code == 200


def test_oidc_callback_rejects_invalid_state(monkeypatch):
    configure(monkeypatch)
    client = TestClient(app)
    client.get("/login", follow_redirects=False)
    response = client.get("/auth/callback?code=code&state=wrong")
    assert response.status_code == 400


def test_logout_clears_session_and_ends_cognito_session(monkeypatch):
    configure(monkeypatch)
    client = TestClient(app)
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    target = urlparse(response.headers["location"])
    assert target.path == "/logout"
    assert parse_qs(target.query) == {
        "client_id": ["gym-client"],
        "logout_uri": ["https://gym.example.test/"],
    }
