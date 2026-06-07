# Concept guides

In-repo learning materials for Python concepts that can't be practiced on LeetCode. Generated on demand as you reach problems that need them.

## How it works

Each problem's `00_prereqs.md` lists either:
- **External primers** → LeetCode problems (you practice there directly)
- **Internal primers** → concept guides here (Python-specific stuff LC doesn't teach)

When you reach a problem with an internal primer, ask Claude Code to generate the concept guide. It'll be tailored to the problem you're approaching.

## Planned concept guides

These will be generated as you need them:

| Guide | Needed for | Status |
|-------|-----------|--------|
| [`iterators.md`](iterators.md) | Problem 4 (Resumable Iterator) | **Generated** — read alongside `week2/04_resumable_iterator/00_prereqs.md`. Generator drills at [`practice/generators/`](practice/generators/) (5 files). |
| `parsing.md` | Problem 7 (In-Memory SQL) | Not yet generated |
| `threading.md` | Problem 8 (Multithreaded Crawler) | **Done via drills** — `week3/08_multithreaded_crawler/practice/01–05.py` plus the prereqs doc cover the same material end-to-end. No separate guide planned. |
| [`asyncio.md`](asyncio.md) | Problem 4 (async follow-up), Problem 8 alt + general | **Generated** — sections 1–4 self-contained for Problem 4's async follow-up; 5–7 for Problem 8. Drills at [`practice/asyncio/`](practice/asyncio/) (6 files). |
| `generators.md` | Generally useful, may apply to several | Not yet generated |
| `context_managers.md` | General Python depth | Not yet generated |
| `dunder_methods.md` | General Python depth | Not yet generated |

## When to generate one

Ask Claude Code: **"generate the iterators concept guide"** (or whichever).

What it'll do: produce a guide in the format below, tuned to the problem context.

## Format

Each concept guide has:

1. **The 30-second pitch** — what this concept actually is, in plain English
2. **The minimal Python code** — smallest example that illustrates it
3. **How CPython implements it** — at the level a senior engineer should know
4. **Common patterns** — 3-5 idiomatic uses
5. **Common mistakes** — what trips people up
6. **Exercises** — small problems to practice, with solutions in a collapsible section
7. **How this shows up in OpenAI interviews** — the connection to actual interview questions

Read the guide → do the exercises → then attempt the problem that needed it.
