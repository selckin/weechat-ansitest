"""Decode a WeeChat logger line (logger.file.color_lines on: colors as ANSI)
into per-character gui states."""

from __future__ import annotations

import re

from . import split_id
from ..model import visible
from ..project import project
from ..sgr import runs



def message(log_line: str) -> str:
    """Message of a logger line "<time>\\t<prefix>\\t<message>"."""
    parts = log_line.split("\t", 2)
    return parts[2] if len(parts) == 3 else log_line


PRINT_ID = re.compile(r"(P\d{5}) ")


def decode_print(log_line: str) -> tuple[str, list[tuple[str, dict]]] | None:
    """(case ID, characters after "<id> " with their displayed color) for a
    logger line of a /print case."""
    chars = []
    for text, state in runs(message(log_line))[0]:
        projected = project(state, "print")
        chars.extend((char, projected) for char in visible(text))
    text = "".join(char for char, _ in chars)
    match = PRINT_ID.search(text)
    if not match:
        return None
    return match.group(1), chars[match.end():]


def decode_gui(log_line: str) -> tuple[str, list[tuple[str, dict]]] | None:
    """(case ID, characters after "<id> " with their gui state), None if the
    line has no case ID."""
    chars = []
    for text, state in runs(message(log_line))[0]:
        projected = project(state, "gui")
        chars.extend((char, projected) for char in visible(text))
    return split_id(chars)
