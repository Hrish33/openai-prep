"""
Tests for the streaming codec.
Run: pytest coding/week1/02_kv_serialize/test_solution_stream.py -v
"""

import io
import pytest
from solution import KVCodec
from solution_stream import serialize_stream, deserialize_stream


# --- Basic deserialize_stream ---

def test_deserialize_stream_single_record():
    blob = KVCodec().serialize({"name": "alice"})
    print(blob)
    pairs = list(deserialize_stream(io.BytesIO(blob)))
    assert pairs == [("name", "alice")]


def test_deserialize_stream_multiple_records():
    original = {"name": "alice", "city": "NYC", "lang": "python"}
    blob = KVCodec().serialize(original)
    pairs = list(deserialize_stream(io.BytesIO(blob)))
    assert dict(pairs) == original


def test_deserialize_stream_empty_blob():
    """Empty stream yields zero pairs — not an error."""
    pairs = list(deserialize_stream(io.BytesIO(b"")))
    assert pairs == []


def test_deserialize_stream_yields_lazily():
    """next() should produce one pair without consuming the whole stream."""
    blob = KVCodec().serialize({"a": "1", "b": "2", "c": "3"})
    stream = io.BytesIO(blob)
    gen = deserialize_stream(stream)
    first = next(gen)
    assert first == ("a", "1")
    # After one pair, the stream still has bytes for b and c left.
    # tell() should be well short of the total length.
    assert stream.tell() < len(blob)


def test_deserialize_stream_unicode():
    blob = KVCodec().serialize({"🔑": "値", "k": "héllo"})
    pairs = list(deserialize_stream(io.BytesIO(blob)))
    assert dict(pairs) == {"🔑": "値", "k": "héllo"}


# --- Streaming truncation cases (raise ValueError) ---

def test_deserialize_stream_truncated_header_raises():
    blob = KVCodec().serialize({"key": "value"})
    truncated = blob[:2]  # not even a full length prefix
    with pytest.raises(ValueError):
        list(deserialize_stream(io.BytesIO(truncated)))


def test_deserialize_stream_truncated_payload_raises():
    blob = KVCodec().serialize({"key": "value"})
    truncated = blob[:-3]  # lop off some of the value bytes
    with pytest.raises(ValueError):
        list(deserialize_stream(io.BytesIO(truncated)))


def test_deserialize_stream_clean_eof_between_records_is_not_an_error():
    """Stream ending exactly at a record boundary is the normal end case."""
    blob = KVCodec().serialize({"a": "1", "b": "2"})
    pairs = list(deserialize_stream(io.BytesIO(blob)))
    assert pairs == [("a", "1"), ("b", "2")]


# --- serialize_stream ---

def test_serialize_stream_matches_base_format():
    """The streaming serializer must produce byte-identical output to the base."""
    original = {"name": "alice", "city": "NYC"}
    streamed = b"".join(serialize_stream(original.items()))
    assert streamed == KVCodec().serialize(original)


def test_serialize_stream_empty_input():
    streamed = b"".join(serialize_stream([]))
    assert streamed == b""


def test_serialize_stream_is_lazy():
    """Pulling one chunk should not consume the whole input iterable."""
    consumed = []

    def slow_source():
        for k, v in [("a", "1"), ("b", "2"), ("c", "3")]:
            consumed.append(k)
            yield (k, v)

    gen = serialize_stream(slow_source())
    next(gen)  # pull one chunk
    # We should NOT have consumed all three records to produce the first chunk.
    assert len(consumed) < 3


# --- Round trip through both ---

def test_stream_roundtrip():
    """serialize_stream + deserialize_stream cycle preserves data."""
    original = {f"key_{i}": f"value_{i}" for i in range(100)}
    blob = b"".join(serialize_stream(original.items()))
    decoded = dict(deserialize_stream(io.BytesIO(blob)))
    assert decoded == original


def test_stream_roundtrip_with_arbitrary_chars():
    original = {"with:colons": "and\nnewlines", "": "", "🔑": "値"}
    blob = b"".join(serialize_stream(original.items()))
    decoded = dict(deserialize_stream(io.BytesIO(blob)))
    assert decoded == original
