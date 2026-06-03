"""
Iterator that yields fixed-size chunks of a string.

GOAL: ChunkedReader(text, chunk_size) yields successive slices of `text`,
each of length `chunk_size`, except possibly the last which may be shorter.

When working, expect output:
  list(ChunkedReader("hello world", 3)):    ['hel', 'lo ', 'wor', 'ld']
  list(ChunkedReader("", 3)):                []
  list(ChunkedReader("abc", 5)):             ['abc']
  list(ChunkedReader("abcdef", 2)):          ['ab', 'cd', 'ef']
  invalid chunk_size:                         ValueError raised as expected

Why this drill matters:
  This is the closest single-source analog of the real problem. The cursor
  is an integer offset into the text. Advance by `chunk_size` each next().
  Stop when the cursor is past the end. This is the exact same shape as
  CompositeIterator's "offset within current source."

Subtleties:
  - The final chunk is "len(text) - cursor" long, which can be < chunk_size.
    Just slice — Python handles this for you. Don't write special logic.
  - chunk_size <= 0 is ValueError (infinite loop / negative slice).
  - Empty input string is a valid empty iterator, not an error.
"""


class ChunkedReader:
    def __init__(self, text: str, chunk_size: int) -> None:
        if chunk_size <= 0:
            raise ValueError
        self.text = text
        self.len = len(self.text)
        self.chunk = chunk_size
        self.current = 0


    def __iter__(self) -> "ChunkedReader":
        return self

    def __next__(self) -> str:
        if self.current >= self.len:
            raise StopIteration

        next_ptr = min(self.len, self.current + self.chunk)
        next_chunk = self.text[self.current: next_ptr]
        self.current = next_ptr

        return next_chunk


def main() -> None:
    print('list(ChunkedReader("hello world", 3)):   ', list(ChunkedReader("hello world", 3)))
    print('list(ChunkedReader("", 3)):               ', list(ChunkedReader("", 3)))
    print('list(ChunkedReader("abc", 5)):            ', list(ChunkedReader("abc", 5)))
    print('list(ChunkedReader("abcdef", 2)):         ', list(ChunkedReader("abcdef", 2)))

    try:
        ChunkedReader("hi", 0)
        print("invalid chunk_size:                       BUG — should have raised")
    except ValueError:
        print("invalid chunk_size:                       ValueError raised as expected")


if __name__ == "__main__":
    main()
