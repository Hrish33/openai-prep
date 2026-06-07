"""
Stateful generator — the section 3 pattern from iterators.md.

GOAL: chunked(text, size) yields slices of `text` of length `size`. The
last chunk may be shorter.

When working, expect output:
  list(chunked("hello world", 3)): ['hel', 'lo ', 'wor', 'ld']
  list(chunked("", 3)):             []
  list(chunked("abc", 5)):          ['abc']
  list(chunked("abcdef", 2)):       ['ab', 'cd', 'ef']

Compare to your class-based ChunkedReader (../../../week2/04_resumable_iterator/
practice/03_chunked_reader.py): same observable behavior, ~1/3 the lines.

The state — `cursor` — lives in the function frame. CPython keeps the frame
alive between yields, so the local retains its value. That's why this works
without `self.cursor`. The frame IS the state.

Two rules:
  1. The local variables ARE the state. Don't introduce a class for this.
  2. No explicit StopIteration — falling off the end of the function
     raises it implicitly.
"""


def chunked(text, size):
      cursor = 0
      while cursor < len(text):
          yield text[cursor : cursor + size]
          cursor += size


def main() -> None:
    # print('list(chunked("hello world", 3)):', list(chunked("hello world", 3)))
    # print('list(chunked("", 3)):            ', list(chunked("", 3)))
    # print('list(chunked("abc", 5)):         ', list(chunked("abc", 5)))
    # print('list(chunked("abcdef", 2)):      ', list(chunked("abcdef", 2)))

        for chunk in chunked("abcdef", 2):
            print(chunk)


if __name__ == "__main__":
    main()
