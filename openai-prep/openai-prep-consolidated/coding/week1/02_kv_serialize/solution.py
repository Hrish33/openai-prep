"""
KV store serialize / deserialize.

Read 00_prereqs.md (bytes vs strings + length-prefix encoding), then
problem.md. Sketch the byte layout for ONE record on paper before coding.

Suggested structure (you don't have to follow this — design what makes
sense to you):
  - Format: per record, [4-byte big-endian length][utf-8 key bytes]
    [4-byte big-endian length][utf-8 value bytes]. EOF-terminated.
  - serialize: bytearray() + struct.pack('>I', n) + .encode('utf-8').
    Return bytes(buf) at the end.
  - deserialize: a cursor i over data, struct.unpack('>I', ...) for
    each header, .decode('utf-8') for each payload.
  - Length prefixes count BYTES, not code points.

Do NOT use json, pickle, or eval. Designing the wire format IS the
problem.
"""

import struct  # noqa: F401  (you'll want this for the length headers)


class KVCodec:
    def serialize(self, kv: dict[str, str]) -> bytes:
        buffer = bytearray()
        for k, v in kv.items():
            encoded_key = k.encode("utf-8")
            buffer.extend(struct.pack('>I', len(encoded_key)))
            buffer.extend(encoded_key)
            encoded_value = v.encode("utf-8")
            buffer.extend(struct.pack('>I', len(encoded_value)))
            buffer.extend(encoded_value)
        return bytes(buffer)

    def deserialize(self, data: bytes) -> dict[str, str]:
        res = {}
        i = 0
        while i < len(data):
            if i + 4 > len(data):
                raise ValueError("truncated key length header")
            key_len = struct.unpack('>I', data[i:i + 4])[0]
            i += 4
            if i + key_len > len(data):
                raise ValueError("truncated key payload")
            key = data[i:i + key_len].decode("utf-8")
            i += key_len
            if i + 4 > len(data):
                raise ValueError("truncated value length header")
            value_len = struct.unpack('>I', data[i:i + 4])[0]
            i += 4
            if i + value_len > len(data):
                raise ValueError("truncated value payload")
            value = data[i:i + value_len].decode("utf-8")
            i += value_len
            res[key] = value
        return res


def main():
    codec = KVCodec()
    buffer = codec.serialize({"lol": "lolol", "lolol": "lolol"})
    output = codec.deserialize(buffer)
    print(output)



if __name__ == "__main__":
    main()
