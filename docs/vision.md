# Vision

**AI Engineering Gym** is a phone-first app for preparing for AI engineering interviews. It is a personal "gym" — a place to do daily reps on the things that decide interviews: explaining projects under pressure, recalling technical concepts quickly, and rehearsing the pitch until it sounds natural.

The motivation is specific. Interview readiness is not the same as knowledge. You can know RAG deeply and still fumble the explanation in a live call. The gym is built around the thing that actually fixes that: **recording yourself answering interview questions, rating the answer, and repeating until it lands.**

## Why phone-first

The strongest constraint that shaped this project: most of the prep happens from a phone, often while traveling or away from a computer. So the gym is designed around short sessions (25-35 min/day) that work entirely on a small screen:

- tap through flashcards one-handed;
- record a spoken answer, transcribe it, self-rate it;
- glance at a job tracker and a metrics dashboard.

Anything that needs a real keyboard or a big screen is out of scope for the MVP. The gym is the thing you open on the train.

## What's in the gym

The app is organized around a few connected tools, each tied to a concrete prep outcome:

- **Flashcards & spaced repetition.** Daily cards on RAG, evals, agents, production engineering, system design, behavioral stories, and salary scripts. Spaced repetition keeps old cards coming back before you forget them.
- **Voice practice.** The centerpiece. Pick a question, record yourself answering it, get a transcript, and rate the answer on clarity, structure, conciseness, depth, and confidence. Over time this builds a log of recorded answers — the single best measure of real interview readiness.
- **Question bank.** Categorized prompts: behavioral, project deep-dives (FAQ Assistant, DataOps, OLX), RAG/system design, and the standard recruiter openers ("tell me about yourself", "why are you looking").
- **Job tracker.** Save a role, classify it as practice / serious / exceptional, extract keywords, compare against the CV, and keep interview-process notes per company.
- **Metrics dashboard.** Business-automation and project-eval numbers in one place, so the "I automated X hours/week" pitch is grounded in real figures.
- **Brag doc generator.** Turn a project README, eval outputs, and architecture notes into a 60-second pitch, STAR stories, and likely interviewer questions.

## Guiding principles

- **Record-first.** If a feature doesn't help you rehearse, recall, or track real evidence, it doesn't belong in the MVP.
- **Mobile-only sessions.** Every core flow must be usable one-handed on a phone. Desktop is a nice-to-have, not the target.
- **Small daily reps beat big cram sessions.** The app rewards a few minutes every day over an occasional hour.
- **Evidence over vibes.** Track metrics and recorded answers so improvement is measurable, not just felt.
- **Build it with agents, review from the phone.** The app itself is developed with coding agents and reviewed over SSH from the phone — the same constraint it's designed for.

## What this repo is right now

This repository currently holds only the vision and README. No code yet — it's the target the first implementation sprint aims at.
