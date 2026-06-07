"""
Resumable composite iterator.

Read 00_prereqs.md (iterator protocol + state design), then problem.md.
Sketch your state shape before coding.

Suggested structure (you don't have to follow this — design what makes
sense to you):
  - keep `sources` as the original input (re-iterable)
  - cursor: which source you're currently in (int) + offset within it (int)
  - `__next__`:
      walk forward across sources, skipping empties, until you yield one
      item or raise StopIteration
  - `get_state`: return a fresh dict with the two cursor ints
  - `set_state`: store cursor; lazily open the source on next __next__,
                 OR eagerly seek (decide and justify)

The interview signal is the state shape, not the code length. Aim for
a state dict that's literally:
    {"source_idx": int, "offset": int}
plus whatever you need for the per-source independent-state follow-up.
"""

from typing import Iterable, TypeVar, List, AsyncIterable

T = TypeVar("T")


class CompositeIterator:
    def __init__(self, sources : List[List[T]]):
        self.sources = sources
        self.state= {"source_index" : 0, "index" : 0 }

    def __iter__(self):
        return self

    def __next__(self):
        source_index = self.state["source_index"]
        index = self.state["index"]

        while source_index < len(self.sources) and index >= len(self.sources[source_index]) :
            source_index += 1
            index = 0
        if source_index >= len(self.sources):
            raise StopIteration
        ele = self.sources[source_index][index]
        self.state= {"source_index" : source_index, "index" : index + 1 }
        return ele

    def get_state(self):
        return self.state.copy()

    def set_state(self, state):
        self.state = state.copy()

class AsyncCompositeIterator:
    def __init__(self, sources : List[AsyncIterable[T]]):
        self.sources = sources
        self.state= {"source_index" : 0, "index" : 0 }

    def __aiter__(self):
        return self

    async def __anext__(self):
        source_index = self.state["source_index"]
        index = self.state["index"]
        while source_index < len(self.sources) and index >= len(self.sources[source_index]) :
            source_index += 1
            index = 0
        if source_index >= len(self.sources):
            raise StopAsyncIteration
        ele = self.sources[source_index][index]
        self.state= {"source_index" : source_index, "index" : index + 1 }
        return ele

    def get_state(self):
        return self.state.copy()

    def set_state(self, state):
        self.state = state.copy()