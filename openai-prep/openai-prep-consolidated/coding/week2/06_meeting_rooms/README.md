# Problem 6: Meeting Rooms / Interval Scheduling

**Status:** Not yet scaffolded. Tell Claude Code "scaffold problem 6" when you're ready.

**One-liner:** Given a list of meeting intervals, determine if a person can attend all, OR the minimum number of rooms needed.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/design-sql-2408/cm5eguhah03va838ozuanzsde) (referenced in their OpenAI article)

**Key concept:** sweep line algorithm + interval reasoning

**Likely prereqs:**
- [LeetCode 252 — Meeting Rooms](https://leetcode.com/problems/meeting-rooms/) (Easy, premium) — "can attend all"
- [LeetCode 253 — Meeting Rooms II](https://leetcode.com/problems/meeting-rooms-ii/) (Medium, premium) — "minimum rooms needed"
- If you don't have LC premium: same problems are widely written up; search "meeting rooms II Python"
- Concepts: sorting by start time, min-heap for end times, OR the sweep line approach (separate start/end events, sort, count)

**When to do this:** week 2. The most "algorithmic" problem in the set — closest to a classic LC pattern. Good if you want a break from the bigger system-y problems.
