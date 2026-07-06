# Design (MVP blueprint)

Working blueprint for the first cut. Breadth-first: stand up the whole loop thinly
across **all** categories, then iron out details per category. Decisions marked
**[default]** are my calls — override any of them.

> Supersedes the voice-centric framing in [vision.md](vision.md). No voice practice.
> New center of gravity: **"Duolingo for AI-engineering interviews"** — bite-sized,
> gamified, tap-first reps you do on the go. Explicitly *not* a replacement for focused
> desk study.

## 1. Concept

A phone-first web app that turns the [AI Engineering Field Guide](../../ai-engineering-field-guide)
question bank into daily interview-prep reps. The field guide holds the **questions**
(with source citations); this repo holds the **answers** — each one *researched online
and cited*, reviewed by Alexey, then served as interactive exercises.

## 2. Core loop

A **session** = ~7–15 exercises, ~5 min, drawn from one skill.

```
pick skill / daily goal  →  session of exercises  →  score + XP  →  streak & mastery update
                                     ↑                                        │
                                     └──────────── spaced repetition ─────────┘
```

## 3. Categories → flows

The six field-guide categories don't share one flow. They collapse into **three flow
archetypes**; a content item's `type` field selects its flow.

| Category           | Flow type     | Source | Notes |
|--------------------|---------------|--------|-------|
| Theory             | `knowledge`   | `questions/01-theory.md` | LLMs, RAG, agents, eval, ML — split into sub-skills later |
| Coding             | `coding`      | `questions/02-coding.md` | algo (leetcode) + implementation/ML; conceptual answer + pseudocode, desk-out |
| AI system design   | `walkthrough` | `questions/04-ai-system-design.md` | think-aloud + template + mermaid diagram |
| Project deep-dive  | `rehearsal`   | `questions/03-project-deep-dive.md` | *your* projects (FAQ Assistant, DataOps, OLX) |
| Behavioral         | `rehearsal`   | `questions/05-behavioral.md` | STAR stories |
| Home assignments   | `knowledge`   | `questions/06-home-assignments.md` | mostly reference/checklist reps; not a daily-rep core |

Gym-native extras (later modules): recruiter openers, salary scripts, job tracker, metrics/brag-doc.

## 4. The four flows

### A. `knowledge` — shared bank, tap-first
Objective answers everyone shares. SRS-driven. Exercise types, easy → hard:

1. **Multiple choice** — recognition warm-up.
2. **Match / order** — concept↔definition, order pipeline/algorithm steps.
3. **Fill-the-gap** — tap chips into blanks.
4. **Recall flip** — flashcard, self-mark got-it/missed (SRS backbone).
5. **Explain-it** — short typed answer, **LLM-graded against key points**. Rationed 1–2/session. **[default: IN]**

### B. `coding` — solve-and-reveal (conceptual, desk-out)
Two sub-types, both about *how you'd solve it*, not typing code on a phone:

- **Algorithm (LeetCode-style):** show the problem → you think → reveal **conceptual
  approach** (data structure + algorithm choice), **pseudocode**, and **time/space
  complexity** → self-rate. Actual implementation is desk work, out of scope.
  *Source:* Alexey's own [leetcode-solutions](https://github.com/alexeygrigorev/leetcode-solutions)
  repo — his `solutions.md` write-ups (his words) + the C++ solutions — so answers are
  authentic, not researched from strangers.
- **Implementation / ML coding** (progressive builds, refactors, "implement logistic
  regression in NumPy"): same shape — reveal the **design approach**, key decisions, and
  how you'd extend it under follow-ups. Real coding links out to desk.

Self-rated recall, SRS'd. Optional MCQ warm-ups (pick-complexity, spot-the-bug).

### C. `rehearsal` — your own answers, rehearse till it lands
No shared correct answer — the content is *personal* (Behavioral, Project deep-dive).
The file holds the **prompt + probes + rubric** (and optional model structure). Runs in
**two modes**:

- **Author (desk):** write/refine your canonical answer once; LLM critiques vs rubric.
- **Recall (on-the-go):** prompt → say it in your head → reveal *your own saved answer*
  → self-rate. Pure tap, SRS'd like flashcards.

Your actual answer is stored **per-user at runtime**, not in content. This is what
survives from the voice vision, minus voice.

### D. `walkthrough` — think-aloud system design
A scenario you drive verbally. The app shows **guiding questions to think through**
(clarify → high-level → deep-dive → trade-offs), you **answer out loud**, then reveal a
**researched reference answer** and a **mermaid diagram** of the reference architecture.
Self-rated per step. Backed by a reusable **template** (below).

### Templates (system-design study artifact + generator)
For system design, we don't hand-write each answer in isolation. Instead:

```
pick a design question  →  research MANY good answers online (cite)
                        →  synthesize a reusable ANSWER TEMPLATE (save it)
                        →  template becomes study material (you learn the framework)
                        →  generate further walkthroughs FROM the template
```

A template captures the repeatable structure (e.g. the 5-step progression; the RAG /
caching / hallucination-mitigation / scaling patterns) plus a skeleton mermaid diagram.
Templates are first-class content you can study directly, not just generation scaffolding.

## 5. Gamification

- **Streak** (daily), **XP** per session, **daily goal**.
- **Per-skill mastery bars** driven by SRS state.
- Deferred until multi-user: leagues, friends, leaderboards.

## 6. Content model

- **Answers live in this repo as version-controlled YAML files** → review happens in git
  diffs (phone/SSH-friendly). Only `status: approved` items get served.
- Each answer is **researched + cited**, not model-generated from memory.
- Portable by design (answers get hosted elsewhere later) → plain files, stable IDs.
- Format: **YAML** (structured), one file per item: `content/<category>/<id>.yaml`.

### Shared front-matter (all types)

```yaml
id: rag-what-is-rag
category: theory
skill: rag
type: knowledge            # knowledge | rehearsal | walkthrough
question: "What's RAG? Explain the complete process."
difficulty: 2              # 1–3
status: draft              # draft | reviewed | approved
source_refs: [reddit-ai-eng-questions, khushal-kumar]   # back-refs to field-guide citations
sources:                   # MY citations, researched for THIS item (inline OR block form OK)
  - { title: "...", url: "https://...", supports: "definition of RAG" }
```

**Schema conventions (apply to every type):**
- **`question` is the single canonical display field** for the raw interview prompt —
  used by `knowledge` (the question), `coding` (the problem statement), and `rehearsal`
  (the behavioral prompt). Do **not** add separate `problem:`/`prompt:` top-level fields.
  (`walkthrough` uses `scenario` as its headline.)
- **`skill`** must come from the controlled vocabulary in `content/skills.yaml` (e.g.
  `rag`, `agents`, `evaluation`, `llm-practice`, `ml-fundamentals`, `algorithms`,
  `conflict`, …). Ingest tags on this — no free-text.
- **`difficulty` (1–3) is item-level**; the easy→hard exercise ordering in §4A is a
  separate within-item axis. Don't conflate them.
- `sources` may be inline (`{title, url, supports}`) or block mapping form — both valid.
  Each entry may carry a short `key:` (e.g. `igotanoffer`); reference/answer prose then
  cites inline with `[igotanoffer]` tags that the app can resolve to the source.

### `type: knowledge`

```yaml
answer:
  short: "RAG retrieves relevant context from a store and feeds it to the LLM so it answers from your data..."
  key_points:              # used to grade explain-it
    - "retrieval pulls external context; weights unchanged"
    - "chunk → embed → index → retrieve top-k → augment → generate"
follow_ups:
  - "How do you handle it when nothing relevant is retrieved?"
exercises:
  - kind: mcq
    stem: "What does the retrieval step do?"
    options:
      - { text: "Fetches relevant context from a store", correct: true }
      - { text: "Fine-tunes the model on your data" }
      - { text: "Compresses the prompt" }
    explain: "Retrieval pulls context; no weights change."
  - kind: order
    prompt: "Order the RAG pipeline"
    steps: ["Chunk & embed docs", "Store in index", "Embed query", "Retrieve top-k", "Augment prompt", "Generate"]
  - kind: fill
    template: "{0} search finds exact tokens; {1} search finds meaning."
    blanks: ["Keyword", "Vector"]
    chips: ["Keyword", "Vector", "Fuzzy", "Graph"]
  - kind: match
    prompt: "Match each concept to its definition"
    pairs:
      - { left: "Chunking", right: "splitting docs into retrievable units" }
      - { left: "Reranking", right: "reordering retrieved candidates by relevance" }
  - kind: recall             # flashcard flip; self-marked got-it / missed
    front: "What does the retrieval step do?"
    back: "Fetches relevant context from the store to ground generation."
  - kind: explain            # grades typed answer vs answer.key_points
```

### `type: rehearsal`

```yaml
question: "Tell me about a time you had a conflict with a teammate."
probes:                    # interviewer follow-ups to drill
  - "What would you do differently?"
scaffold: { format: STAR, slots: [Situation, Task, Action, Result] }
rubric:
  - "situation is concrete"
  - "your specific action, not the team's"
  - "result is quantified"
example_structure: |       # a STAR skeleton, NOT a real story
  "S: ...  T: ...  A: ...  R: ..."
# the user's own answer is stored per-user at runtime, NOT in this file
```

Project-deep-dive rehearsal adds `your_project: faq-assistant` and project-specific probes.

### `type: coding`

```yaml
subtype: algorithm          # algorithm | implementation
question: "LRU Cache with O(1) get and put."   # the problem statement
answer:
  approach: "Hash map for O(1) lookup + doubly linked list for O(1) recency updates..."
  pseudocode: |
    get(k): if k in map -> move node to head, return val; else -1
    put(k,v): upsert; move to head; if over capacity -> evict tail
  complexity: { time: "O(1) per op", space: "O(capacity)" }
follow_ups: ["How would you make it thread-safe?"]
# implementation subtype uses design_approach + extension_points instead of pseudocode
```

### `type: walkthrough`

```yaml
template_ref: sysdesign-rag-template     # the answer template this is generated from
scenario: "Design a Document Q&A / RAG system for 10M+ articles."
steps:                                    # think-aloud guiding questions (answer out loud, self-rate)
  # phase ∈ { clarify, high-level, deep-dive, tradeoffs, conclude }; phases may repeat
  # (a real design has several deep-dive steps). Citations from template_ref are inherited;
  # `sources` here lists only net-new ones.
  - phase: clarify
    prompt: "What questions do you ask to frame the problem? (users, scale, latency, quality bar)"
    reference: "Clarify: who queries, QPS, freshness needs, accuracy bar, guardrails..."
  - phase: high-level
    prompt: "Sketch the high-level architecture end to end."
    reference: "Ingest → chunk → embed → index; query → embed → ANN retrieve → rerank → augment → generate → cite."
  - phase: deep-dive
    prompt: "Which retrieval index for 10M vectors at low latency, and why?"
    reference: "ANN (HNSW/IVF); brute force too slow at 10M; trade a little recall for latency."
  - phase: tradeoffs
    prompt: "What breaks at scale and how do you detect it?"
    reference: "Cost blowup, stale index, hallucination on empty retrieval; monitor + eval..."
diagram: |                                # mermaid reference architecture
  graph LR
    Q[Query] --> E[Embed] --> R[ANN Retrieve] --> RR[Rerank] --> G[LLM Generate] --> A[Answer + citations]
    D[Docs] --> C[Chunk] --> EM[Embed] --> IDX[(Vector Index)]
    IDX --> R
```

### `type: template` (system-design study artifact)

Templates are first-class content items: they carry the shared front-matter
(`skill`, `difficulty`, `status`) and are served as study material.

```yaml
id: sysdesign-rag-template
category: ai-system-design
skill: rag
type: template
status: draft                              # required — templates are served, so they gate on status
title: "RAG / Document Q&A system design template"
synthesized_from:                          # the many real answers researched (same shape as sources)
  - { title: "IGotAnOffer — GenAI system design", url: "https://...", supports: "5-phase structure" }
  - { title: "Chip Huyen — GenAI platform", url: "https://...", supports: "caching, model gateway" }
framework:                                 # per-phase checklist, studyable
  - phase: frame
    do: ["clarify users, scale, latency, quality bar, guardrails"]
  - phase: high-level
    do: ["ingest/index path", "query/generate path"]
  - phase: deep-dive
    do: ["chunking", "retrieval + ANN", "reranking", "grounding", "eval"]
  - phase: tradeoffs
    do: ["cost", "freshness", "hallucination", "caching", "model tiering"]
key_patterns:                              # cross-cutting synthesis — the core study payload
  - "grounding over trust: cite sources, don't let the LLM assert"
  - "stateless RAG; ACLs enforced at retrieval time"
  - "two-stage retrieval: ANN recall → rerank precision"
  - "model gateway + caching + tiering for cost/latency"
skeleton_diagram: |
  graph LR
    ...
generates: [walkthrough]                   # walkthroughs are generated from this
```

### Content pipeline

```
field-guide question  →  research (web search + fetch, cite)  →  draft YAML
                      →  Alexey review (git)  →  status: approved  →  ingest → serve
```

Export-back to the field guide and user-submitted questions ride on this same schema later.

## 7. Data model (runtime)

- `users` (single user for now)
- `items` (ingested from approved content files)
- `progress` — per user/item SRS state (ease, interval, due date, last grade)
- `answers` — per-user captured `rehearsal` answers + their grades over time
- `sessions` — history, XP, streak

## 8. Architecture

- **Backend:** Python + FastAPI, deployed to **AWS Lambda** (Mangum + API Gateway). **[default]**
- **Content:** authored in git as YAML → ingested at deploy. **[default]**
- **Runtime store:** DynamoDB (multi-user-ready). Local skeleton can read files / SQLite;
  swap to Dynamo before deploy. **[default]**
- **Frontend:** phone-first, **server-rendered FastAPI + HTMX + Alpine.js**, single Lambda
  deploy (HTML + API from one app). Alpine covers tap/drag/streak interactions. Graduate to
  a full SPA only if the feel isn't snappy enough. **[decided]**
- **Auth:** passphrase gate for now (Starlette `SessionMiddleware` signed cookie;
  `GYM_PASSPHRASE`). Magic-link/Cognito when multi-user (AI Shipping Labs).
- **Deploy:** `uv` builds the Lambda package; **CloudFormation** (`infra/cloudformation.yaml`,
  run via `scripts/deploy.sh`) provisions Lambda + HTTP API + ACM cert (DNS-validated in
  Route53) + custom domain + alias. Live at **gym.dtcdev.click** (region eu-west-1).
- **Draft visibility:** `INGEST_INCLUDE_DRAFTS=true` on the sandbox serves draft content
  so you can review authored items from the phone before approving them.

## 9. Screens & navigation

Navigation is **interview-stage first**: the home screen shows the stages of a real
interview loop (from `interview/01-interview-process.md`), each mapped to a content
category and its flow type. You open the app, pick the stage you're prepping, then train.
The stage → category map lives in `app/web.py` (`STAGES`).

Stages: Recruiter Screen · Coding Round · AI/ML Deep-Dive · System Design ·
Project Deep-Dive · Behavioral · Take-Home.

1. **Home** — XP/streak header + interview-stage tiles, each with a question count.
2. **Stage** — the questions in that stage, each tagged with its flow-type badge.
3. **Item / Session** — study the answer (browse mode) or run a session (one exercise at a
   time, immediate feedback). Renders per flow type.
4. **Result** — XP, accuracy, what to review, streak update.
5. (later) job tracker, metrics.

## 10. Build order

1. Design sign-off (this doc).
2. Repo scaffold: backend skeleton, content dir, ingest, one sample item **per flow type**.
3. Core loop end-to-end with a handful of items (thin, all flows rendering).
4. Research pipeline; fill content category-by-category with your review.
5. Gamification (streak/XP/SRS), then deploy to Lambda.
6. Iron out details: frontend choice, sub-skills, multi-user.

## 11. Open / deferred

- Typed explain-it kept? (default yes, rationed.)
- Sub-splitting Theory into RAG/agents/eval/... skills.
- Multi-user + auth timing.
- DynamoDB key/GSI design (e.g. "items due by skill") — a real pass before deploy (#11).
- Runtime field names now live in `app/models.py` (pydantic) — treat that as source of truth over §7's bullet list.
