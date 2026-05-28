# Problem 8: Multithreaded Web Crawler

**Status:** Scaffolded. Work the files in order.

**One-liner:** Build a crawler that uses multiple threads to fetch pages concurrently, dedupes URLs, restricts to same-host, and terminates cleanly.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/multithreaded-web-crawler/cmbsl2nhd005107adsfu8ohme) — mirrors [LeetCode 1242](https://leetcode.com/problems/web-crawler-multithreaded/)

**Key concept:** concurrency primitives (`queue.Queue`, `threading.Lock`, `task_done`/`join`, sentinels)

## Files

| File | When to read |
|------|--------------|
| `00_prereqs.md` | First. 4-6 hours of foundation work — GIL, queues, locks, termination. Don't skip. |
| `problem.md` | Once prereqs feel solid. The actual interview problem. |
| `solution.py` | Empty starter. Fill in. |
| `test_solution.py` | `pytest test_solution.py -v` — includes a speedup test that catches lock-during-fetch. |
| `interviewer_notes.md` | **After** your attempt. Reference solution, async variant, grading rubric, common mistakes. |

## When to do this

Week 3. The big concurrency problem. Don't tackle without working through `00_prereqs.md` — concurrency bugs are easy to write and hard to debug, and the muscle has to actually be there.
