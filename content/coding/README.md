# Coding question bank — curation notes

Curated 2026-07-06 to keep only problems **representative of real AI Engineer /
Applied AI / GenAI / LLM-focused ML Engineer coding rounds** (2025–2026), grounded in
the AI Engineering Field Guide (`interview/questions/02-coding.md`) plus a fresh web
sweep of first-hand interview recaps (Yuan Meng, Hello Interview, linkjob
OpenAI/Anthropic/xAI, Sundeep Teki, Mimansa Jaiswal, interviewing.io/Databricks).

61 cards kept; 38 non-representative LeetCode problems moved to `../../parked/coding/`
(outside `content/`, never ingested — see that folder's README for the rationale).

## The three coding-round formats (what the bank mirrors)

1. **ML coding** (NumPy/PyTorch from scratch) — the signature AI-eng round.
   `aieng-softmax-numpy`, `aieng-self-attention-forward`, `aieng-cosine-similarity-numpy`,
   `aieng-kmeans-numpy`, `aieng-logistic-regression-numpy`, `aieng-debug-embeddings`.
2. **Multi-level implementation / OOP** — heavily over-indexed at OpenAI, Anthropic,
   xAI, Databricks. `aieng-key-value-store`, `aieng-in-memory-db`,
   `aieng-credits-expiry-system`, `aieng-web-crawler`, `aieng-rle-encoding`.
3. **Algorithm round** (mostly easy/medium, occasional hard at frontier labs) — the
   kept numbered LeetCode set, restricted to the patterns that actually recur:
   hash-map/array/string, linked lists, trees/BST, graph BFS/DFS/topo-sort, heaps/top-k,
   tries, stacks, intervals, backtracking basics, and design (LRU/LFU/trie).

## Notable kept cards, by why

- **Design (explicitly named in recaps):** `lru-cache` (xAI/Anthropic), `460-lfu-cache`,
  `211-design-add-and-search-words` (trie), `297-serialize-and-deserialize-binary-tree`
  (Microsoft senior).
- **Heap / top-k (recur often):** `215-kth-largest`, `347-top-k-frequent`,
  `295-find-median-from-data-stream`, `023-merge-k-sorted-lists`.
- **Graph BFS/DFS/topo:** `200-number-of-islands`, `207-course-schedule`, `127-word-ladder`.
- **Named AI-eng specifics:** `aieng-excel-column-name` & `aieng-reverse-linked-list`
  (Microsoft AI-assisted round), `aieng-primes-0-100` & `aieng-cosine-similarity-numpy`
  (Amazon GenAI phone screen).

## Recommended additions (not yet authored)

High-value problem types that recur in 2025–2026 AI-eng recaps but aren't in the bank
yet — good candidates to author next:

- **Time-Based Key-Value Store** (LC 981) — OpenAI, repeatedly.
- **Spreadsheet / formula evaluator** with cell dependencies + cycle detection
  (topological eval) — signature OpenAI implementation problem.
- **Rate limiter from scratch** — "write it without looking up syntax," labs broadly.
- **Tokenizer** (tokenize/detokenize, UNK handling, BPE/trie) — Anthropic code-review.
- **Decoding strategies as coding cards** — beam search / top-k / top-p / temperature /
  autoregressive loop (the most on-brand GenAI coding problems).
- **ML-debugging card** — "model runs but doesn't learn" (wrong softmax dim, double
  softmax before cross-entropy, missing `zero_grad`, broadcasting, dataloader shuffle).
- **Resumable / stateful iterator** with `getState`/`setState` across files — OpenAI.
