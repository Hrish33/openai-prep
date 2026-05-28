# Practice files — threading primitives

**These are scaffolds, not finished code.** Each file has the structure laid out with `# TODO` markers where you fill in the implementation. Run as-is and you'll hit `NotImplementedError` — that's expected. Fill in, then run.

The point is to build muscle memory by typing the pattern, not to read a reference.

| File | What you're implementing |
|------|--------------------------|
| `01_producer_consumer.py` | Raw `queue.Queue` + `threading.Thread`. The four-phase lifecycle. ~20 lines of code. |
| `02_worker_pool.py` | Same lifecycle wrapped in a context manager. Should feel like a refactor of 01. |
| `03_check_then_act_race.py` | Two functions: one that races, one that's locked. Demonstrates why the visited-set needs a lock. |
| `04_recursive_enqueue.py` | The crawler's shape in miniature — workers themselves put new work on the queue. Closest thing to the real problem. |

## Workflow

For each file:

1. **Read** the docstring at the top — it tells you what "working" looks like.
2. **Sketch** what each `# TODO` should be before typing.
3. **Type** the implementation.
4. **Run** it. Compare output to the expected description in the docstring.
5. **Delete** your implementation. Re-do it from scratch the next day.

## How to run

```bash
cd coding/week3/08_multithreaded_crawler/practice
python 01_producer_consumer.py
python 02_worker_pool.py
python 03_check_then_act_race.py
python 04_recursive_enqueue.py
```

## Readiness bar

Once you can fill in `01_producer_consumer.py` from a blank screen (delete everything in the file except imports and run it again — write it back) in **under 5 minutes**, you're ready to attempt `solution.py`. Not before.

## Stuck?

Re-read the relevant Concept in `../00_prereqs.md`:
- 01, 02 → Concept 2 (queue.Queue)
- 03    → Concept 3 (check-then-act race)
- 04    → Concept 4 (termination) + Concept 3 (the lock)
