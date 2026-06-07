# Problem 2: KV Store Serialize / Deserialize

**Prereqs:** Work through `00_prereqs.md` first — especially Concept 1 (bytes vs strings) and Concept 2 (length-prefix encoding). Don't attempt this cold; the bytes-vs-chars trap will get you.

**Time budget:** 30 minutes for the base. The base is short; spend the remainder of a 45-60 min round on the follow-up ladder, where the real signal is.
**Source:** [HelloInterview community report](https://www.hellointerview.com/community/questions/kv-serialize-deserialize/cm6xw6unw00003b6qz67bpfaj).

## Problem

Design a serializer and deserializer for an in-memory key-value store. Both keys and values are arbitrary strings that may contain **any character whatsoever** — including newlines, colons, control bytes, non-ASCII, and the empty string. The output is a `bytes` blob you could write to disk or send over a socket; the deserializer reconstructs the original `dict` exactly.

```python
codec = KVCodec()

data = codec.serialize({"name": "alice", "city": "NYC"})
# data is bytes, opaque format

codec.deserialize(data)
# {"name": "alice", "city": "NYC"}

# The hard cases — must round-trip cleanly:
codec.deserialize(codec.serialize({"with:colons": "and\nnewlines"}))
# {"with:colons": "and\nnewlines"}

codec.deserialize(codec.serialize({"": "empty key"}))
# {"": "empty key"}

codec.deserialize(codec.serialize({"unicode_🔑": "値"}))
# {"unicode_🔑": "値"}

codec.deserialize(codec.serialize({}))
# {}
```

## Required API

- `serialize(kv: dict[str, str]) -> bytes` — encode a dict into a self-describing byte blob.
- `deserialize(data: bytes) -> dict[str, str]` — decode a blob produced by `serialize` back to the original dict.

The format you choose is *your* design decision — it's a major part of what's being evaluated. The contract is "round-trip is exact for any string."

## Requirements

- **Round-trip is exact for any string.** Keys and values are arbitrary `str` — including empty strings, strings containing the delimiter you'd reach for first, ASCII control bytes, full UTF-8 including emoji and combining characters. The serializer must not corrupt any of them.
- **No `pickle`, no `json`, no `eval`.** This is the *point* of the problem — designing a wire format. `json.dumps`/`json.loads` works but ducks the question; an interviewer will reject it and ask you to do it from scratch. `pickle` is a security hole (arbitrary code execution on load) and is the wrong tool. State this up front; don't get caught.
- **The format is self-describing.** Given only the bytes, the deserializer reconstructs the dict. No external schema, no out-of-band length, no "you also need to know N records."
- **Byte counts, not character counts.** Length prefixes must count UTF-8 bytes, not code points. This is the single most-tested boundary in this problem (see prereqs Concept 1).
- **`serialize` is O(total bytes).** No quadratic concatenation — build with `bytearray` or `b"".join`.
- **`deserialize` is O(total bytes).** Single pass with a cursor; no regex or `split` over the whole blob.

## Constraints

- Keys are unique within the input dict (Python `dict` invariant — you don't have to deduplicate).
- Encoding is **UTF-8.** Commit to it; mention it in your format.
- Empty dict serializes to a deterministic, non-empty (or empty — your call) byte blob that round-trips.
- Malformed input to `deserialize` (truncated, garbage bytes, header claims more bytes than remain) should **raise `ValueError`.** Silently returning a partial dict is the worse failure mode.
- Maximum payload size: pick one and state it. `2**32 - 1` bytes per field (the natural limit of a 4-byte length header) is the normal answer.

## What an OpenAI interviewer is looking for

The base is small. The differentiation is **how deliberately you design the format and how cleanly you articulate the trade-offs.** They're watching:

1. **Did you reject the easy wrong answers, out loud?** Saying "I'm not going to use a delimiter because keys can contain anything; I'm not going to use `json` because that ducks the question; I'm not going to use `pickle` because it's a security hole" *before* you start coding shows you understood the question. Silently picking length-prefixes looks like you got lucky.
2. **Bytes vs strings — handled deliberately.** Where does `.encode("utf-8")` happen? Where does `len()` count *bytes* vs *code points*? Reaching for `bytearray` to build, `bytes` for the return type, `.decode("utf-8")` on the way out — these should be conscious, not accidental.
3. **The format on a napkin.** Before coding, sketch the byte layout: `[4-byte big-endian key length][key bytes][4-byte big-endian value length][value bytes]` per record. Stating this out loud is worth more than 10 minutes of clean code.
4. **Real-world anchor.** Reference one wire protocol that does this — RESP (Redis), gRPC (5-byte header), protobuf varints. Grounding your design in something real reads as senior.
5. **Layered optimization under follow-up.** Streaming from a file, type-aware values, schema versioning, compression, cross-language. The follow-up ladder is where this round actually decides — see below.
6. **Edge-case discipline up front.** Name these *before* coding: empty dict, empty key, empty value, key containing your would-be delimiter, multi-byte UTF-8, truncated blob.

## Follow-ups (don't peek until the base works)

<details>
<summary>Click to expand — this is where the round is decided</summary>

Roughly in the order an interviewer escalates. Rungs 1-3 are the natural extensions of the wire format; 4-6 are the broader system-design rungs.

1. **Streaming deserialization with a generator.** The blob may be 10 GB and you can't load it into memory. Change `deserialize(data: bytes)` to consume from a file-like or socket-like stream and `yield (key, value)` pairs one at a time. (This is the bridge to week 2 — iterators and `yield`. Get the cursor-pattern parser clean now and this is a 15-line change.)
2. **Non-string values: type-tagged encoding.** Values can be `str`, `int`, `bool`, `bytes`, or `None`. Add a 1-byte type tag before each value's length prefix. The reader switches on the tag. What about nested dicts? (Recursion: type tag `0x05 = dict`, length prefix = total bytes of the encoded sub-dict.)
3. **Schema evolution / versioning.** v2 of the format adds a feature. Old readers see v2 blobs — what happens? Add a 1-byte version header at the top. Old readers reject `version > known`. This is the **protobuf** insight: length-prefix every field so an unknown field can be skipped without parsing it. Discuss "forward vs backward compatibility" explicitly.
4. **Compression.** Wrap the payload in `gzip` / `zstd`. Where does the compression boundary go? (Per-record? Per-blob? Per-block of N records?) Trade-off: random access vs compression ratio. Real systems (LevelDB, Parquet) chunk into blocks specifically for this.
5. **Cross-language consumers.** A Go process needs to read what your Python writes. Big-endian is critical (you already used it — good); UTF-8 is critical; and now you need a *spec document*, not just code. This is the moment to mention **protobuf, MessagePack, CBOR** — formats designed for this — and the trade-off (writing your own = control + zero dependencies; using protobuf = battle-tested + tooling).
6. **Integrity: detect corruption.** Add a 4-byte CRC32 at the end of the blob (or per-record). Mention that crypto-grade integrity (signed blobs) is a separate concern from corruption detection; pick the right tool for the threat model. (`hashlib.sha256` for tamper resistance, `zlib.crc32` for "did the disk flip a bit.")

</details>

<details>
<summary>More follow-ups — deeper extensions</summary>

**Python-internals depth**
- **Implement as a generator from the start.** Make `serialize` accept `Iterable[tuple[str, str]]` and itself `yield` bytes chunks — never materialize the whole blob. This generalizes to `serialize(d.items())` for dicts but also handles "stream of records that doesn't fit in memory."
- **`__iter__` on the deserializer.** Make the streaming deserializer a class with `__iter__` / `__next__`, not a function — gives `set_state` / `get_state` hooks for the resumable iterator (problem 4) pattern.
- **Memory: `memoryview` over the blob.** Avoid the O(N) copy in `data[i:i+n]` — use `memoryview(data)[i:i+n].tobytes()` (or just feed the memoryview to `.decode()`).

**Format design**
- **Varint length prefixes.** Protobuf's trick: a length under 128 is one byte, under 16384 is two, etc. Smaller blobs at the cost of a slightly more complex reader. When is this worth it? (Small values dominate; bandwidth/storage matters.)
- **Length-prefix the *whole* blob with a record count.** Lets the reader pre-size a dict and detect truncation up front, vs the EOF-terminated version that only detects truncation mid-record. Trade-off: the serializer now has to know the count up front (incompatible with the streaming serializer above).
- **Symmetric vs asymmetric encoding.** Should the serializer emit *the exact same bytes* for the same input every time? (Determinism matters for caching, content-addressing, hashing.) `dict` iteration order is insertion order in Python 3.7+ — note it; the format inherits that ordering unless you sort.

**Operational**
- **Append-only log.** Writes append records to a file; reads scan from the start. This is the building block of LSM-tree storage engines (LevelDB, RocksDB). What changes? (Reads need an in-memory index, or you re-scan; deletes need tombstones.)
- **Backward-compatible reader for forward-compatible writers.** v3 of the format adds a new field. v2 readers must skip it cleanly. This is the **"why every field needs a length prefix"** argument made concrete.
- **Atomic writes.** If the process crashes mid-write, the file is truncated mid-record. Detection (CRC, length-prefix-whole-blob) vs recovery (write to a tempfile, `fsync`, rename — the POSIX atomic-rename pattern). Mention `fsync` explicitly.

**Security**
- **Untrusted input.** A malicious blob with a header claiming `2**32 - 1` bytes of value will cause your deserializer to allocate 4 GB. Cap the per-field size *before* allocating. This is the same class of bug as XML entity expansion / billion-laughs.
- **Why not `pickle`.** Required answer: pickle executes arbitrary code on load (`__reduce__`). Even on trusted input, pickle's compatibility across Python versions is fragile. Wire format = bytes + spec; pickle = "Python implementation detail."

</details>

## Evidence (checked 2026-06-04)

Where the follow-up tiers above come from, graded by source quality:

- **The question itself is confirmed at OpenAI** — [HelloInterview community page](https://www.hellointerview.com/community/questions/kv-serialize-deserialize/cm6xw6unw00003b6qz67bpfaj), built from real candidate reports. It's also on HelloInterview's [OpenAI coding questions list](https://www.hellointerview.com/blog/openai-coding-questions), the same list confirming all 8 problems in this repo.
- **Length-prefix encoding as the expected answer** — implicit in the question (it's the *only* way to handle arbitrary characters without escape sequences) and confirmed by the dominant pattern in real wire protocols (RESP, gRPC, protobuf, HTTP/2). High trust.
- **Streaming with a generator (#1)** — not directly attested for this problem, but OpenAI tests `__iter__` / `__anext__` heavily in Problem 4 (resumable iterator) in the same loop. High plausibility as a cross-over.
- **Schema evolution (#3)** — not directly attested; included as the natural protobuf-shaped escalation that an interviewer with backend experience will reach for. Medium plausibility.
- **Compression, cross-language, CRC (#4-6)** — not specifically attested; standard system-design rungs that follow once the wire format is solid. Treat as a prep bank, not a script.

**Bottom line:** the question is confirmed; the specific follow-up sequence is not enumerated by any credible source. Prep the *technique* (length-prefix encoding cleanly, then the three escalation themes: streaming, evolution, integrity) and you can field whatever shape the interviewer takes.

## Honest difficulty note

This is the **shortest** problem in the set by lines of code — the reference base is ~25 lines for `serialize` + `deserialize`. **Do not let that fool you.** The signal is concentrated in three places: (a) how cleanly you reject the wrong-shape answers (`json`, `pickle`, delimiters) up front; (b) how deliberately you handle the bytes-vs-chars boundary; and (c) how far you can climb the follow-up ladder. A polished base that you "luck into" without articulation is a weak performance; a slightly-rougher base with a clear "here's why I picked this shape, here's where it would break under streaming, here's how versioning would fold in" is strong.

Treat the 30-minute base as a warm-up — your prep time goes into the follow-ups.
