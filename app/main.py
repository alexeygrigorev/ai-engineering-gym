"""FastAPI app + Lambda handler (design.md §8, §9).

Exposes:
- ``GET  /health``
- Session flow (design.md §2): start → next → submit, wired to the store.

Business logic (grading, real SRS scheduling, XP curves) is intentionally
stubbed — the shapes are right so real logic can slot in later. The ``handler``
export is the Mangum adapter for AWS Lambda + API Gateway.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from mangum import Mangum
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app.ingest import ingest_dir, load_items_bundle
from app.models import RehearsalAnswer, SessionResult, Session, User
from app.reviews import get_review_store
from app.store import InMemoryStore, Store
from app.web import AuthMiddleware, build_router

review_store = get_review_store()

DEFAULT_USER = "me"
SESSION_SIZE = 10  # design.md §2: ~7–15 exercises
XP_PER_ITEM = 10

# --- store + ingest bootstrap ---------------------------------------------
store: Store = InMemoryStore()
CONTENT_DIR = os.environ.get("CONTENT_DIR", "content")
CONTENT_BUNDLE = os.environ.get("CONTENT_BUNDLE", "content_bundle.json")
INCLUDE_DRAFTS = os.environ.get("INGEST_INCLUDE_DRAFTS", "").lower() in ("1", "true", "yes")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-insecure-secret-change-me")
SESSION_HTTPS_ONLY = os.environ.get("SESSION_HTTPS_ONLY", "").lower() in ("1", "true", "yes")


def bootstrap(content_dir: str = CONTENT_DIR) -> None:
    """Load content once and ensure the single default user exists.

    Fast path: a prebuilt ``content_bundle.json`` (made at deploy time) is loaded
    directly, avoiding a per-startup parse+validate of ~200 YAML files. Falls back
    to walking the YAML when there is no bundle (local dev / tests / custom dirs).
    """
    if content_dir == CONTENT_DIR and Path(CONTENT_BUNDLE).exists():
        load_items_bundle(CONTENT_BUNDLE, store)
    else:
        ingest_dir(content_dir, store, include_drafts=INCLUDE_DRAFTS)
    if store.get_user(DEFAULT_USER) is None:
        store.put_user(User(id=DEFAULT_USER))


app = FastAPI(title="AI Engineering Gym", version="0.1.0")

# Passphrase gate (design: simple auth). SessionMiddleware must wrap AuthMiddleware,
# so it is added last (outermost) to populate request.session first.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
    max_age=60 * 60 * 24 * 365,  # remember the login for a year (stable SESSION_SECRET)
)

# Phone-first web UI (interview-stage navigation).
app.include_router(build_router(store, review_store))

# Ingest ONCE per container at import time (not per-request via lifespan), so warm
# Lambda invocations don't re-parse content on every screen.
bootstrap()


# --- request/response shapes ----------------------------------------------


class StartSessionRequest(BaseModel):
    user_id: str = DEFAULT_USER
    skill: Optional[str] = None
    size: int = SESSION_SIZE


class SubmitRequest(BaseModel):
    """One exercise submission. Fields depend on the flow type; all optional."""

    grade: Optional[int] = None  # self-rate (recall/coding/rehearsal/walkthrough)
    correct: Optional[bool] = None  # mcq/order/fill auto-check
    answer_text: Optional[str] = None  # rehearsal captured answer / explain-it


class NextResponse(BaseModel):
    session_id: str
    done: bool
    index: int
    total: int
    item: Optional[dict] = None


# --- health ---------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "items": len(store.list_items()),
    }


# --- session flow ----------------------------------------------------------


@app.post("/session")
def start_session(req: StartSessionRequest) -> Session:
    """Start a session: pick a handful of items (optionally filtered by skill)."""
    if store.get_user(req.user_id) is None:
        store.put_user(User(id=req.user_id))

    items = store.list_items(skill=req.skill)
    if not items:
        raise HTTPException(status_code=404, detail="no approved items available")

    # Stub selection: first N. Real logic sorts by SRS due date.
    chosen = [i.id for i in items[: req.size]]
    session = Session(
        id=uuid.uuid4().hex,
        user_id=req.user_id,
        skill=req.skill,
        item_ids=chosen,
    )
    store.put_session(session)
    return session


@app.get("/session/{session_id}/next", response_model=NextResponse)
def next_exercise(session_id: str) -> NextResponse:
    """Return the item at the session cursor (or done)."""
    session = _require_session(session_id)
    total = len(session.item_ids)

    if session.cursor >= total:
        return NextResponse(session_id=session_id, done=True, index=session.cursor, total=total)

    item = store.get_item(session.item_ids[session.cursor])
    return NextResponse(
        session_id=session_id,
        done=False,
        index=session.cursor,
        total=total,
        item=item.model_dump(mode="json") if item else None,
    )


@app.post("/session/{session_id}/submit")
def submit_exercise(session_id: str, req: SubmitRequest) -> NextResponse:
    """Record a submission, advance the cursor, award stub XP.

    Real grading / SRS scheduling goes here; for now we store the raw result,
    capture rehearsal answers per-user, and bump XP.
    """
    session = _require_session(session_id)
    total = len(session.item_ids)
    if session.cursor >= total:
        raise HTTPException(status_code=409, detail="session already complete")

    item_id = session.item_ids[session.cursor]
    item = store.get_item(item_id)

    # Capture rehearsal answers per-user at runtime (design.md §4C, §7 `answers`).
    if item and item.type == "rehearsal" and req.answer_text:
        existing = store.get_answer(session.user_id, item_id)
        if existing is None:
            existing = RehearsalAnswer(
                user_id=session.user_id, item_id=item_id, text=req.answer_text
            )
        else:
            existing.text = req.answer_text
        if req.grade is not None:
            existing.grades.append(req.grade)
        store.put_answer(existing)

    session.results.append(
        SessionResult(item_id=item_id, grade=req.grade, correct=req.correct)
    )
    session.cursor += 1
    session.xp_earned += XP_PER_ITEM

    if session.cursor >= total:
        session.state = "completed"
        _award_session(session)

    store.put_session(session)

    return NextResponse(
        session_id=session_id,
        done=session.cursor >= total,
        index=session.cursor,
        total=total,
    )


# --- helpers ---------------------------------------------------------------


def _require_session(session_id: str) -> Session:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _award_session(session: Session) -> None:
    """Stub gamification: add XP to the user (streak logic deferred)."""
    user = store.get_user(session.user_id)
    if user is None:
        return
    user.xp += session.xp_earned
    store.put_user(user)


# --- Lambda handler (Mangum) ----------------------------------------------
# lifespan="off": content is ingested at import (above), so Mangum must NOT re-run
# ASGI startup on every invocation — doing so re-ingested content per request and
# made every screen slow.
_asgi_handler = Mangum(app, lifespan="off")


def handler(event, context=None):
    # EventBridge keep-warm pings return immediately without touching the ASGI app.
    if isinstance(event, dict) and event.get("warmup"):
        return {"ok": True, "warm": True}
    return _asgi_handler(event, context)
