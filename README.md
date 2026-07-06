# AI Engineering Gym

A phone-first app for preparing for AI engineering interviews. A personal "gym" for doing daily reps on what actually decides interviews: explaining your work under pressure, recalling technical concepts fast, and rehearsing the pitch until it sounds like you.

> Interview readiness is not the same as knowledge. You can know RAG deeply and still fumble the explanation in a live call. This project is built around the thing that fixes that: **recording yourself answering interview questions, rating the answer, and repeating until it lands.**

## Why

Most prep happens from a phone — on a train, between things, away from a desk. So the gym is designed for short, one-handed sessions (25-35 min/day) instead of long desk sessions. The core loop is:

- tap through flashcards (spaced repetition);
- record a spoken answer, transcribe it, self-rate it;
- track real jobs and real metrics.

## What's in it

- **Flashcards & spaced repetition** — daily cards on RAG, evals, agents, production engineering, system design, behavioral stories, and salary scripts.
- **Voice practice** — the centerpiece. Record an answer, get a transcript, rate yourself on clarity, structure, depth, and confidence, and build a log of recorded answers over time.
- **Question bank** — categorized prompts: behavioral, project deep-dives, RAG/system design, and recruiter openers.
- **Job tracker** — save a role, classify it as practice / serious / exceptional, compare against your CV, and keep per-company interview notes.
- **Metrics dashboard** — automation and eval numbers in one place so claims are grounded in real figures.
- **Brag doc generator** — turn a project README and eval outputs into a 60-second pitch, STAR stories, and likely interviewer questions.

## Principles

- **Record-first.** If a feature doesn't help you rehearse, recall, or track real evidence, it's out of the MVP.
- **Mobile-only sessions.** Every core flow must work one-handed on a phone.
- **Small daily reps beat big cram sessions.**
- **Evidence over vibes.**

## Status

This repo currently holds only the [vision](docs/vision.md) and this README. No implementation yet — it's the target for the first sprint.

## Background

The concept came out of planning a phone-first interview prep workflow during a holiday period with limited computer access. The gym is meant to be built with coding agents and reviewed from the phone over SSH — the same constraint it's designed for.
