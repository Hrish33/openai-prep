# Interviewer notes — KV Serialize / Deserialize

**Read AFTER your attempt.** Reading first defeats the point.

The base here is genuinely small — ~25 lines for `serialize` + `deserialize`. That's why **most of this doc is the design discussion and the follow-up ladder.** If you finished the base in 15 minutes, good; the differentiation comes from how cleanly you can articulate the format and engage the follow-ups.

## Reference solution (base — scrappy)

```python
import struct


class KVCodec:
    def serialize(self, kv: dict[str, str]) -> bytes:
        buf = bytearray()
        for key, value in kv.items():
            key_bytes = key.encode("utf-8")
            value_bytes = value.encode("utf-8")
            buf.extend(struct.pack(">I", len(key_bytes)))   # 4-byte big-endian uint
            buf.extend(key_bytes)
            buf.extend(struct.pack(">I", len(value_bytes)))
            buf.extend(value_bytes)
        return bytes(buf)

    def deserialize(self, data: bytes) -> dict[str, str]:
        result: dict[str, str] = {}
        i = 0
        n = len(data)
        while i < n:
            if i + 4 > n:
                raise ValueError("truncated key length header")
            (key_len,) = struct.unpack(">I", data[i:i+4])
            i += 4
            if i + key_len > n:
                raise ValueError("truncated key payload")
            key = data[i:i+key_len].decode("utf-8")
            i += key_len

            if i + 4 > n:
                raise ValueError("truncated value length header")
            (val_len,) = struct.unpack(">I", data[i:i+4])
            i += 4
            if i + val_len > n:
                raise ValueError("truncated value payload")
            value = data[i:i+val_len].decode("utf-8")
            i += val_len

            result[key] = value
        return result
```

That's the whole base. The shape is `[4-byte len][bytes]` repeated, EOF-terminated. Memorize three things: `struct.pack(">I", n)` for the header, `.encode("utf-8")` on the way in, the bounds check before every slice.

## Walking through the design choices

**Why 4-byte big-endian uint32 for the length prefix?**

| Choice | Reason |
|--------|--------|
| **4 bytes** | Caps payload size at ~4 GB, which is fine for in-memory KV. 2 bytes (65 KB cap) is too tight; 8 bytes is overkill for this use case. State the cap explicitly. |
| **Big-endian (`>I`)** | Network byte order. Cross-language consumers expect it. No real performance difference on modern CPUs. Convention is the whole reason. |
| **Unsigned (`I`, not `i`)** | A signed length is nonsense — payloads can't be -3 bytes long. Catches a class of bug at the type level. |

**Why `bytearray` to build, `bytes` to return?**
- `bytes` is immutable: `out += chunk` reallocates every step → O(n²) over the whole serialize.
- `bytearray` is mutable: `.extend(chunk)` is amortized O(1).
- `bytes(buf)` at the end is one O(n) copy. Worth it — callers want an immutable return type.
- Alternative: collect to a `list[bytes]` and `b"".join(parts)`. Also O(n), slightly more Pythonic, slightly more allocation. Either is fine; `bytearray` is the slimmer answer.

**Why `.encode("utf-8")` and `.decode("utf-8")` explicitly, not the defaults?**
- The defaults (`.encode()` is utf-8 in CPython) work but are implicit. Naming the encoding once in the function body documents the spec. The whole format depends on UTF-8 being the encoding; making it grep-able is cheap insurance against a future maintainer "fixing" it to `.encode("ascii")`.

**Why EOF-terminated, not record-count-prefixed?**
- EOF-terminated: simpler serializer (no need to know the count up front — works for streaming), simpler deserializer.
- Count-prefixed: lets the reader pre-size the dict and reject obvious truncation up front, but commits the serializer to materializing the whole dict before writing the first byte.
- **EOF-terminated is the right base.** The count-prefixed shape becomes relevant if you stream millions of records and want eager truncation detection. Either is defensible; name the trade-off.

## Why this format and not the obvious alternatives

| Approach | What goes wrong | Verdict |
|----------|-----------------|---------|
| `"key1=val1;key2=val2"` (delimiter) | Keys/values can contain `=` and `;`. | Wrong shape. |
| Same + escape sequences (`\=`, `\;`) | Now `\` is a delimiter, escape `\\`. Parser is a state machine. Errors silently corrupt. | Wrong shape. Don't go here. |
| `json.dumps(d)` | Works. But it ducks the question — the *point* is "design a wire format." | Mention it as an option, then reject it. |
| `pickle.dumps(d)` | Works. But pickle **executes arbitrary code on load** — security hole. And it's Python-only, fragile across versions. | Hard reject. Name it as a security hole. |
| Base64 the keys and values, join with `:` | Works! But ~33% overhead, and you've just punted to "delimiter on opaque tokens" — clever but not how real systems do it. | Acceptable hack; not the answer they want. |
| **Length-prefix encoding (chosen)** | Bytes-vs-chars trap is the only real risk. No escape handling. No max field size beyond the length-header's cap. Matches Redis/gRPC/protobuf. | Right shape. |

Walking through this table in the interview — naming each rejected option and *why* — is worth more than the lines of code that follow. It's the clearest signal that you understand the *problem space*, not just the answer.

## The one bug that silently passes some tests

```python
key_bytes = key.encode("utf-8")
buf.extend(struct.pack(">I", len(key)))    # BUG: len(key), not len(key_bytes)
buf.extend(key_bytes)
```

For ASCII keys, `len(key) == len(key_bytes)` and the test suite is green. The moment a key contains a non-ASCII character — `"héllo"` is 5 chars but 6 bytes — the header undercounts, and the deserializer reads 5 bytes instead of 6, mid-character. The resulting `.decode("utf-8")` either raises `UnicodeDecodeError` or returns a garbage string with the next field's first byte glued on.

This is **the** test in `test_solution.py` (`test_unicode_value`, `test_emoji_in_key_and_value`, `test_mixed_byte_widths`). If those pass, you've handled bytes-vs-chars correctly. If they fail with a `UnicodeDecodeError`, that's the bug.

## Honest weaknesses to acknowledge in interview

- **4 GB per-field cap.** A 32-bit length prefix can't address more. For a KV store that's fine; for a blob store you'd switch to 8-byte (`>Q`).
- **No integrity check.** A single bit-flip on disk silently corrupts the next field. Real formats add a CRC32 (per-record or per-blob). Mention it; the fix is one line of `zlib.crc32`.
- **No versioning.** v2 of the format breaks all existing readers. The fix is a 1-byte version header up front — see follow-up #3.
- **No type information.** Values are always `str`. Adding `int`/`bool`/`bytes`/`dict` requires a 1-byte type tag per value — see follow-up #2.
- **EOF-terminated means truncation detection is partial.** A blob that gets cut between records looks legal. A record-count header would catch this; trade-off is committing to materializing the count up front.
- **Reads the whole blob into memory.** Fine for the in-memory KV store. For 10 GB on disk, switch to the streaming generator — see follow-up #1.

## Grading yourself

| Axis | Passing |
|------|---------|
| Rejected wrong shapes out loud | Named delimiter, json, pickle, base64 and said why each is wrong **before** coding |
| Bytes vs chars handled deliberately | Length prefix counts `len(.encode("utf-8"))`, not `len(str)`; you said "bytes, not chars" out loud |
| Format choice justified | Named `struct.pack(">I", n)` and one real system that uses this shape (RESP, gRPC, protobuf) |
| Builder is not quadratic | `bytearray` + `extend`, or list + `b"".join` — not `out += chunk` in a loop |
| Deserializer is a cursor pattern | Single integer `i`, advancing deterministically; bounds-checked before every slice |
| Edge cases up front | Named: empty dict, empty key/value, multi-byte UTF-8, truncated blob — before coding |
| Follow-up readiness | Streaming, type tags, versioning don't make you freeze — you can sketch each |

A clean base alone is a **median** performance here. The differentiation is the follow-ups and the design articulation.

## Follow-up sketches

### 1. Streaming deserialization with a generator

The blob is 10 GB. You can't `data = f.read()`. Switch to a stream-driven parser that yields records lazily:

```python
def deserialize_stream(stream) -> Iterator[tuple[str, str]]:
    while True:
        header = stream.read(4)
        if not header:                          # clean EOF between records
            return
        if len(header) < 4:
            raise ValueError("truncated header")
        (key_len,) = struct.unpack(">I", header)

        key_bytes = stream.read(key_len)
        if len(key_bytes) < key_len:
            raise ValueError("truncated key")
        key = key_bytes.decode("utf-8")

        # ... same for value ...
        yield key, value
```

Two things to articulate when you write this:

1. **Why a generator, not a list.** Memory: the caller drives the pace and never materializes more than one record. Same shape as Python's `csv.reader`, `json.JSONDecoder.raw_decode` over a stream, `xml.etree.ElementTree.iterparse`. This is the *streaming-parser* pattern across the stdlib.
2. **Why the EOF policy lives in the reader, not the caller.** `read(4)` returning `b""` is the canonical signal for clean EOF. `read(4)` returning 1-3 bytes is unambiguously truncation. The reader encodes that — callers shouldn't have to.

(This is the bridge to **week 2, problem 4** — resumable iterators. If you find yourself wanting a `get_state` / `set_state` on this stream parser, you've discovered why that problem exists. Flag it.)

### 2. Non-string values: type-tagged encoding

Values can be `str`, `int`, `bool`, `bytes`, `None`, or a nested `dict`. Add a 1-byte type tag before each value's length prefix:

```
TAG = {0x00: str, 0x01: int, 0x02: bool, 0x03: bytes, 0x04: None, 0x05: dict}
```

```python
def encode_value(v) -> bytes:
    if isinstance(v, str):
        payload = v.encode("utf-8")
        return bytes([0x00]) + struct.pack(">I", len(payload)) + payload
    if isinstance(v, bool):                   # check BEFORE int — bool is an int subclass!
        return bytes([0x02]) + struct.pack(">I", 1) + (b"\x01" if v else b"\x00")
    if isinstance(v, int):
        payload = v.to_bytes((v.bit_length() + 8) // 8, "big", signed=True) or b"\x00"
        return bytes([0x01]) + struct.pack(">I", len(payload)) + payload
    if v is None:
        return bytes([0x04]) + struct.pack(">I", 0)
    if isinstance(v, bytes):
        return bytes([0x03]) + struct.pack(">I", len(v)) + v
    if isinstance(v, dict):
        sub = serialize(v)                    # recurse
        return bytes([0x05]) + struct.pack(">I", len(sub)) + sub
    raise TypeError(f"unsupported value type: {type(v).__name__}")
```

The two land mines, both worth saying out loud:

- **`bool` is a subclass of `int` in Python.** `isinstance(True, int)` is `True`. Check `bool` first or `True` encodes as int `1`. This is the dunder-depth trap interviewers love.
- **Recursion for `dict`** ties the format to itself — the sub-dict's bytes are just another payload with a length prefix. The whole "every field gets a length prefix" rule (see follow-up #3) is what makes this clean.

### 3. Schema evolution / versioning

v1 of your format is shipped. v2 adds a feature. Three rules:

1. **1-byte version header at the top of every blob.** v2 readers see `0x01` and dispatch to the v1 decoder. v1 readers see `0x02` and refuse (or skip — depends on your forward-compat policy).
2. **Every field gets a length prefix.** Not just variable-length ones — *every* field. This is the protobuf rule. The reason: a v1 reader encountering a v2-only field can read the length prefix and skip exactly that many bytes, with no knowledge of what the field actually means.
3. **No field is ever repurposed.** Add new field numbers; never re-use old ones for a different meaning. (Protobuf encodes this with field numbers; you can fake it with a `(tag_byte, length, payload)` triple per field.)

Forward vs backward compatibility, stated cleanly:
- **Backward compat:** new code reads old data. Easy — new fields are optional, default-filled if missing.
- **Forward compat:** old code reads new data. Hard — requires "skip unknown fields cleanly," which requires length-prefixing everything.

The protobuf insight ("length-prefix every field, even fixed-width ones, for forward compat") is the senior depth here. You don't have to implement it; you have to be able to say it.

### 4. Compression

Wrap the payload in `gzip` or `zstd`. Two questions to settle:

| Question | Answer |
|----------|--------|
| Compress per-record or per-blob? | Per-blob = better ratio (more repeated bytes to find). Per-record = random access without full decompress. |
| Where does the compression boundary live in the format? | A header byte: `0x00 = uncompressed, 0x01 = gzip, 0x02 = zstd`. Reader checks before decoding. |
| What about per-block compression? | Real systems (Parquet, LevelDB SSTables) chunk into ~64 KB blocks: compress each block, store offsets to each block, decompress only the block containing the queried key. This is the "ratio vs. random access" Pareto answer. |

Don't write the code — name the block-compression pattern and which real systems use it.

### 5. Cross-language consumers

A Go process reads what Python writes. What changes?

- **Big-endian is critical** — you already used it. State it explicitly: "I picked big-endian *because* of this case."
- **UTF-8 is critical** — Python and Go agree on UTF-8; this is automatic.
- **You now owe a spec doc**, not just code. The byte layout becomes the contract.
- **Field tags** (from #3) replace field positions — Go's struct field order must not matter for compatibility.

This is the moment to mention **protobuf, MessagePack, CBOR** by name: "If cross-language matters, I'd reach for protobuf instead of rolling our own. The trade-off is dependency surface vs. tooling — protobuf gives you `.proto` files, codegen, and `protoc --decode_raw` for debugging out of the box."

### 6. Integrity: CRC for corruption detection

A bit flip on disk silently corrupts the next field. Add a 4-byte CRC32 at the end of the blob (`zlib.crc32`). Reader recomputes and compares; mismatch raises.

Two scope-management points:
- **CRC catches corruption, not tampering.** A malicious party can recompute the CRC after editing. For tamper resistance, you want HMAC-SHA256 with a shared secret — a separate problem.
- **Per-record or per-blob?** Per-record costs 4 bytes overhead per record but pinpoints exactly which record corrupted. Per-blob is one check but tells you nothing about which record. Depends on whether you need partial recovery.

## Common mistakes interviewers see

1. **`len(key)` instead of `len(key.encode("utf-8"))`** — works on ASCII tests, silently corrupts unicode. The most-tested bug.
2. **`out += chunk` in a serialize loop** — O(n²) over the whole blob. Use `bytearray.extend` or `b"".join`.
3. **Forgetting the bounds check** — `data[i:i+key_len]` on a truncated blob silently returns a shorter slice (Python doesn't raise on slice out-of-bounds). Then `.decode("utf-8")` may or may not raise, depending on the bytes. Check `i + key_len > len(data)` before the slice.
4. **`bisect_left` style off-by-one in the cursor** — not from `bisect`, but from advancing `i` by the wrong amount (forgetting to add the 4 header bytes). The cursor pattern is "advance by 4 for the header, then advance by the payload length." Every step deterministic.
5. **Picking `json.dumps` and hoping** — ducks the question. The interviewer will reject it and ask you to do it from scratch. Reject `json` and `pickle` yourself, before they ask.
6. **`pickle.dumps` for "any value type"** — silently introduces an RCE on `pickle.loads(untrusted)`. Hard fail in any interview that touches the security axis.
7. **Storing the length prefix as text (`str(len)` + `\n`)** — works! It's the Redis RESP shape. But mixing the format makes the parser harder; binary length headers are the cleaner base. Know that the text-shaped version exists; pick binary unless asked.
8. **Returning `str` instead of `bytes` from `serialize`** — works for ASCII-only, breaks on any binary payload (compressed, CRC, type tag bytes). Commit to `bytes` from the start.

## Want a Round 2?

Once the base is solid, write the **streaming variant** as a separate file (`solution_stream.py`) with `serialize_stream` and `deserialize_stream` as generators. The base tests should still pass when wrapped, plus add a test that builds a 100k-record blob, deserializes it lazily, and asserts memory doesn't blow up (`tracemalloc` or just trust the generator semantics).

After that, bolt on type tags from follow-up #2 — that's where the "every field gets a length prefix" insight earns its keep. Those two follow-ups, *actually written* (not just described), are what move this from "I know the trick" to "I can design a wire format."
