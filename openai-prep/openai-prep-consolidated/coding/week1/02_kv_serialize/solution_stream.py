"""
Streaming KV codec — follow-up #1 from interviewer_notes.md.

The base codec materializes the whole blob in memory. The streaming
variant works on file-like / socket-like objects: anything that supports
`.read(n)` returning up to n bytes (and `b""` on clean EOF).

API:
  - deserialize_stream(stream) -> Iterator[tuple[str, str]]
        Lazily yields (key, value) pairs as the stream is consumed.
        Caller drives pace with next() or `for k, v in ...`.

  - serialize_stream(records: Iterable[tuple[str, str]]) -> Iterator[bytes]
        Lazily yields encoded chunks. Caller can stream to a file/socket
        without ever materializing the whole blob.

Format is identical to the base codec — same [4-byte BE length][utf-8 bytes]
record shape. A stream produced by `serialize_stream` is byte-for-byte
equivalent to `KVCodec().serialize(dict(records))`.

Things worth thinking about before you write a line:

  1. EOF policy. `stream.read(4)` can return three things: 4 bytes
     (a full header), `b""` (clean end of stream — no more records,
     not an error), or 1-3 bytes (truncation — error). Encode the
     distinction.

  2. Generator semantics. `yield` here is doing work for you — the
     caller's `next()` is what drives one record's worth of reads.
     Don't pre-read the whole stream; that would defeat the point.

  3. Same wire format. You should be able to round-trip:
        b"".join(serialize_stream(d.items())) == KVCodec().serialize(d)
     If that property doesn't hold, the formats have drifted.

  4. Errors raise ValueError, same contract as the base.
"""

import struct  # noqa: F401
from typing import Iterable, Iterator, Tuple, BinaryIO


def serialize_stream(records: Iterable[Tuple[str, str]]) -> Iterator[bytes]:
    """Yield encoded chunks for each (key, value) pair, lazily."""
    for k, v in records:
        buffer = bytearray()
        key = k.encode("utf-8")
        buffer.extend(struct.pack('>I', len(key)))
        buffer.extend(key)
        value = v.encode("utf-8")
        buffer.extend(struct.pack('>I', len(value)))
        buffer.extend(value)
        yield bytes(buffer)


def _read_exact(stream: BinaryIO, n: int, what: str) -> bytes:
    """Read exactly n bytes from stream, or raise ValueError(truncated <what>)."""
    buf = stream.read(n)
    if len(buf) < n:
        raise ValueError(f"truncated {what}")
    return buf


def deserialize_stream(stream: BinaryIO) -> Iterator[Tuple[str, str]]:
    """Yield (key, value) pairs from a stream of length-prefixed bytes."""
    while True:
        header = stream.read(4)
        if not header:                                       # clean EOF
            return
        if len(header) < 4:                                 # truncation at boundary
            raise ValueError("truncated key length header")
        (key_len,) = struct.unpack('>I', header)

        key = _read_exact(stream, key_len, "key payload").decode("utf-8")
        (val_len,) = struct.unpack('>I', _read_exact(stream, 4, "value length header"))
        value = _read_exact(stream, val_len, "value payload").decode("utf-8")

        yield key, value



