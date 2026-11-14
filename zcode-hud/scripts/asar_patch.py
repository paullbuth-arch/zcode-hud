"""Minimal ASAR patcher for zcode-hud.

The repack algorithm mirrors the MIT-licensed implementation in
ByteRax/zcode-token-usage-statusbar (patch_install.py); it rebuilds the archive
with a single entry replaced, updating offsets and per-file integrity hashes.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ALIGN = 4
BLOCK = 4194304


def read_header(stream):
    stream.seek(0)
    prefix, pickle_size, header_size, json_size = struct.unpack("<4I", stream.read(16))
    if prefix != 4:
        raise RuntimeError(f"unexpected asar pickle prefix {prefix}")
    header = json.loads(stream.read(json_size))
    return header, 8 + pickle_size


def iter_files(node, path=""):
    for name, child in node.get("files", {}).items():
        current = f"{path}/{name}"
        if "files" in child:
            yield from iter_files(child, current)
        else:
            yield current, child


def compute_integrity(data: bytes):
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(data).hexdigest(),
        "blockSize": BLOCK,
        "blocks": [
            hashlib.sha256(data[i:i + BLOCK]).hexdigest()
            for i in range(0, len(data), BLOCK)
        ],
    }


def entry_bytes(asar: Path, entry_path: str) -> bytes:
    with open(asar, "rb") as stream:
        header, base = read_header(stream)
        node = dict(iter_files(header)).get("/" + entry_path.strip("/"))
        if node is None:
            raise KeyError(f"entry not found: {entry_path}")
        stream.seek(base + int(node["offset"]))
        return stream.read(int(node["size"]))


def repack(src: Path, modify: dict, dst: Path) -> None:
    """Rebuild `src` into `dst`, replacing the given asar paths with new bytes."""
    with open(src, "rb") as stream:
        header, base = read_header(stream)
        header = json.loads(json.dumps(header))
        nodes = list(iter_files(header))
        known = {"/" + p.lstrip("/") for p, _ in nodes}
        missing = set(modify) - known
        if missing:
            raise RuntimeError(f"paths not in asar: {sorted(missing)}")

        plan = []
        offset = 0
        for path, node in nodes:
            if node.get("unpacked"):
                node["offset"] = "0"
                continue
            old_offset = int(node["offset"])
            if path in modify:
                data = modify[path]
                node["size"] = len(data)
                node["integrity"] = compute_integrity(data)
                plan.append((old_offset, len(data), data, False))
            else:
                plan.append((old_offset, int(node["size"]), None, True))
            node["offset"] = str(offset)
            offset += int(node["size"])

        header_bytes = json.dumps(
            header, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        json_size = len(header_bytes)
        padded = (json_size + 4 + ALIGN - 1) // ALIGN * ALIGN
        pickle_size = padded + 4

        with open(dst, "wb") as out:
            out.write(struct.pack("<4I", 4, pickle_size, padded, json_size))
            out.write(header_bytes)
            out.write(b"\0" * (padded - json_size - 4))
            assert out.tell() == 8 + pickle_size
            for old_offset, size, data, from_src in plan:
                if from_src:
                    stream.seek(base + old_offset)
                    remaining = size
                    while remaining > 0:
                        chunk = stream.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise RuntimeError("unexpected EOF while copying asar payload")
                        out.write(chunk)
                        remaining -= len(chunk)
                else:
                    out.write(data)
            out.flush()
