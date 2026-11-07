"""Decoders of WeeChat's output into per-character states."""

from __future__ import annotations

import re

ID = re.compile(r"(T\d{5}) ")
ID_BYTES = re.compile(rb"(T\d{5}) ")


def split_id(chars: list[tuple[str, dict]]) -> tuple[str, list[tuple[str, dict]]] | None:
    """(case ID, characters after "<id> "), None if the text has no case ID."""
    text = "".join(char for char, _ in chars)
    match = ID.search(text)
    if not match:
        return None
    return match.group(1), chars[match.end():]


def split_id_bytes(data: bytes) -> tuple[str, bytes] | None:
    """(case ID, bytes after "<id> "), None if there is no case ID."""
    match = ID_BYTES.search(data)
    if not match:
        return None
    return match.group(1).decode(), data[match.end():]
