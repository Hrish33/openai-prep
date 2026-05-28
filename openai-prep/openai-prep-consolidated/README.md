# OpenAI Applied Foundations — Backend SWE Prep

## Philosophy

**Learning the material > being interviewed.** This repo is structured to teach concepts first, with timed interview practice as a secondary layer.

Each coding problem is a learning unit:
1. **Prereqs** (`00_prereqs.md`) — what to learn before attempting (LeetCode primers + Python concept guides)
2. **Problem** (`problem.md`) — the actual interview problem, once you've built the skills
3. **Solution stub** (`solution.py`) — empty starter to fill in
4. **Tests** (`test_solution.py`) — reference test suite
5. **Notes** (`interviewer_notes.md`) — reference solution + follow-ups, read after attempt

System design is handled separately via HelloInterview Premium.
Behavioral stories live in `behavioral/`.

---

## Folder map

```
openai-prep/
├── README.md                       ← this file
├── CLAUDE.md                       ← how Claude Code should behave
├── PLAN.md                         ← 3-week schedule
│
├── coding/
│   ├── concepts/                   ← Python internals guides (generated on demand)
│   │   └── README.md
│   ├── week1/
│   │   ├── 01_spreadsheet/         ← fully scaffolded
│   │   ├── 02_kv_serialize/        ← README only (scaffold on demand)
│   │   └── 03_time_based_kv/       ← README only
│   ├── week2/
│   │   ├── 04_resumable_iterator/  ← README only
│   │   ├── 05_unix_cd_symlinks/    ← README only
│   │   └── 06_meeting_rooms/       ← README only
│   └── week3/
│       ├── 07_in_memory_sql/       ← README only
│       └── 08_multithreaded_crawler/ ← README only
│
├── deep-dive/
│   └── PROJECT.md                  ← your project narrative
├── behavioral/
│   ├── STORIES.md                  ← your STAR stories
│   └── AI_POV.md                   ← your point of view on AI
└── mock-loops/                     ← debriefs from mock sessions
```

---

## Problem list (all from HelloInterview's verified OpenAI question set)

| # | Problem | Week | Key concept |
|---|---------|------|-------------|
| 1 | Spreadsheet with Dependencies | 1 | Graphs, topo sort, parsing |
| 2 | KV Serialize/Deserialize | 1 | Length-prefix encoding, bytes |
| 3 | Time-Based KV Store | 1 | Binary search |
| 4 | Resumable Iterator | 2 | Iterator protocol (Python internals) |
| 5 | Unix `cd` with Symlinks | 2 | Path parsing, cycle detection |
| 6 | Meeting Rooms | 2 | Interval scheduling, sweep line |
| 7 | In-Memory SQL | 3 | Parsing + execution |
| 8 | Multithreaded Crawler | 3 | Concurrency (Python internals) |

---

## How to work through this

**For each problem:**

1. Read the problem's `00_prereqs.md` (or `README.md` if not scaffolded yet)
2. Work the LeetCode prereqs OR read the relevant concept guide
3. When prereqs feel solid, attempt the problem (open `solution.py` and `test_solution.py`)
4. Run tests: `pytest coding/weekX/0N_<name>/test_solution.py -v`
5. After your attempt: read `interviewer_notes.md` for the reference solution and grading

**Pacing:** ~3-5 hours of prereq work per problem (spread over days), then 60-75 min for the problem itself. Don't compress the prereq work — the muscle has to form.

---

## How to use Claude Code in this repo

Default behavior is **coach/teacher**. Just talk to it normally:
- "Help me understand topological sort"
- "Review my solution.py"
- "Why is my cycle detection failing?"
- "Walk me through how Kahn's algorithm works"

For interview simulation, use explicit triggers:
- `timer started, 60 min` → strict interviewer mode (silent)
- `timer done` or `review mode` → honest code review against the OpenAI rubric
- `scaffold problem 4` → generates the full problem files for problem 4
- `generate the iterators concept guide` → creates `coding/concepts/iterators.md`

See `CLAUDE.md` for the full behavior spec.

---

## Setup

```bash
cd openai-prep
python3 -m venv venv
source venv/bin/activate
pip install pytest pytest-asyncio
git init && git add . && git commit -m "Initial setup"
```

Open in IntelliJ. Open integrated terminal. Run `claude`.

---

## Suggested starting move

Open `coding/week1/01_spreadsheet/00_prereqs.md` and start working through the LeetCode primers. That's the actual first step — not coding problem 1.
