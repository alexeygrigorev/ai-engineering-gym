"""Phone-first web UI + passphrase auth (design.md §9).

Navigation is organized by **interview stage** (mirrors the real interview loop
from the field guide's interview-process analysis). You open the app, see the
stages you'll actually face, tap one, and browse its questions. Each stage maps
to a content category and its flow type.

This is a thin server-rendered layer (HTML strings, no build step) so it packages
cleanly into a single Lambda. HTMX/Alpine interactivity comes later.
"""

from __future__ import annotations

import os
import html

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.store import Store

PASSPHRASE = os.environ.get("GYM_PASSPHRASE", "aislgym")
PUBLIC_PATHS = {"/login", "/health", "/favicon.ico"}

# Interview stages (field guide: interview/01-interview-process.md) → content category.
STAGES = [
    {"key": "recruiter", "title": "Recruiter Screen", "emoji": "📞",
     "blurb": "Openers, salary, why you're looking", "category": None, "flow": "coming soon"},
    {"key": "coding", "title": "Coding Round", "emoji": "💻",
     "blurb": "LeetCode-style + implementation", "category": "coding", "flow": "solve & reveal"},
    {"key": "theory", "title": "AI/ML Deep-Dive", "emoji": "🧠",
     "blurb": "LLMs, RAG, agents, evaluation", "category": "theory", "flow": "flashcards & quiz"},
    {"key": "system-design", "title": "System Design", "emoji": "🏗️",
     "blurb": "Design AI systems, tradeoffs", "category": "ai-system-design", "flow": "think-aloud walkthrough"},
    {"key": "project", "title": "Project Deep-Dive", "emoji": "📦",
     "blurb": "Your projects, under the microscope", "category": "project-deep-dive", "flow": "rehearsal"},
    {"key": "behavioral", "title": "Behavioral", "emoji": "🤝",
     "blurb": "STAR stories, values", "category": "behavioral", "flow": "rehearsal"},
    {"key": "take-home", "title": "Take-Home", "emoji": "🏠",
     "blurb": "Assignment prep & checklists", "category": "home-assignments", "flow": "reference"},
]
STAGE_BY_KEY = {s["key"]: s for s in STAGES}


# --- auth middleware -------------------------------------------------------


class AuthMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated browser traffic to /login (passphrase gate)."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)
        if request.session.get("auth"):
            return await call_next(request)
        if request.method == "GET":
            return RedirectResponse("/login", status_code=303)
        return HTMLResponse("unauthorized", status_code=401)


# --- rendering -------------------------------------------------------------

CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0f1115;color:#e7e9ee;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:640px;margin:0 auto;padding:20px 16px 64px}
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
h1{font-size:22px;margin:0}
.sub{color:#9aa1ad;font-size:13px}
a{color:inherit;text-decoration:none}
.tile{display:block;background:#171a21;border:1px solid #232733;border-radius:14px;padding:16px;margin:10px 0;transition:.15s}
.tile:active{transform:scale(.99)}
.tile .row{display:flex;align-items:center;gap:12px}
.tile .emoji{font-size:26px}
.tile .t{font-weight:600}
.tile .b{color:#9aa1ad;font-size:13px}
.badge{font-size:11px;color:#8fd6a9;border:1px solid #2c5a3d;border-radius:999px;padding:2px 8px}
.count{margin-left:auto;font-size:13px;color:#9aa1ad}
.pill{display:inline-block;font-size:11px;background:#232733;border-radius:999px;padding:2px 8px;color:#c3c8d2;margin-right:6px}
.q{background:#171a21;border:1px solid #232733;border-radius:12px;padding:14px;margin:10px 0}
.q .qt{font-weight:600;margin-bottom:6px}
pre{white-space:pre-wrap;background:#0b0d11;border:1px solid #232733;border-radius:10px;padding:12px;overflow-x:auto;font-size:13px}
.src a{color:#7aa2f7}
.back{color:#9aa1ad;font-size:14px;margin-bottom:12px;display:inline-block}
.streak{font-weight:700}
input[type=password]{width:100%;padding:14px;border-radius:12px;border:1px solid #232733;background:#0b0d11;color:#e7e9ee;font-size:16px}
button{width:100%;padding:14px;border-radius:12px;border:0;background:#3b6fe0;color:#fff;font-size:16px;font-weight:600;margin-top:12px}
.err{color:#ff8087;font-size:14px;margin-top:8px}
"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html><head><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1,maximum-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><div class=wrap>{body}</div></body></html>"
    )


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


# --- routes ----------------------------------------------------------------


def build_router(store: Store) -> APIRouter:
    r = APIRouter()

    def _items_for(category):
        return [i for i in store.list_items() if i.category == category]

    @r.get("/login", response_class=HTMLResponse)
    def login_get(request: Request, bad: int = 0):
        err = "<div class=err>Wrong passphrase</div>" if bad else ""
        body = (
            "<header><h1>AISL Gym</h1></header>"
            "<p class=sub>Interview prep, one rep at a time.</p>"
            "<form method=post action=/login>"
            "<input type=password name=passphrase placeholder=Passphrase autofocus>"
            f"<button>Enter</button>{err}</form>"
        )
        return page("Login · AISL Gym", body)

    @r.post("/login")
    def login_post(request: Request, passphrase: str = Form("")):
        if passphrase.strip() == PASSPHRASE:
            request.session["auth"] = True
            return RedirectResponse("/", status_code=303)
        return RedirectResponse("/login?bad=1", status_code=303)

    @r.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @r.get("/", response_class=HTMLResponse)
    def home(request: Request):
        user = store.get_user("me")
        xp = getattr(user, "xp", 0) if user else 0
        tiles = []
        for s in STAGES:
            n = len(_items_for(s["category"])) if s["category"] else 0
            count = f"{n} Q" if s["category"] else "soon"
            tiles.append(
                f"<a class=tile href='/stage/{s['key']}'><div class=row>"
                f"<div class=emoji>{s['emoji']}</div>"
                f"<div><div class=t>{esc(s['title'])}</div>"
                f"<div class=b>{esc(s['blurb'])}</div></div>"
                f"<div class=count>{count}</div></div></a>"
            )
        body = (
            "<header><h1>AISL Gym</h1>"
            f"<div class=streak>⭐ {xp} XP</div></header>"
            "<p class=sub>Pick an interview stage to train.</p>"
            + "".join(tiles)
            + "<p class=sub style='margin-top:20px'><a href=/logout>Log out</a></p>"
        )
        return page("AISL Gym", body)

    @r.get("/stage/{key}", response_class=HTMLResponse)
    def stage(request: Request, key: str):
        s = STAGE_BY_KEY.get(key)
        if not s:
            return page("Not found", "<a class=back href=/>&larr; Home</a><p>Unknown stage.</p>")
        items = _items_for(s["category"]) if s["category"] else []
        head = (
            "<a class=back href=/>&larr; Home</a>"
            f"<header><h1>{s['emoji']} {esc(s['title'])}</h1></header>"
            f"<p class=sub><span class=pill>{esc(s['flow'])}</span>{esc(s['blurb'])}</p>"
        )
        if not items:
            body = head + "<p class=sub>No questions yet — coming soon.</p>"
            return page(s["title"], body)
        rows = []
        for it in items:
            q = it.content.get("question") or it.content.get("scenario") or it.content.get("title") or it.id
            rows.append(
                f"<a class=q href='/item/{esc(it.id)}'><div class=qt>{esc(q)}</div>"
                f"<span class=pill>{esc(it.type)}</span>"
                f"<span class=pill>{esc(it.status)}</span></a>"
            )
        return page(s["title"], head + "".join(rows))

    @r.get("/item/{item_id}", response_class=HTMLResponse)
    def item(request: Request, item_id: str):
        it = store.get_item(item_id)
        if not it:
            return page("Not found", "<a class=back href=/>&larr; Home</a><p>Not found.</p>")
        c = it.content
        q = c.get("question") or c.get("scenario") or c.get("title") or it.id
        parts = [
            "<a class=back href='javascript:history.back()'>&larr; Back</a>",
            f"<header><h1>{esc(q)}</h1></header>",
            f"<p class=sub><span class=pill>{esc(it.type)}</span>"
            f"<span class=pill>{esc(it.skill)}</span>"
            f"<span class=pill>{esc(it.status)}</span></p>",
        ]
        ans = c.get("answer")
        if isinstance(ans, dict):
            if ans.get("short"):
                parts.append(f"<div class=q><div class=qt>Answer</div>{esc(ans['short'])}</div>")
            if ans.get("approach"):
                parts.append(f"<div class=q><div class=qt>Approach</div>{esc(ans['approach'])}</div>")
            if ans.get("pseudocode"):
                parts.append(f"<div class=qt>Pseudocode</div><pre>{esc(ans['pseudocode'])}</pre>")
            if ans.get("complexity"):
                parts.append(f"<p class=sub>Complexity: {esc(ans['complexity'])}</p>")
        for step in c.get("steps", []) or []:
            parts.append(
                f"<div class=q><div class=qt>{esc(step.get('phase',''))}: "
                f"{esc(step.get('prompt',''))}</div>{esc(step.get('reference',''))}</div>"
            )
        if c.get("diagram") or c.get("skeleton_diagram"):
            parts.append(f"<div class=qt>Diagram (mermaid)</div><pre>{esc(c.get('diagram') or c.get('skeleton_diagram'))}</pre>")
        for k in ("probes", "follow_ups", "rubric", "key_patterns"):
            vals = c.get(k)
            if vals:
                lis = "".join(f"<li>{esc(v)}</li>" for v in vals)
                parts.append(f"<div class=qt>{esc(k.replace('_',' ').title())}</div><ul>{lis}</ul>")
        srcs = c.get("sources") or c.get("synthesized_from")
        if srcs:
            links = "".join(
                f"<div class=src>&bull; <a href='{esc(x.get('url',''))}'>{esc(x.get('title',''))}</a></div>"
                for x in srcs if isinstance(x, dict)
            )
            parts.append(f"<div class=qt style='margin-top:14px'>Sources</div>{links}")
        return page(q, "".join(parts))

    return r
