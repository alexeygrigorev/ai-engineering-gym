"""Phone-first web UI + passphrase auth (design.md §9).

Navigation is organized by **interview stage** (mirrors the real interview loop from
the field guide). Each stage maps to a content category and its flow type.

The core interaction is **Anki-style active recall** (design.md §4): a card shows the
question only; you think, optionally reveal progressive hints, then reveal the answer
and self-rate (Again / Hard / Good / Easy), which feeds spaced repetition. A flat
"browse" view is available as study-mode.

Thin server-rendered layer (HTML strings + a little vanilla JS) so it packages into a
single Lambda. HTMX/Alpine can come later for richer interactions.
"""

from __future__ import annotations

import html
import json
import os
import uuid
from datetime import timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models import Progress, Session, SessionResult, _now
from app.store import Store

PASSPHRASE = os.environ.get("GYM_PASSPHRASE", "aislgym")
PUBLIC_PATHS = {"/login", "/health", "/favicon.ico"}
USER = "me"
PRACTICE_SIZE = 15
GRADES = {"again": 0, "hard": 1, "good": 2, "easy": 3}

# Interview stages (field guide: interview/01-interview-process.md) → content category.
STAGES = [
    {"key": "recruiter", "title": "Recruiter Screen", "emoji": "📞",
     "blurb": "Positioning, why you're looking, salary", "category": "recruiter", "flow": "rehearsal"},
    {"key": "coding", "title": "Coding Round", "emoji": "💻",
     "blurb": "ML coding, implementation, algorithms", "category": "coding", "flow": "solve & reveal"},
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


# --- styles ----------------------------------------------------------------

CSS = """
:root {
    color-scheme: dark;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0f1115;
    color: #e7e9ee;
    font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.wrap {
    max-width: 640px;
    margin: 0 auto;
    padding: 20px 16px 72px;
}

header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
}

h1 {
    font-size: 22px;
    margin: 0;
}

.sub {
    color: #9aa1ad;
    font-size: 13px;
}

a {
    color: inherit;
    text-decoration: none;
}

.back {
    display: inline-block;
    margin-bottom: 12px;
    color: #9aa1ad;
    font-size: 14px;
}

/* stage tiles */
.tile {
    display: block;
    background: #171a21;
    border: 1px solid #232733;
    border-radius: 14px;
    padding: 16px;
    margin: 10px 0;
    transition: transform 0.12s ease;
}

.tile:active {
    transform: scale(0.99);
}

.tile .row {
    display: flex;
    align-items: center;
    gap: 12px;
}

.tile .emoji {
    font-size: 26px;
}

.tile .t {
    font-weight: 600;
}

.tile .b {
    color: #9aa1ad;
    font-size: 13px;
}

.tile .count {
    margin-left: auto;
    font-size: 13px;
    color: #9aa1ad;
    text-align: right;
}

/* question rows in a stage list */
.q {
    display: block;
    background: #171a21;
    border: 1px solid #232733;
    border-radius: 12px;
    padding: 14px;
    margin: 10px 0;
}

.q .qt {
    font-weight: 600;
    margin-bottom: 8px;
}

/* pills and difficulty tags */
.pill {
    display: inline-block;
    font-size: 11px;
    background: #232733;
    border-radius: 999px;
    padding: 3px 9px;
    color: #c3c8d2;
    margin-right: 6px;
}

.tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    border-radius: 999px;
    padding: 3px 9px;
    margin-right: 6px;
}

.tag.easy {
    color: #8fd6a9;
    background: rgba(44, 90, 61, 0.35);
    border: 1px solid #2c5a3d;
}

.tag.medium {
    color: #e6c07a;
    background: rgba(90, 74, 30, 0.35);
    border: 1px solid #5a4a1e;
}

.tag.hard {
    color: #f0908f;
    background: rgba(90, 40, 40, 0.35);
    border: 1px solid #5a2828;
}

.section-label {
    color: #9aa1ad;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 18px 0 6px;
}

/* practice card */
.card {
    background: #171a21;
    border: 1px solid #232733;
    border-radius: 16px;
    padding: 20px;
    margin-top: 10px;
}

.tagrow {
    margin-bottom: 12px;
}

.question {
    font-size: 19px;
    font-weight: 600;
    line-height: 1.4;
}

.hint {
    background: #14202a;
    border: 1px solid #234a5a;
    border-radius: 10px;
    padding: 10px 12px;
    margin-top: 10px;
    font-size: 14px;
    color: #a9d6e5;
}

.actions {
    display: flex;
    gap: 10px;
    margin-top: 18px;
}

.answer {
    margin-top: 18px;
    border-top: 1px solid #232733;
    padding-top: 14px;
}

.answer .qt {
    font-weight: 600;
    margin: 12px 0 4px;
}

pre {
    white-space: pre-wrap;
    background: #0b0d11;
    border: 1px solid #232733;
    border-radius: 10px;
    padding: 12px;
    overflow-x: auto;
    font-size: 13px;
}

ul {
    margin: 6px 0;
    padding-left: 20px;
}

.src a {
    color: #7aa2f7;
}

.progress {
    height: 6px;
    background: #232733;
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 16px;
}

.progress > span {
    display: block;
    height: 100%;
    background: #3b6fe0;
}

/* buttons */
button {
    font: inherit;
    cursor: pointer;
    border: 0;
    border-radius: 12px;
    padding: 13px 16px;
    font-weight: 600;
}

button.primary {
    background: #3b6fe0;
    color: #fff;
    flex: 1;
}

button.ghost {
    background: #232733;
    color: #e7e9ee;
}

button:disabled {
    opacity: 0.4;
    cursor: default;
}

.rating {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 18px;
}

.rating button {
    padding: 14px 4px;
}

.rating .again { background: #4a2530; color: #f0908f; }
.rating .hard  { background: #4a3a20; color: #e6c07a; }
.rating .good  { background: #234a30; color: #8fd6a9; }
.rating .easy  { background: #23324a; color: #9ec1ff; }

/* login */
input[type=password] {
    width: 100%;
    padding: 14px;
    border-radius: 12px;
    border: 1px solid #232733;
    background: #0b0d11;
    color: #e7e9ee;
    font-size: 16px;
}

form.login button {
    width: 100%;
    background: #3b6fe0;
    color: #fff;
    margin-top: 12px;
}

.err {
    color: #ff8087;
    font-size: 14px;
    margin-top: 8px;
}

.cta {
    display: block;
    text-align: center;
    background: #3b6fe0;
    color: #fff;
    font-weight: 600;
    border-radius: 12px;
    padding: 14px;
    margin: 6px 0 14px;
}
"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1,maximum-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><div class=wrap>{body}</div></body></html>"
    )


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def difficulty_tag(item) -> str:
    d = (item.difficulty or "medium").lower()
    return f'<span class="tag {esc(d)}">{esc(d)}</span>'


def display_question(content: dict, fallback: str) -> str:
    return content.get("question") or content.get("scenario") or content.get("title") or fallback


# --- answer / sources rendering (shared by browse + card reveal) -----------


def render_answer(content: dict) -> str:
    parts: list[str] = []
    ans = content.get("answer")
    if isinstance(ans, dict):
        if ans.get("short"):
            parts.append(f'<div class="qt">Answer</div><div>{esc(ans["short"])}</div>')
        if ans.get("approach"):
            parts.append(f'<div class="qt">Approach</div><div>{esc(ans["approach"])}</div>')
        if ans.get("design_approach"):
            parts.append(f'<div class="qt">Design approach</div><div>{esc(ans["design_approach"])}</div>')
        if ans.get("pseudocode"):
            parts.append(f'<div class="qt">Pseudocode</div><pre>{esc(ans["pseudocode"])}</pre>')
        if ans.get("complexity"):
            parts.append(f'<p class="sub">Complexity: {esc(ans["complexity"])}</p>')
        if ans.get("key_points"):
            lis = "".join(f"<li>{esc(v)}</li>" for v in ans["key_points"])
            parts.append(f'<div class="qt">Key points</div><ul>{lis}</ul>')
        if ans.get("extension_points"):
            lis = "".join(f"<li>{esc(_flat(v))}</li>" for v in ans["extension_points"])
            parts.append(f'<div class="qt">Extension points</div><ul>{lis}</ul>')
    for step in content.get("steps", []) or []:
        parts.append(
            f'<div class="qt">{esc(step.get("phase", ""))}: {esc(step.get("prompt", ""))}</div>'
            f'<div>{esc(step.get("reference", ""))}</div>'
        )
    if content.get("diagram") or content.get("skeleton_diagram"):
        parts.append(
            '<div class="qt">Diagram (mermaid)</div>'
            f'<pre>{esc(content.get("diagram") or content.get("skeleton_diagram"))}</pre>'
        )
    if content.get("example_structure"):
        parts.append(f'<div class="qt">Model structure</div><pre>{esc(content["example_structure"])}</pre>')
    for key in ("probes", "follow_ups", "rubric", "key_patterns", "extension_points"):
        vals = content.get(key)
        if vals:
            lis = "".join(f"<li>{esc(v)}</li>" for v in vals)
            parts.append(f'<div class="qt">{esc(key.replace("_", " ").title())}</div><ul>{lis}</ul>')
    return "".join(parts)


def render_sources(content: dict) -> str:
    srcs = content.get("sources") or content.get("synthesized_from")
    if not srcs:
        return ""
    rows = []
    for x in srcs:
        if not isinstance(x, dict):
            continue
        title = esc(x.get("title", ""))
        url = esc(x.get("url", ""))
        link = f'<a href="{url}">{title}</a>' if url else title
        rows.append(f'<div class="src">&bull; {link}</div>')
    return "".join(rows)


# --- routes ----------------------------------------------------------------


def build_router(store: Store) -> APIRouter:
    r = APIRouter()

    def items_for(category):
        return [i for i in store.list_items() if i.category == category]

    def practice_order(items):
        """AI-relevant coding first, then unseen, then earliest due (simple SRS ordering)."""
        def key(i):
            rel = 0 if i.content.get("ai_relevant") is True else 1
            p = store.get_progress(USER, i.id)
            if p is None or p.due is None:
                return (rel, 0, 0.0)  # unseen first within its relevance band
            return (rel, 1, p.due.timestamp())
        return sorted(items, key=key)

    # -- auth --
    @r.get("/login", response_class=HTMLResponse)
    def login_get(request: Request, bad: int = 0):
        err = '<div class="err">Wrong passphrase</div>' if bad else ""
        body = (
            "<header><h1>AISL Gym</h1></header>"
            '<p class="sub">Interview prep, one rep at a time.</p>'
            '<form method="post" action="/login" class="login">'
            '<input type="password" name="passphrase" placeholder="Passphrase" autofocus>'
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

    # -- home --
    @r.get("/", response_class=HTMLResponse)
    def home(request: Request):
        user = store.get_user(USER)
        xp = getattr(user, "xp", 0) if user else 0
        tiles = []
        for s in STAGES:
            items = items_for(s["category"])
            if s["category"] == "coding":
                rel = sum(1 for i in items if i.content.get("ai_relevant") is True)
                count = f"{rel} relevant<br>{len(items)} total" if items else "soon"
            else:
                count = f"{len(items)} Q" if items else "soon"
            tiles.append(
                f'<a class="tile" href="/stage/{s["key"]}"><div class="row">'
                f'<div class="emoji">{s["emoji"]}</div>'
                f'<div><div class="t">{esc(s["title"])}</div>'
                f'<div class="b">{esc(s["blurb"])}</div></div>'
                f'<div class="count">{count}</div></div></a>'
            )
        body = (
            f'<header><h1>AISL Gym</h1><div class="pill">⭐ {xp} XP</div></header>'
            '<p class="sub">Pick an interview stage to train.</p>'
            + "".join(tiles)
            + '<p class="sub" style="margin-top:20px"><a href="/logout">Log out</a></p>'
        )
        return page("AISL Gym", body)

    # -- stage list (browse) --
    @r.get("/stage/{key}", response_class=HTMLResponse)
    def stage(request: Request, key: str):
        s = STAGE_BY_KEY.get(key)
        if not s:
            return page("Not found", '<a class="back" href="/">&larr; Home</a><p>Unknown stage.</p>')
        items = items_for(s["category"])
        head = (
            '<a class="back" href="/">&larr; Home</a>'
            f'<header><h1>{s["emoji"]} {esc(s["title"])}</h1></header>'
            f'<p class="sub"><span class="pill">{esc(s["flow"])}</span>{esc(s["blurb"])}</p>'
        )
        if not items:
            return page(s["title"], head + '<p class="sub">No questions yet — coming soon.</p>')

        practice_btn = f'<a class="cta" href="/practice/{key}">Start practice ({min(len(items), PRACTICE_SIZE)} cards)</a>'

        def row(it):
            q = display_question(it.content, it.id)
            return (
                f'<a class="q" href="/item/{esc(it.id)}"><div class="qt">{esc(q)}</div>'
                f"{difficulty_tag(it)}<span class=\"pill\">{esc(it.type)}</span></a>"
            )

        # coding: split AI-relevant vs the rest
        if s["category"] == "coding":
            relevant = [i for i in items if i.content.get("ai_relevant") is True]
            rest = [i for i in items if i.content.get("ai_relevant") is not True]
            body = head + practice_btn
            if relevant:
                body += '<div class="section-label">AI-engineering relevant</div>' + "".join(row(i) for i in relevant)
            if rest:
                body += f'<div class="section-label">General DSA ({len(rest)})</div>' + "".join(row(i) for i in rest)
            return page(s["title"], body)

        return page(s["title"], head + practice_btn + "".join(row(i) for i in items))

    # -- browse a single item (study mode) --
    @r.get("/item/{item_id}", response_class=HTMLResponse)
    def item(request: Request, item_id: str):
        it = store.get_item(item_id)
        if not it:
            return page("Not found", '<a class="back" href="/">&larr; Home</a><p>Not found.</p>')
        c = it.content
        q = display_question(c, it.id)
        sources = render_sources(c)
        sources_block = (
            '<button class="ghost" onclick="toggleSources()">Sources</button>'
            f'<div id="sources" style="display:none;margin-top:10px">{sources}</div>'
            '<script>function toggleSources(){var s=document.getElementById("sources");'
            's.style.display=s.style.display==="none"?"block":"none";}</script>'
            if sources else ""
        )
        body = (
            '<a class="back" href="javascript:history.back()">&larr; Back</a>'
            f'<div class="tagrow">{difficulty_tag(it)}<span class="pill">{esc(it.type)}</span>'
            f'<span class="pill">{esc(it.skill)}</span></div>'
            f'<div class="question">{esc(q)}</div>'
            f'<div class="answer">{render_answer(c)}{sources_block}</div>'
        )
        return page(q, body)

    # -- practice: start a session --
    @r.get("/practice/{key}")
    def practice_start(request: Request, key: str):
        s = STAGE_BY_KEY.get(key)
        if not s:
            return RedirectResponse("/", status_code=303)
        items = practice_order(items_for(s["category"]))[:PRACTICE_SIZE]
        if not items:
            return RedirectResponse(f"/stage/{key}", status_code=303)
        session = Session(
            id=uuid.uuid4().hex,
            user_id=USER,
            skill=s["category"],
            item_ids=[i.id for i in items],
        )
        store.put_session(session)
        return RedirectResponse(f"/practice/s/{session.id}", status_code=303)

    # -- practice: render the current card --
    @r.get("/practice/s/{sid}", response_class=HTMLResponse)
    def practice_card(request: Request, sid: str):
        session = store.get_session(sid)
        if session is None:
            return RedirectResponse("/", status_code=303)
        total = len(session.item_ids)
        if session.cursor >= total:
            return RedirectResponse(f"/practice/s/{sid}/done", status_code=303)

        it = store.get_item(session.item_ids[session.cursor])
        c = it.content
        q = display_question(c, it.id)
        hints = c.get("hints") or []
        sources = render_sources(c)
        pct = int(session.cursor / total * 100)

        sources_block = (
            '<button class="ghost" type="button" onclick="toggleSources()">Sources</button>'
            f'<div id="sources" style="display:none;margin-top:10px">{sources}</div>'
            if sources else ""
        )

        body = f"""
<a class="back" href="/stage/{esc(session.skill)}">&larr; Exit</a>
<div class="progress"><span style="width:{pct}%"></span></div>
<div class="card">
  <div class="tagrow">{difficulty_tag(it)}<span class="pill">{esc(it.skill)}</span>
    <span class="pill">{esc(session.cursor + 1)}/{esc(total)}</span></div>
  <div class="question">{esc(q)}</div>
  <div id="hints"></div>
  <div class="actions">
    <button class="ghost" type="button" id="hintbtn" onclick="hint()">Hint</button>
    <button class="primary" type="button" onclick="reveal()">Reveal answer</button>
  </div>
  <div id="answer" class="answer" style="display:none">
    {render_answer(c)}
    {sources_block}
    <form method="post" action="/practice/s/{esc(sid)}/rate" class="rating">
      <button class="again" name="grade" value="again">Again</button>
      <button class="hard" name="grade" value="hard">Hard</button>
      <button class="good" name="grade" value="good">Good</button>
      <button class="easy" name="grade" value="easy">Easy</button>
    </form>
  </div>
</div>
<script>
const HINTS = {json.dumps(hints)};
let hi = 0;
function hint() {{
    if (hi < HINTS.length) {{
        const d = document.createElement('div');
        d.className = 'hint';
        d.textContent = '💡 ' + HINTS[hi];
        document.getElementById('hints').appendChild(d);
        hi++;
        if (hi >= HINTS.length) document.getElementById('hintbtn').disabled = true;
    }}
}}
if (HINTS.length === 0) document.getElementById('hintbtn').disabled = true;
function reveal() {{ document.getElementById('answer').style.display = 'block'; }}
function toggleSources() {{
    const s = document.getElementById('sources');
    s.style.display = s.style.display === 'none' ? 'block' : 'none';
}}
</script>
"""
        return page(q, body)

    # -- practice: rate current card, advance --
    @r.post("/practice/s/{sid}/rate")
    def practice_rate(request: Request, sid: str, grade: str = Form("good")):
        session = store.get_session(sid)
        if session is None:
            return RedirectResponse("/", status_code=303)
        total = len(session.item_ids)
        if session.cursor < total:
            item_id = session.item_ids[session.cursor]
            q = GRADES.get(grade, 2)
            prog = store.get_progress(USER, item_id) or Progress(user_id=USER, item_id=item_id)
            prog.reps += 1
            prog.last_grade = q
            if q == 0:
                prog.interval = 0
                prog.ease = max(1.3, prog.ease - 0.2)
            else:
                prog.interval = 1 if prog.interval == 0 else max(1, round(prog.interval * prog.ease))
                if q >= 3:
                    prog.ease = min(3.0, prog.ease + 0.1)
            prog.due = _now() + timedelta(days=prog.interval)
            store.put_progress(prog)
            session.results.append(SessionResult(item_id=item_id, grade=q))
            session.cursor += 1
            session.xp_earned += 10
            store.put_session(session)
        if session.cursor >= total:
            return RedirectResponse(f"/practice/s/{sid}/done", status_code=303)
        return RedirectResponse(f"/practice/s/{sid}", status_code=303)

    # -- practice: summary --
    @r.get("/practice/s/{sid}/done", response_class=HTMLResponse)
    def practice_done(request: Request, sid: str):
        session = store.get_session(sid)
        if session is None:
            return RedirectResponse("/", status_code=303)
        session.state = "completed"
        store.put_session(session)
        user = store.get_user(USER)
        if user:
            user.xp += session.xp_earned
            store.put_user(user)
        n = len(session.results)
        good = sum(1 for x in session.results if (x.grade or 0) >= 2)
        body = (
            '<header><h1>Session complete 🎉</h1></header>'
            f'<div class="card"><div class="question">+{session.xp_earned} XP</div>'
            f'<p class="sub">{good}/{n} cards rated Good or better.</p></div>'
            f'<a class="cta" href="/practice/{esc(session.skill)}">Practice again</a>'
            '<p class="sub"><a href="/">&larr; Home</a></p>'
        )
        return page("Done", body)

    return r
