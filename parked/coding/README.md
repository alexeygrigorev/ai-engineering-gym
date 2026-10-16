# Parked coding problems

These LeetCode problems were moved out of the active bank (`content/coding/`) on
2026-07-06 because they are **not representative of what companies actually ask in
AI Engineer / Applied AI / GenAI / LLM-focused ML Engineer coding rounds**.

Nothing here is deleted — this folder is outside `content/`, so it is never
ingested or served, but the cards are preserved and can be moved back at any time
(`git mv parked/coding/<file> content/coding/`).

## Why these were parked

The decision was grounded in two aligned sources:

1. The **AI Engineering Field Guide** (`interview/questions/02-coding.md`,
   `interview/01-interview-process.md`) — consolidated from 100+ interview recaps.
2. A fresh 2025–2026 web sweep of first-hand interview reports (Yuan Meng "MLE
   Interview 2.0", Hello Interview OpenAI, linkjob OpenAI/Anthropic/xAI question
   banks, Sundeep Teki, Mimansa Jaiswal, interviewing.io/Databricks).

Both agree: AI-eng coding rounds reward **"can you build a correct, well-structured,
edge-case-handled component and reason about it"** (KV stores, crawlers, in-memory
DBs, model layers, top-k/heap, tries, graph BFS/DFS) — **not** "did you memorize the
one algorithmic trick." Anthropic explicitly states its round *"doesn't benefit from
memorizing standard algorithms or data structures."* "DP doesn't appear unless
you're at Google" (Yuan Meng).

The parked problems fall into categories that did **not** appear in any first-hand
AI-eng recap:

- **Esoteric hard DP** — regex matching (010), longest-valid-parens (032), edit
  distance (072), scramble string (087), interleaving string (097), distinct
  subsequences (115), best-time-III (123).
- **Math / bit-manipulation tricks** — count primes (204), single-number-II (137),
  gray code (089), largest palindrome product (479).
- **Geometry / grid gotchas** — trapping rain water (042), largest rectangle in
  histogram (084), maximal rectangle (085).
- **Backtracking puzzles** — sudoku solver (037), N-Queens (051/052), word ladder II
  (126).
- **Heavy data-structure engineering** — range-sum-query-mutable / segment tree (307),
  find-duplicate-subtrees (652), sliding-window median (480), sliding-window max (239).
- **Sliding-window / two-pointer "speed gotchas"** — min-window-substring (076),
  substring concatenation (030). (When strings show up in AI-eng rounds it's
  parsing/tokenizing, not window optimization.)
- **String-parsing trivia** — zigzag (006), reverse integer (007), atoi (008),
  text justification (068).
- **Redundant variants** of a kept card — 3sum-closest (016, vs 015), search-rotated-II
  (081, vs 033), remove-dupes-sorted-list-II (082, vs 083), jump-game-II (045, vs 055),
  median-of-two-sorted-arrays (004, a binary-search gotcha), recover-BST (099),
  insertion-sort-list (147), bus-routes (815, esoteric BFS).

## What was kept and why

See `content/coding/README.md` for the kept set and the reasoning.
