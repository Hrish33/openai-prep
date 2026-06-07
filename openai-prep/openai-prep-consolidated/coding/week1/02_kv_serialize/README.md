# Problem 2: KV Store Serialize/Deserialize

**Status:** Scaffolded. Start with `00_prereqs.md`, then `problem.md`. Reference lives in `interviewer_notes.md` (read after your attempt).

**One-liner:** Implement serialization and deserialization for a key-value store where both keys and values can contain any characters including delimiters.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/kv-serialize-deserialize/cm6xw6unw00003b6qz67bpfaj)

**Key concept:** length-prefix encoding (the pattern Redis uses in its wire protocol)

**Likely prereqs:**
- Bytes vs strings in Python (`bytes`, `bytearray`, `.encode()`, `.decode()`)
- Stream-style parsing (consume N bytes, decode, repeat)
- No external LeetCode primer required — this is more about Python internals than algorithms

**When to do this:** after problem 1, week 1.
