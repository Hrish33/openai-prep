"""
Tests for the KV codec.
Run: pytest coding/week1/02_kv_serialize/test_solution.py -v

If you wrote your own tests first (good!), compare against these afterward.
These cover the BASE problem only (dict[str, str] in memory).
Follow-ups (streaming, type tags, versioning) get their own tests when
you implement them — see interviewer_notes.md.
"""

import pytest
from solution import KVCodec


# --- Round-trip happy path ---

def test_roundtrip_single_entry():
    codec = KVCodec()
    data = codec.serialize({"name": "alice"})
    assert codec.deserialize(data) == {"name": "alice"}


def test_roundtrip_multiple_entries():
    codec = KVCodec()
    original = {"name": "alice", "city": "NYC", "lang": "python"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_serialize_returns_bytes():
    """The contract says bytes — not str. This catches the .encode-too-late bug."""
    codec = KVCodec()
    out = codec.serialize({"a": "b"})
    assert isinstance(out, bytes)


def test_empty_dict_roundtrips():
    codec = KVCodec()
    data = codec.serialize({})
    assert codec.deserialize(data) == {}


# --- The whole-point cases: arbitrary characters in keys/values ---

def test_value_contains_newline():
    codec = KVCodec()
    original = {"k": "line1\nline2"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_value_contains_colon():
    """Catches the 'I'll just split on colons' bug."""
    codec = KVCodec()
    original = {"k": "host:port"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_value_contains_every_ascii_byte():
    """All printable + control bytes that a delimiter scheme would trip on."""
    codec = KVCodec()
    payload = "".join(chr(b) for b in range(1, 128))  # skip null for str safety
    original = {"k": payload}
    assert codec.deserialize(codec.serialize(original)) == original


def test_key_contains_delimiter_characters():
    """Keys are arbitrary too — not just values."""
    codec = KVCodec()
    original = {"weird:key\nwith\tstuff": "value"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_empty_key():
    codec = KVCodec()
    original = {"": "value for empty key"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_empty_value():
    codec = KVCodec()
    original = {"key with empty value": ""}
    assert codec.deserialize(codec.serialize(original)) == original


def test_both_key_and_value_empty():
    codec = KVCodec()
    original = {"": ""}
    assert codec.deserialize(codec.serialize(original)) == original


# --- Unicode / multi-byte UTF-8 (the bytes-vs-chars trap) ---

def test_unicode_value():
    codec = KVCodec()
    original = {"greeting": "héllo wörld"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_emoji_in_key_and_value():
    """4-byte UTF-8. If your length prefix counted code points, this corrupts."""
    codec = KVCodec()
    original = {"🔑": "🌍"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_cjk_characters():
    """3-byte UTF-8."""
    codec = KVCodec()
    original = {"名前": "値", "city": "東京"}
    assert codec.deserialize(codec.serialize(original)) == original


def test_mixed_byte_widths():
    """ASCII + 2-byte + 3-byte + 4-byte UTF-8 in one record. Length count = bytes, not chars."""
    codec = KVCodec()
    original = {"a_é_中_🎉": "x_ñ_文_🚀"}
    assert codec.deserialize(codec.serialize(original)) == original


# --- Scale / boundaries ---

def test_large_value():
    codec = KVCodec()
    original = {"k": "x" * 100_000}
    assert codec.deserialize(codec.serialize(original)) == original


def test_many_entries():
    codec = KVCodec()
    original = {f"key_{i}": f"value_{i}" for i in range(1000)}
    assert codec.deserialize(codec.serialize(original)) == original


# --- Malformed input ---

def test_truncated_blob_raises():
    """A header claiming more bytes than remain must raise, not silently truncate."""
    codec = KVCodec()
    data = codec.serialize({"key": "value"})
    truncated = data[:-3]  # lop off some of the value bytes
    with pytest.raises(ValueError):
        codec.deserialize(truncated)


def test_truncated_header_raises():
    """Header itself is incomplete (fewer than 4 bytes)."""
    codec = KVCodec()
    data = codec.serialize({"key": "value"})
    truncated = data[:2]  # not even a full length prefix
    with pytest.raises(ValueError):
        codec.deserialize(truncated)


# --- Determinism / sequence properties ---

def test_serialize_is_deterministic_for_same_input():
    """Same dict, same input order → same bytes. Lets you cache, content-address."""
    codec = KVCodec()
    d = {"a": "1", "b": "2", "c": "3"}
    assert codec.serialize(d) == codec.serialize(d)


def test_double_roundtrip_is_stable():
    """serialize(deserialize(serialize(d))) == serialize(d). Format is idempotent."""
    codec = KVCodec()
    original = {"k1": "v1", "k2": "v2"}
    once = codec.serialize(original)
    twice = codec.serialize(codec.deserialize(once))
    assert once == twice


def test_problem_example_sequence():
    """Mirrors the example block in problem.md."""
    codec = KVCodec()
    assert codec.deserialize(codec.serialize({"name": "alice", "city": "NYC"})) == {
        "name": "alice",
        "city": "NYC",
    }
    assert codec.deserialize(codec.serialize({"with:colons": "and\nnewlines"})) == {
        "with:colons": "and\nnewlines"
    }
    assert codec.deserialize(codec.serialize({"": "empty key"})) == {"": "empty key"}
    assert codec.deserialize(codec.serialize({"unicode_🔑": "値"})) == {"unicode_🔑": "値"}
    assert codec.deserialize(codec.serialize({})) == {}
