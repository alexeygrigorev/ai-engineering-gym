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
import random
import uuid
from datetime import timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from app.models import Progress, Session, SessionResult, _now
from app.store import Store


class ReviewIn(BaseModel):
    verdict: str = ""
    comment: str = ""

PASSPHRASE = os.environ.get("GYM_PASSPHRASE", "aislgym")
PUBLIC_PATHS = {"/login", "/health", "/favicon.ico", "/manifest.webmanifest", "/sw.js", "/icon.svg"}
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

.cta.secondary {
    background: #232733;
    color: #e7e9ee;
}

/* content review controls */
.review {
    margin-top: 16px;
    border-top: 1px solid #232733;
    padding-top: 14px;
}

.rev-btns {
    display: flex;
    gap: 8px;
    margin: 8px 0;
}

.revbtn {
    flex: 1;
    background: #232733;
    color: #e7e9ee;
}

.revbtn.up.sel {
    background: #234a30;
    color: #8fd6a9;
}

.revbtn.down.sel {
    background: #4a2530;
    color: #f0908f;
}

.cmt {
    width: 100%;
    min-height: 64px;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid #232733;
    background: #0b0d11;
    color: #e7e9ee;
    font: inherit;
    resize: vertical;
}

.rev-status {
    font-size: 13px;
    color: #8fd6a9;
    margin-top: 6px;
    min-height: 16px;
}
"""


GLOBAL_JS = """
<script>
// content review (thumbs up/down + comment), offline-queued
function review(id, verdict){
  const box=document.querySelector('.review[data-id="'+CSS.escape(id)+'"]');
  if(!box) return;
  if(verdict){ box.dataset.verdict=verdict;
    box.querySelectorAll('.revbtn').forEach(b=>b.classList.remove('sel'));
    const b=box.querySelector('.revbtn.'+verdict); if(b) b.classList.add('sel'); }
  const ta=document.getElementById('cmt-'+id);
  sendReview(id, box.dataset.verdict||'', ta?ta.value:'');
}
async function sendReview(id, verdict, comment){
  const st=document.getElementById('revst-'+id);
  try{
    if(!navigator.onLine) throw 0;
    const r=await fetch('/review/'+encodeURIComponent(id),{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({verdict,comment})});
    if(!r.ok) throw 0;
    if(st) st.textContent='Saved \\u2713';
  }catch(e){ queueReview(id,{verdict,comment}); if(st) st.textContent='Saved offline \\u2014 will sync'; }
}
function queueReview(id,p){ const q=JSON.parse(localStorage.getItem('reviewQueue')||'{}');
  q[id]=p; localStorage.setItem('reviewQueue',JSON.stringify(q)); }
async function flushReviews(){ if(!navigator.onLine) return;
  const q=JSON.parse(localStorage.getItem('reviewQueue')||'{}'); let ch=false;
  for(const [id,p] of Object.entries(q)){ try{
    const r=await fetch('/review/'+encodeURIComponent(id),{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});
    if(r.ok){ delete q[id]; ch=true; } }catch(e){} }
  if(ch) localStorage.setItem('reviewQueue',JSON.stringify(q)); }
window.addEventListener('online',flushReviews); window.addEventListener('load',flushReviews);
// PWA service worker
if('serviceWorker' in navigator){ navigator.serviceWorker.register('/sw.js').catch(()=>{}); }
// download all cards for offline use
async function downloadOffline(){
  const btn=document.getElementById('dlbtn'); if(btn) btn.textContent='Downloading\\u2026';
  try{
    const urls=await (await fetch('/offline-urls')).json();
    const reg=await navigator.serviceWorker.ready;
    reg.active.postMessage({type:'precache', urls});
    if(btn) btn.textContent='Downloaded '+urls.length+' cards \\u2713';
  }catch(e){ if(btn) btn.textContent='Download failed'; }
}
</script>
"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1,maximum-scale=1'>"
        "<meta name=theme-color content='#0f1115'>"
        "<link rel=manifest href='/manifest.webmanifest'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><div class=wrap>{body}</div>{GLOBAL_JS}</body></html>"
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


def recall_block(it, footer: str = "") -> str:
    """Anki recall card: question only, progressive hints, then reveal answer + sources.

    Shared by the single-item browse view and the practice session. ``footer`` is
    extra HTML (e.g. the rating form) shown inside the revealed answer.
    """
    c = it.content
    q = display_question(c, it.id)
    hints = c.get("hints") or []
    sources = render_sources(c)
    sources_block = (
        '<button class="ghost" type="button" onclick="toggleSources()">Sources</button>'
        f'<div id="sources" style="display:none;margin-top:10px">{sources}</div>'
        if sources else ""
    )
    return f"""
<div class="tagrow">{difficulty_tag(it)}<span class="pill">{esc(it.skill)}</span></div>
<div class="question">{esc(q)}</div>
<div id="hints"></div>
<div class="actions">
  <button class="ghost" type="button" id="hintbtn" onclick="hint()">Hint</button>
  <button class="primary" type="button" onclick="reveal()">Reveal answer</button>
</div>
<div id="answer" class="answer" style="display:none">
  {render_answer(c)}
  {sources_block}
  {footer}
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


def review_controls(item_id: str, current) -> str:
    """Thumbs up/down + comment controls, shown after the answer is revealed."""
    cur = current or {}
    v = cur.get("verdict", "")
    comment = esc(cur.get("comment", ""))
    up = " sel" if v == "up" else ""
    down = " sel" if v == "down" else ""
    iid = esc(item_id)
    return (
        f'<div class="review" data-id="{iid}" data-verdict="{esc(v)}">'
        '<div class="qt">Review this card</div>'
        '<div class="rev-btns">'
        f"<button type=\"button\" class=\"revbtn up{up}\" onclick=\"review('{iid}','up')\">👍 Keep</button>"
        f"<button type=\"button\" class=\"revbtn down{down}\" onclick=\"review('{iid}','down')\">👎 Cut</button>"
        "</div>"
        f'<textarea id="cmt-{iid}" class="cmt" placeholder="Comment (optional)">{comment}</textarea>'
        f"<button type=\"button\" class=\"ghost\" onclick=\"review('{iid}',null)\">Save comment</button>"
        f'<div class="rev-status" id="revst-{iid}"></div>'
        "</div>"
    )


SERVICE_WORKER_JS = """
const CACHE = 'gym-v1';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  e.respondWith((async () => {
    try {
      const res = await fetch(req);
      if (res && res.ok) { const c = await caches.open(CACHE); c.put(req, res.clone()); }
      return res;
    } catch (err) {
      const cached = await caches.match(req);
      if (cached) return cached;
      const home = await caches.match('/');
      return home || new Response('offline', {status: 503, headers: {'Content-Type': 'text/plain'}});
    }
  })());
});
self.addEventListener('message', async e => {
  if (e.data && e.data.type === 'precache') {
    const c = await caches.open(CACHE);
    await Promise.all((e.data.urls || []).map(u =>
      fetch(u, {credentials: 'same-origin'}).then(r => { if (r.ok) c.put(u, r.clone()); }).catch(() => {})
    ));
    if (e.source && e.source.postMessage) e.source.postMessage({type: 'precache-done'});
  }
});
"""


# --- routes ----------------------------------------------------------------


def build_router(store: Store, reviews) -> APIRouter:
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
            + '<button id="dlbtn" class="cta secondary" style="width:100%;margin-top:16px" '
            'onclick="downloadOffline()">⬇ Download for offline</button>'
            '<p class="sub" style="margin-top:16px">'
            '<a href="/reviews">My reviews</a> &middot; <a href="/logout">Log out</a></p>'
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

        def row(it):
            q = display_question(it.content, it.id)
            return (
                f'<a class="q" href="/item/{esc(it.id)}"><div class="qt">{esc(q)}</div>'
                f"{difficulty_tag(it)}<span class=\"pill\">{esc(it.type)}</span></a>"
            )

        def practice_buttons(link_base, n):
            return (
                f'<a class="cta" href="{link_base}&mode=random">🎲 Random question</a>'
                if "?" in link_base
                else f'<a class="cta" href="{link_base}?mode=random">🎲 Random question</a>'
            ) + (
                f'<a class="cta secondary" href="{link_base}">Practice due cards ({n})</a>'
            )

        # coding: drill into a sub-type (ML Coding / Implementation / Algorithms)
        if s["category"] == "coding":
            groups = [
                ("ml-coding", "ML Coding", "💡", "Implement ML/AI primitives in NumPy"),
                ("implementation", "Implementation Rounds", "🔧", "Progressive build &amp; extend systems"),
                ("algorithms", "Algorithms &amp; DSA", "🧩", "LeetCode-style problem solving"),
            ]
            sub = request.query_params.get("sub")
            if not sub:
                tiles = []
                for gskill, gname, gemoji, gblurb in groups:
                    n = len([i for i in items if i.skill == gskill])
                    if not n:
                        continue
                    tiles.append(
                        f'<a class="tile" href="/stage/coding?sub={gskill}"><div class="row">'
                        f'<div class="emoji">{gemoji}</div>'
                        f'<div><div class="t">{gname}</div><div class="b">{gblurb}</div></div>'
                        f'<div class="count">{n} Q</div></div></a>'
                    )
                return page(s["title"], head + '<p class="sub">Pick a coding type.</p>' + "".join(tiles))

            g = next((x for x in groups if x[0] == sub), None)
            if not g:
                return RedirectResponse("/stage/coding", status_code=303)
            gskill, gname, gemoji, gblurb = g
            gitems = practice_order([i for i in items if i.skill == gskill])
            body = (
                '<a class="back" href="/stage/coding">&larr; Coding</a>'
                f"<header><h1>{gemoji} {gname}</h1></header>"
                f'<p class="sub">{gblurb}</p>'
                + practice_buttons(f"/practice/coding?skill={gskill}", min(len(gitems), PRACTICE_SIZE))
                + "".join(row(i) for i in gitems)
            )
            return page(gname, body)

        return page(
            s["title"],
            head + practice_buttons(f"/practice/{key}", min(len(items), PRACTICE_SIZE))
            + "".join(row(i) for i in items),
        )

    # -- browse a single item (study mode) --
    @r.get("/item/{item_id}", response_class=HTMLResponse)
    def item(request: Request, item_id: str):
        it = store.get_item(item_id)
        if not it:
            return page("Not found", '<a class="back" href="/">&larr; Home</a><p>Not found.</p>')
        q = display_question(it.content, it.id)
        footer = review_controls(it.id, reviews.get(it.id))
        body = (
            '<a class="back" href="javascript:history.back()">&larr; Back</a>'
            f'<div class="card">{recall_block(it, footer=footer)}</div>'
        )
        return page(q, body)

    # -- practice: start a session --
    @r.get("/practice/{key}")
    def practice_start(request: Request, key: str, skill: str = None, mode: str = None):
        s = STAGE_BY_KEY.get(key)
        if not s:
            return RedirectResponse("/", status_code=303)
        pool = items_for(s["category"])
        if skill:  # optional sub-group filter (e.g. coding -> ml-coding)
            pool = [i for i in pool if i.skill == skill]
        if mode == "random":
            random.shuffle(pool)
            items = pool[:PRACTICE_SIZE]
        else:  # spaced repetition: unseen first, then earliest due
            items = practice_order(pool)[:PRACTICE_SIZE]
        if not items:
            return RedirectResponse(f"/stage/{key}", status_code=303)
        session = Session(
            id=uuid.uuid4().hex,
            user_id=USER,
            skill=key,  # store the STAGE KEY for exit/again nav (not the category)
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
        q = display_question(it.content, it.id)
        pct = int(session.cursor / total * 100)
        rating = (
            f'<form method="post" action="/practice/s/{esc(sid)}/rate" class="rating">'
            '<button class="again" name="grade" value="again">Again</button>'
            '<button class="hard" name="grade" value="hard">Hard</button>'
            '<button class="good" name="grade" value="good">Good</button>'
            '<button class="easy" name="grade" value="easy">Easy</button></form>'
        )
        body = (
            f'<a class="back" href="/stage/{esc(session.skill)}">&larr; Exit</a>'
            f'<div class="progress"><span style="width:{pct}%"></span></div>'
            f'<p class="sub">Card {session.cursor + 1} of {total}</p>'
            f'<div class="card">{recall_block(it, footer=rating)}</div>'
        )
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

    # -- content review (thumbs up/down + comment) --
    @r.post("/review/{item_id}")
    def review_post(item_id: str, body: ReviewIn):
        reviews.put(item_id, body.verdict, body.comment)
        return {"ok": True}

    @r.get("/reviews", response_class=HTMLResponse)
    def reviews_page(request: Request):
        rows = []
        for rec in reviews.all():
            iid = rec.get("item_id", "")
            it = store.get_item(iid)
            q = display_question(it.content, iid) if it else iid
            v = rec.get("verdict", "")
            badge = "👍" if v == "up" else ("👎" if v == "down" else "•")
            cmt = esc(rec.get("comment", ""))
            rows.append(
                f'<a class="q" href="/item/{esc(iid)}"><div class="qt">{badge} {esc(q)}</div>'
                + (f'<div class="sub">{cmt}</div>' if cmt else "")
                + "</a>"
            )
        body = (
            '<a class="back" href="/">&larr; Home</a><header><h1>My reviews</h1></header>'
            + ("".join(rows) or '<p class="sub">No reviews yet — 👍/👎 cards as you go.</p>')
        )
        return page("Reviews", body)

    # -- PWA: manifest, service worker, icon, offline url list --
    @r.get("/manifest.webmanifest")
    def manifest():
        return JSONResponse(
            {
                "name": "AISL Gym", "short_name": "Gym", "start_url": "/", "scope": "/",
                "display": "standalone", "background_color": "#0f1115", "theme_color": "#0f1115",
                "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
            },
            media_type="application/manifest+json",
        )

    @r.get("/icon.svg")
    def icon():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            '<rect width="512" height="512" rx="96" fill="#3b6fe0"/>'
            '<text x="50%" y="52%" font-size="300" text-anchor="middle" dominant-baseline="central"'
            ' fill="#fff" font-family="sans-serif" font-weight="bold">G</text></svg>'
        )
        return Response(svg, media_type="image/svg+xml")

    @r.get("/sw.js")
    def service_worker():
        return Response(SERVICE_WORKER_JS, media_type="application/javascript")

    @r.get("/offline-urls")
    def offline_urls():
        urls = ["/"] + [f"/stage/{s['key']}" for s in STAGES]
        urls += [f"/stage/coding?sub={sk}" for sk in ("ml-coding", "implementation", "algorithms")]
        urls += [f"/item/{it.id}" for it in store.list_items()]
        return JSONResponse(urls)

    return r
