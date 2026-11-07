"""Decode a buffer line as WeeChat stores it into per-character gui states.

Only the color codes that WeeChat's ANSI decoder (gui_color_decode_ansi)
writes are accepted, read the way the curses display reads them
(src/gui/curses/gui-curses-window.c):

- \\x19F[flags]NN       foreground, basic WeeChat color NN (00-16)
- \\x19F@[flags]NNNNN   foreground, terminal color NNNNN
- \\x19BNN, \\x19B@NNNNN background
- \\x1aA, \\x1bA         set, remove attribute A (\\x01-\\x06)
- \\x1c                 reset colors and attributes

Flags: "|" keeps the attributes (without it, a foreground color removes
them); "*", ".", "/", "_", "!", "%" set bold, dim, italic, underline,
reverse, blink. Anything else that starts with a code byte (\\x19-\\x1c) is
not something the ANSI decoder should store: it is shown as
"<unexpected ...>" in the text, so the case fails with the bytes visible.

The line is read as bytes, like WeeChat, so a multibyte character after a
code cannot be taken for part of the code. The display is modeled for a
terminal with 16 colors or more, with weechat.look.color_real_white on.
"""

from __future__ import annotations

import re

from . import split_id
from ..model import State, visible
from ..project import project

RAW_MARKER = "ANSITEST-RAW "

# gui_weechat_colors (src/gui/curses/gui-curses-color.c): WeeChat color numbers.
BASIC = ("default", "black", "darkgray", "red", "lightred", "green", "lightgreen",
         "brown", "yellow", "blue", "lightblue", "magenta", "lightmagenta", "cyan",
         "lightcyan", "gray", "white")
# gui_color_ansi (src/gui/gui-color.c): ANSI colors 0-15.
ANSI = ("black", "red", "green", "brown", "blue", "magenta", "cyan", "gray",
        "darkgray", "lightred", "lightgreen", "yellow", "lightblue", "lightmagenta",
        "lightcyan", "white")
# GUI_COLOR_ATTR_*_CHAR (after \x1a and \x1b).
ATTR_BYTES = {1: "bold", 2: "reverse", 3: "italic", 4: "underline", 5: "blink", 6: "dim"}
# GUI_COLOR_EXTENDED_*_CHAR (flags in a color code); "|" keeps the attributes.
FLAG_BYTES = {ord("%"): "blink", ord("."): "dim", ord("*"): "bold", ord("!"): "reverse",
              ord("/"): "italic", ord("_"): "underline"}
ATTRS = ("bold", "dim", "italic", "underline", "blink", "reverse")
CODE_BYTES = b"\x19\x1a\x1b\x1c"

_FG_EXTENDED = re.compile(rb"\x19F@([%.*!/_|]*)([0-9]{5})")
_FG_BASIC = re.compile(rb"\x19F([%.*!/_|]*)([0-9]{2})")
_BG_EXTENDED = re.compile(rb"\x19B@([0-9]{5})")
_BG_BASIC = re.compile(rb"\x19B([0-9]{2})")
_ATTR = re.compile(rb"([\x1a\x1b])([\x01-\x06])")


def _initial() -> dict:
    return project(State(), "gui")


def _basic(number: int):
    name = BASIC[number]
    return None if name == "default" else ANSI.index(name)


def _apply_fg(state: dict, flags: bytes, color) -> None:
    """Foreground color with flags: the flagged attributes are set, the
    others are removed unless "|" is there (gui_window_set_custom_color_fg)."""
    keep = ord("|") in flags
    wanted = {FLAG_BYTES[flag] for flag in flags if flag in FLAG_BYTES}
    for attr in ATTRS:
        if attr in wanted:
            state[attr] = True
        elif not keep:
            state[attr] = False
    state["fg"] = color


def _unexpected(data: bytes, i: int) -> str:
    shown = data[i:i + 8].decode("utf-8", "backslashreplace")
    shown = "".join(f"\\x{ord(char):02x}" if ord(char) < 0x20 else char for char in shown)
    return f"<unexpected {shown}>"


def decode_weechat_chars(message) -> list[tuple[str, dict]]:
    """Characters of a stored line with their gui state (message: bytes, or
    str decoded with surrogateescape)."""
    data = message if isinstance(message, bytes) else message.encode("utf-8", "surrogateescape")
    state = _initial()
    chars: list[tuple[str, dict]] = []
    text = bytearray()

    def flush() -> None:
        snapshot = dict(state)
        chars.extend((char, snapshot)
                     for char in visible(bytes(text).decode("utf-8", "surrogateescape")))
        text.clear()

    i = 0
    while i < len(data):
        if data[i] not in CODE_BYTES:
            text.append(data[i])
            i += 1
            continue
        flush()
        if data[i] == 0x1c:
            state = _initial()
            i += 1
            continue
        if (match := _FG_EXTENDED.match(data, i)):
            _apply_fg(state, match.group(1), int(match.group(2)))
        elif (match := _FG_BASIC.match(data, i)) and int(match.group(2)) < len(BASIC):
            _apply_fg(state, match.group(1), _basic(int(match.group(2))))
        elif (match := _BG_EXTENDED.match(data, i)):
            state["bg"] = int(match.group(1))
        elif (match := _BG_BASIC.match(data, i)) and int(match.group(1)) < len(BASIC):
            state["bg"] = _basic(int(match.group(1)))
        elif (match := _ATTR.match(data, i)):
            state[ATTR_BYTES[match.group(2)[0]]] = match.group(1) == b"\x1a"
        else:
            snapshot = dict(state)
            chars.extend((char, snapshot) for char in _unexpected(data, i))
            i += 1
            continue
        i = match.end()
    flush()
    return chars


def decode_weechat(message) -> tuple[str, list[tuple[str, dict]]] | None:
    """(case ID, characters after "<id> " with their gui state), None if the
    message has no case ID."""
    return split_id(decode_weechat_chars(message))


def raw_message(log_line: str) -> bytes | None:
    """Bytes of the stored line in a logger line "... ANSITEST-RAW <hex>"
    written by the capture trigger, None if it is not such a line."""
    if RAW_MARKER not in log_line:
        return None
    hex_text = re.sub(r"\x1b\[[0-9;]*m", "", log_line.split(RAW_MARKER, 1)[1]).strip()
    try:
        return bytes.fromhex(hex_text)
    except ValueError:
        return None


def decode_raw_line(log_line: str) -> tuple[str, list[tuple[str, dict]]] | None:
    """Decode a logger line "... ANSITEST-RAW <hex of the raw message>"
    written by the capture trigger (see ansitest/capture/run.py)."""
    message = raw_message(log_line)
    return decode_weechat(message) if message is not None else None
