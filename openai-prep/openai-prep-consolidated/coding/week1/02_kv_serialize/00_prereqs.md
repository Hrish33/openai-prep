# Prereqs — KV Store Serialize / Deserialize

**Estimated time: 1.5–3 hours.** This problem has **no LeetCode primer** — it's not an algorithm question, it's a *Python internals + wire-protocol design* question. The prep is reading + a few small drills, not LC reps.

There are three things to nail before the base:

1. **Bytes vs strings** — the single most common source of bugs in this problem.
2. **Length-prefix encoding** — the technique. The whole problem is choosing this over delimiter-splitting and being able to defend that choice.
3. **Stream-style parsing** — consume N bytes, decode, repeat. The deserializer is a tiny state machine over a cursor.

The follow-up ladder pulls in two more (streaming + schema evolution), previewed at the end.

---

## Concept 1: Bytes vs strings in Python

**What you're learning:** the difference between `str` (a sequence of Unicode code points) and `bytes` (a sequence of raw 8-bit values), when each is the right tool, and why mixing them up is the dominant bug class in this problem.

**The mental model.** A `str` is *meaning* ("the character 'á'"). A `bytes` object is *transport* ("the two bytes `0xC3 0xA1` that happen to be UTF-8 for 'á'"). Serialization is the bridge: `str → bytes` is `.encode()`, `bytes → str` is `.decode()`. Pick an encoding and commit; **UTF-8 is the only sane default.**

```python
"á".encode("utf-8")          # b'\xc3\xa1'   — 2 bytes for 1 code point
b"\xc3\xa1".decode("utf-8")  # "á"           — 2 bytes round-trip to 1 char
len("á")                      # 1            — code points
len("á".encode("utf-8"))      # 2            — bytes
```

That `len` divergence is the killer. **Length-prefix encoding must count bytes, not characters.** A serializer that prefixes with `len(key)` and a deserializer that reads that many *bytes* will silently corrupt any non-ASCII key. This is *the* bug interviewers probe for.

**The four types you'll actually touch:**

| Type | Mutable? | What it holds | When |
|------|----------|---------------|------|
| `str` | no | Unicode code points | in-memory keys/values (user-facing) |
| `bytes` | no | raw 8-bit values | the serialized blob (wire/disk) |
| `bytearray` | **yes** | raw 8-bit values | building up the blob without O(n²) concatenation |
| `memoryview` | n/a (view) | window into the above | zero-copy slicing during parse (advanced) |

Use `bytearray` in the serializer (`buf = bytearray(); buf.extend(...); return bytes(buf)`). Use `bytes` in the deserializer's signature so callers know the input is immutable. `memoryview` is a follow-up if asked about avoiding copies on large blobs.

**Two stdlib helpers worth knowing cold:**

```python
import struct

struct.pack(">I", 1234)      # b'\x00\x00\x04\xd2'  — 4-byte big-endian uint
struct.unpack(">I", b"\x00\x00\x04\xd2")[0]   # 1234
```

`struct` is how you pack a fixed-width integer length header into bytes. `>I` is "big-endian, unsigned 32-bit." Network byte order (big-endian) is the convention; use it by default and you'll never have to think about endianness. The alternative is ASCII-decimal-plus-delimiter (`"5\n"`) — both are valid; know each (the **Two encoding shapes** section below covers when to pick which).

**Quick drill — find the bug:**

```python
def serialize_bad(d: dict[str, str]) -> bytes:
    out = b""
    for k, v in d.items():
        out += f"{len(k)}:{k}{len(v)}:{v}".encode("utf-8")
    return out
```

Three bugs. Spot them before reading on.

<details>
<summary>Answer</summary>

1. **`len(k)` counts code points, not bytes.** `serialize_bad({"á": "x"})` writes header `1` but `"á"` is 2 bytes — deserializer will read the wrong slice.
2. **The `:` delimiter inside the header is itself ambiguous** if a key happens to start with a digit run that looks like a length — but more importantly, there's no separator *between records*. After `"5:hello3:foo"`, where does the next record start? You need a strict "header *then* value, header *then* value" cursor, not delimiters in the middle.
3. **`out += ...` in a loop is O(n²)** because `bytes` is immutable; each `+=` allocates a new buffer. Use `bytearray` and `.extend()` (or accumulate to a list and `b"".join(...)`).

The right header counts **bytes**, the right framing is **header-then-payload with no inner delimiters**, the right builder is a **`bytearray`**.

</details>

**Done when:** you can state the difference between `str` and `bytes` in one sentence, know that `len()` differs across the boundary, and reach for `bytearray` automatically when building a blob.

---

## Concept 2: Length-prefix encoding

**What you're learning:** the technique. This is the entire problem. Every other approach is a trap.

**The 30-second pitch.** Before every variable-length payload, write a fixed-width count of how many bytes that payload occupies. The reader then reads the count, then reads exactly that many bytes, then moves on. **No delimiters anywhere.** Because the payload is bounded by an out-of-band count, it can contain *any byte sequence whatsoever* — including bytes that would otherwise be delimiters.

```
+---------+----------+----------+----------+
| len(k)  |    k     |  len(v)  |    v     |   ← one record
+---------+----------+----------+----------+
| 4 bytes | len(k) B | 4 bytes  | len(v) B |
```

For a dict of N records, you either prefix the whole blob with the count of records, or you let the reader stop at EOF. Both work; see the **Two encoding shapes** section below.

**Why delimiters lose.** Pick any byte to mean "end of key" and someone will put it inside a key. Escape it (`\` + the delimiter) and now `\` is the new delimiter and *you have to escape `\` too*. Now you have a parser with state machines for escape sequences, and you can corrupt data on a malformed escape. Length prefixes have **no inner state** — count, read, count, read. That simplicity is the whole point.

**Who uses this in the real world** (this is a real wire-protocol pattern, not a toy):

| System | Length-prefix shape |
|--------|---------------------|
| **Redis (RESP)** | ASCII-decimal header + `\r\n`, e.g. `$5\r\nhello\r\n`. Hybrid: human-readable header, raw payload. |
| **Protocol Buffers** | Varint length prefixes (variable-width count, smaller on average for small values). |
| **gRPC** | 5-byte header per message: 1 compression flag + 4-byte big-endian length. |
| **HTTP/2** | 24-bit length on every frame. |
| **MessagePack / CBOR** | Type-tagged length prefixes; same insight, more compact. |

Name-drop one of these in the interview ("this is the shape Redis's RESP uses") — it's the kind of detail that reads as senior because it grounds the answer in a real system.

**Two encoding shapes, both legitimate.** Know each; pick one for the base and have the other in your pocket.

**Shape A — fixed-width binary header (`struct.pack`).**

```
[4-byte LE/BE uint32: count of bytes][payload bytes...]
```

Pros: fixed cost (4 bytes) regardless of payload size, parser is one `struct.unpack` per header. Cons: 4-byte overhead even for tiny values; you've committed to a max payload size (`2**32 - 1` bytes for uint32). Use `>I` (big-endian, unsigned int).

**Shape B — ASCII-decimal header + a single-byte separator.**

```
[ASCII digits][b'\n'][payload bytes...]   e.g.  b"5\nhello"
```

Pros: human-readable when you `cat` the file, no max size, fewer bytes for small payloads (1 digit + 1 newline = 2 bytes vs 4). Cons: variable-width — parser has to `find(b'\n')` first, which is one extra step. Used by Redis RESP and HTTP/1.1's `Content-Length`-style headers.

**Decision rule under interview pressure:**

> "I'll use 4-byte big-endian binary length prefixes (`struct.pack('>I', n)`). It's the wire-protocol convention, the parser is one line, and 4 bytes per field is a fine tax. If you'd prefer something humans can `cat`, I'd switch to ASCII-decimal-plus-newline — Redis's RESP shape."

Saying this out loud — naming both shapes and committing to one — is the senior move. Picking one silently and hoping looks junior.

**Done when:** you can draw the byte layout for one record on paper, explain why a delimiter approach is strictly worse, and recite one real system that uses this pattern.

---

## Concept 3: Stream-style parsing — the cursor pattern

**What you're learning:** the deserializer. It's a tiny state machine over an integer cursor that advances through the blob.

**The shape:**

```python
def deserialize(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    i = 0
    while i < len(data):
        key_len = struct.unpack(">I", data[i:i+4])[0]
        i += 4
        key = data[i:i+key_len].decode("utf-8")
        i += key_len
        val_len = struct.unpack(">I", data[i:i+4])[0]
        i += 4
        val = data[i:i+val_len].decode("utf-8")
        i += val_len
        result[key] = val
    return result
```

That's it. The whole deserializer is "read 4 bytes for the header, read N bytes for the payload, advance the cursor, repeat until done." No regex, no `split`, no escape handling.

**Three things that matter about the shape:**

1. **The cursor is the state.** A single integer `i`. Every step advances it deterministically by `4 + key_len + 4 + val_len`. If something goes wrong, the cursor is in a bad place — usually a clear sign in tests.
2. **Termination by EOF (`while i < len(data)`).** You can also length-prefix the whole blob with a count of records. Both work — EOF-terminated is simpler for the base; count-prefixed is more robust against truncation (you know up front if bytes are missing).
3. **Bounds-checking is the validation surface.** A malformed blob shows up as either "`struct.unpack` didn't get 4 bytes" or "`data[i:i+key_len]` is shorter than expected." Decide your error policy — raise `ValueError` is the usual answer.

**Stretch: streaming from a file or socket.** The same cursor pattern, but instead of slicing `data[i:i+n]`, you `f.read(n)`. The interface flips from "consume a bytes blob" to "consume a stream of bytes lazily." This is follow-up #1 — keep the shape clean and the streaming variant is a 10-line change. Bake the design now.

```python
def deserialize_stream(stream) -> Iterator[tuple[str, str]]:
    while True:
        header = stream.read(4)
        if not header:           # clean EOF between records
            return
        if len(header) < 4:
            raise ValueError("truncated header")
        key_len = struct.unpack(">I", header)[0]
        key = stream.read(key_len).decode("utf-8")
        # ... same for value ...
        yield key, value
```

A *generator* is the right return type for streaming — you don't materialize the whole dict, the caller drives the pace with `next()`. This connects to week 2 (iterators) — flag it during the interview as "this generalizes to a generator if you want to stream from a file."

**Done when:** you can write the cursor-pattern deserializer from a blank screen in under 5 minutes, and articulate where it would change to support streaming.

---

## Concept 4 (preview): schema evolution — read, don't drill

**What you're learning:** *just enough* to engage the schema-evolution follow-up without freezing. You won't implement this in the base.

The format you wrote above is **schema-less** — every record is `(key, value)` and there's no concept of a "field type" or "version." That's fine until the interviewer asks one of:

- **"What if values can be `int` or `bool` too, not just strings?"** → Add a type tag byte before each value. `0x00 = str, 0x01 = int, 0x02 = bool, 0x03 = bytes`. The reader switches on the tag.
- **"What if we add a new field in v2 and old readers see a v2 blob?"** → Add a 4-byte version header to the whole blob. v1 readers refuse versions > 1. v2 readers know which fields are optional. This is the **Protocol Buffers / Avro** problem; both solve it with field numbers and "skip unknown" semantics.
- **"What if we want to add a field without breaking old data on disk?"** → Forward/backward compatibility. Old readers must skip unknown fields without crashing — which means **every field needs a length prefix** so an unknown field can be skipped by reading-and-discarding its bytes. (Length prefixes again — they're load-bearing for evolution, not just for delimiters.)

You don't need to write any of this. You need to be able to *say*: "Versioning gets a header byte at the top, type tags get a byte per value, schema evolution needs every unknown field skippable — which is why protobuf length-prefixes every field, not just variable-length ones."

**Done when:** you can recite that paragraph in two sentences.

---

## Suggested schedule

| Day | What |
|-----|------|
| Day 1 | Read Concept 1 (bytes vs strings). Open a Python REPL: encode/decode UTF-8 strings, observe the `len` divergence, pack/unpack an int with `struct`. 30 min. |
| Day 2 | Read Concepts 2 and 3. Sketch the byte layout for `{"a": "1", "bb": "22"}` on paper. Then implement `serialize` and `deserialize` from scratch in a scratch file, not the solution file. 60 min. |
| Day 3 | Read Concept 4 preview. Open `problem.md`. Attempt `solution.py` cold on a 30-min timer. Run `test_solution.py`. Then read `interviewer_notes.md` and pick one follow-up (streaming with a generator is the highest-value). |

There's no LeetCode grind here. This is a "internalize the technique, then implement it cleanly" problem — most of the prep is mental, not muscle.

## When you're ready

When you can draw the byte layout for one record on a whiteboard, write the `struct.pack('>I', ...)` line from memory, and explain in one sentence why delimiter-splitting fails — open `problem.md` and start a 30-minute timer.
