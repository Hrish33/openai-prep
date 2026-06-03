"""
Add get_state / set_state to your Range — the bridge to the real problem.

GOAL: ResumableRange(start, stop, step) iterates like Range, but exposes
save/restore so iteration can be paused and resumed across instances.

When working, expect output:
  first three: [0, 1, 2]
  state at pause: {'cursor': 3}
  state is JSON-serializable: True
  remainder after resume: [3, 4, 5, 6, 7, 8, 9]
  resume at start: [0, 1, 2, 3, 4]
  resume past exhaustion: []

Why this drill matters:
  This is CompositeIterator without the "multiple sources" complication.
  You're proving the state-design instinct on a single-source iterator.
  Once this feels reflexive, generalizing to "list of sources" is mostly
  adding a source_idx alongside the cursor.

State design rules (the muscle to build):
  1. The state is a dict. JSON-serializable. No live iterators, no pickle.
  2. The state is the MINIMUM information to resume — for Range, that's
     just the cursor. (Start/stop/step come from the constructor, not state.)
  3. get_state returns a FRESH dict, not a reference. Two get_state calls
     followed by mutation of one should not affect the other.
  4. set_state replaces the cursor — subsequent __next__ resumes from there.
"""

import json



class ResumableRange:
    def __init__(self, start, stop = None, step = 1):
        if step <= 0:
            raise ValueError
        self.step = step
        if stop is None:
            self.start = 0
            self.stop = start
        else :
            self.stop = stop
            self.start = start
        self.cursor = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.step > 0 and self.cursor >= self.stop:
            raise StopIteration
        if self.step < 0 and self.cursor <= self.stop:
            raise StopIteration

        val = self.cursor
        self.cursor += self.step
        return val

    def get_state(self):
        return {"cursor" : self.cursor}

    def set_state(self, state):
        self.cursor = state['cursor']


def main() -> None:
    it = ResumableRange(0, 10)

    first_three = [next(it), next(it), next(it)]
    print("first three:", first_three)

    state = it.get_state()
    print("state at pause:", state)
    print("state is JSON-serializable:", json.loads(json.dumps(state)) == state)

    # Resume on a fresh instance
    it2 = ResumableRange(0, 10)
    it2.set_state(state)
    print("remainder after resume:", list(it2))

    # Resume "from start" (state captured before any next)
    it3 = ResumableRange(0, 5)
    start_state = it3.get_state()
    it4 = ResumableRange(0, 5)
    it4.set_state(start_state)
    print("resume at start:", list(it4))

    # Resume from exhausted state
    it5 = ResumableRange(0, 3)
    list(it5)                          # drain
    exhausted_state = it5.get_state()
    it6 = ResumableRange(0, 3)
    it6.set_state(exhausted_state)
    print("resume past exhaustion:", list(it6))


if __name__ == "__main__":
    main()
