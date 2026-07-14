"""Cognito authorization-code/PKCE adapter for the browser session."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import urllib.parse
import urllib.request

import jwt
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse


def _config() -> dict[str, str]:
    issuer = os.environ.get("AUTH_ISSUER", "").rstrip("/")
    return {
        "base_url": os.environ.get("AUTH_BASE_URL", "").rstrip("/"),
        "client_id": os.environ.get("AUTH_CLIENT_ID", ""),
        "callback_url": os.environ.get("AUTH_CALLBACK_URL", ""),
        "logout_url": os.environ.get("AUTH_LOGOUT_URL", ""),
        "issuer": issuer,
        "jwks_url": os.environ.get("AUTH_JWKS_URL", f"{issuer}/.well-known/jwks.json" if issuer else ""),
    }


def configured() -> bool:
    config = _config()
    return all(config[key] for key in ("base_url", "client_id", "callback_url", "issuer", "jwks_url"))


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _safe_return_to(value: str | None) -> str:
    return value if value and value.startswith("/") and not value.startswith("//") else "/"


def begin(request: Request):
    config = _config()
    if not configured():
        return HTMLResponse("Shared authentication is not configured", status_code=503)
    state = _b64url(secrets.token_bytes(32))
    verifier = _b64url(secrets.token_bytes(48))
    nonce = _b64url(secrets.token_bytes(32))
    request.session["oidc"] = {
        "state": state,
        "verifier": verifier,
        "nonce": nonce,
        "return_to": _safe_return_to(request.query_params.get("return_to")),
    }
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": config["client_id"],
            "redirect_uri": config["callback_url"],
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
            "code_challenge_method": "S256",
        }
    )
    return RedirectResponse(f'{config["base_url"]}/oauth2/authorize?{query}', status_code=303)


def _exchange(code: str, verifier: str) -> dict:
    config = _config()
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "code": code,
            "redirect_uri": config["callback_url"],
            "code_verifier": verifier,
        }
    ).encode()
    request = urllib.request.Request(
        f'{config["base_url"]}/oauth2/token',
        data=body,
        headers={"content-type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def _verify(id_token: str) -> dict:
    config = _config()
    key = jwt.PyJWKClient(config["jwks_url"]).get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        key.key,
        algorithms=["RS256"],
        audience=config["client_id"],
        issuer=config["issuer"],
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )


def finish(request: Request):
    pending = request.session.pop("oidc", None)
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    if not pending or not code or not hmac.compare_digest(state, str(pending.get("state", ""))):
        return HTMLResponse("Invalid or expired login state", status_code=400)
    try:
        tokens = _exchange(code, pending["verifier"])
        claims = _verify(tokens["id_token"])
    except Exception:
        return HTMLResponse("Login verification failed", status_code=401)
    if not hmac.compare_digest(str(claims.get("nonce", "")), str(pending.get("nonce", ""))):
        return HTMLResponse("Identity token nonce mismatch", status_code=401)
    email = claims.get("email")
    if not isinstance(email, str) or claims.get("email_verified") is not True:
        return HTMLResponse("A verified email address is required", status_code=401)
    request.session.update({"auth": True, "email": email.lower(), "subject": claims["sub"]})
    return RedirectResponse(_safe_return_to(pending.get("return_to")), status_code=303)


def logout_url() -> str:
    config = _config()
    if not config["base_url"] or not config["client_id"] or not config["logout_url"]:
        return "/login"
    query = urllib.parse.urlencode({"client_id": config["client_id"], "logout_uri": config["logout_url"]})
    return f'{config["base_url"]}/logout?{query}'
