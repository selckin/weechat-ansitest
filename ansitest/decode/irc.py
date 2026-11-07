"""Decode an IRC message (IRC formatting codes, as in
https://modern.ircdocs.horse/formatting) into per-character irc states."""

from __future__ import annotations

import re

from . import split_id
from ..model import visible

_COLOR = re.compile(r"(\d{1,2})(?:,(\d{1,2}))?")
_HEX = re.compile(r"([0-9A-Fa-f]{6})(?:,([0-9A-Fa-f]{6}))?")
_TOGGLES = {"\x02": "bold", "\x1d": "italic", "\x1f": "underline", "\x16": "reverse",
            "\x1e": "strike"}


def irc_state(**changes) -> dict:
    """IRC state (default colors, no attribute) with the given changes."""
    state = {"fg": None, "bg": None, "bold": False, "italic": False, "underline": False,
             "reverse": False, "strike": False}
    state.update(changes)
    return state


def _irc_color(digits: str) -> int | None:
    number = int(digits)
    return None if number == 99 else number


def decode_irc_chars(message: str) -> list[tuple[str, dict]]:
    state = irc_state()
    chars = []
    i = 0
    while i < len(message):
        char = message[i]
        i += 1
        if char in _TOGGLES:
            state[_TOGGLES[char]] = not state[_TOGGLES[char]]
        elif char == "\x0f":
            state = irc_state()
        elif char == "\x03":
            match = _COLOR.match(message, i)
            if match:
                state["fg"] = _irc_color(match.group(1))
                if match.group(2) is not None:
                    state["bg"] = _irc_color(match.group(2))
                i = match.end()
            else:
                state["fg"] = state["bg"] = None
        elif char == "\x04":
            match = _HEX.match(message, i)
            if match:
                state["fg"] = "#" + match.group(1).lower()
                if match.group(2) is not None:
                    state["bg"] = "#" + match.group(2).lower()
                i = match.end()
            else:
                state["fg"] = state["bg"] = None
        elif visible(char):
            chars.append((char, dict(state)))
    return chars


def decode_irc(message: str) -> tuple[str, list[tuple[str, dict]]] | None:
    """(case ID, characters after "<id> " with their irc state), None if the
    message has no case ID."""
    chars = decode_irc_chars(message)
    return split_id(chars)
