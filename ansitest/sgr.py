"""Escape sequence tokenizer and reference SGR model (ECMA-48 / xterm).

Model choices where the standard says nothing (they follow WeeChat's
intended behavior, see the design spec): RGB components are clamped to
0-255, parameter values above 65535 are ignored, a palette index above 255
is ignored but consumed, an unknown or incomplete color type consumes the
remaining parameters.
"""

from __future__ import annotations

import re

from .model import RESET, State, visible

# DEL is ignored anywhere inside a control sequence (ECMA-48, DEC parser).
_CSI = re.compile(r"\x1b\[([\x30-\x3f\x7f]*)([\x20-\x2f\x7f]*)([\x40-\x7e])")
# A CSI without final byte, cancelled by ESC or by the end of the text: a
# terminal shows nothing of it.
_CSI_INCOMPLETE = re.compile(r"\x1b\[[\x30-\x3f\x7f]*[\x20-\x2f\x7f]*(?=\x1b|$)")
# OSC, DCS, SOS, PM, APC: end at BEL, at ST (ESC \), before any other ESC,
# or at the end of the text.
_STRING = re.compile(r"\x1b[\]PX^_].*?(?:\x07|\x1b\\|(?=\x1b)|$)", re.S)
# An escape sequence without its final byte (a lone ESC, or "\e(" before a
# multibyte char) is removed, and the char after it is kept. DEL is ignored
# among the intermediate bytes.
_ESCAPE = re.compile(r"\x1b[\x20-\x2f\x7f]*[\x30-\x7e]?")
_DIGITS = re.compile(r"\d*")
_ESC_DEL = re.compile(r"\x1b\x7f+")

_INVALID = object()


def tokens(text: str) -> list[tuple]:
    """Split text into tokens: ("text", str), ("csi", params, intermediates,
    final), ("incomplete", raw), ("string", raw) and ("escape", raw) (a
    lone ESC is an escape without final byte)."""
    # DEL is ignored in escape sequences, also right after ESC.
    text = _ESC_DEL.sub("\x1b", text)
    result = []
    i = 0
    length = len(text)
    while i < length:
        j = text.find("\x1b", i)
        if j < 0:
            j = length
        if j > i:
            result.append(("text", text[i:j]))
        if j >= length:
            break
        match = _CSI.match(text, j)
        if match:
            result.append(("csi", match.group(1).replace("\x7f", ""),
                           match.group(2).replace("\x7f", ""), match.group(3)))
            i = match.end()
            continue
        match = _CSI_INCOMPLETE.match(text, j)
        if match:
            result.append(("incomplete", match.group(0)))
            i = match.end()
            continue
        match = _STRING.match(text, j)
        if match:
            result.append(("string", match.group(0)))
            i = match.end()
            continue
        match = _ESCAPE.match(text, j)
        result.append(("escape", match.group(0).replace("\x7f", "")))
        i = match.end()
    return result


def is_sgr(params: str, intermediates: str, final: str) -> bool:
    return (final == "m" and not intermediates
            and all(char in "0123456789:;" for char in params))


def _value(item: str) -> int | None:
    """Value of a parameter: empty is 0; sub-parameters after ":" are
    ignored; None if not a number or greater than 65535."""
    head = item.split(":", 1)[0]
    if head == "":
        return 0
    if not head.isdigit():
        return None
    value = int(head)
    return value if value <= 65535 else None


def _component(item: str) -> int:
    """RGB component: leading digits (none is 0), clamped to 255."""
    digits = _DIGITS.match(item).group(0)
    return min(int(digits or "0"), 255)


def _rgb(red: str, green: str, blue: str) -> str:
    return "#%02x%02x%02x" % (_component(red), _component(green), _component(blue))


def _color_from_subs(subs: list[str]):
    """Color of "38:5:N", "38:2:R:G:B" or "38:2:<color space>:R:G:B"."""
    kind = _value(subs[1]) if len(subs) >= 2 else None
    if kind == 2 and len(subs) >= 5:
        return _rgb(*subs[3:6]) if len(subs) >= 6 else _rgb(*subs[2:5])
    if kind == 5 and len(subs) >= 3:
        index = _value(subs[2])
        return index if index is not None and index <= 255 else _INVALID
    return _INVALID


def _color_from_items(items: list[str], i: int):
    """Color after items[i] (38/48/58): "5;N" or "2;R;G;B".

    Return (color, index of the last item used)."""
    kind = _value(items[i + 1]) if i + 1 < len(items) else None
    if kind == 2 and i + 4 < len(items):
        return _rgb(items[i + 2], items[i + 3], items[i + 4]), i + 4
    if kind == 5 and i + 2 < len(items):
        index = _value(items[i + 2])
        return (index if index is not None and index <= 255 else _INVALID), i + 2
    return _INVALID, len(items) - 1


_ON = {1: "bold", 2: "dim", 3: "italic", 5: "blink", 6: "blink", 7: "reverse",
       9: "strike", 21: "underline"}
_OFF = {23: ("italic",), 24: ("underline",), 25: ("blink",), 27: ("reverse",),
        29: ("strike",), 22: ("bold", "dim")}


def apply_sgr(state: State, params: str) -> State:
    """Apply the parameters of one SGR sequence (text between "\\e[" and "m")."""
    items = params.split(";")
    i = 0
    while i < len(items):
        item = items[i]
        value = _value(item)
        subs = item.split(":") if ":" in item else None
        if value is None:
            pass
        elif value == 0:
            state = RESET
        elif value == 4:
            off = subs is not None and len(subs) >= 2 and subs[1].strip("0") == ""
            state = state.set(underline=not off)
        elif value in _ON:
            state = state.set(**{_ON[value]: True})
        elif value in _OFF:
            state = state.set(**{name: False for name in _OFF[value]})
        elif 30 <= value <= 37:
            state = state.set(fg=value - 30)
        elif value == 39:
            state = state.set(fg=None)
        elif 40 <= value <= 47:
            state = state.set(bg=value - 40)
        elif value == 49:
            state = state.set(bg=None)
        elif 90 <= value <= 97:
            state = state.set(fg=value - 90 + 8)
        elif 100 <= value <= 107:
            state = state.set(bg=value - 100 + 8)
        elif value in (38, 48, 58):
            if subs is not None:
                color = _color_from_subs(subs)
            else:
                color, i = _color_from_items(items, i)
            if color is not _INVALID and value == 38:
                state = state.set(fg=color)
            elif color is not _INVALID and value == 48:
                state = state.set(bg=color)
        i += 1
    return state


def runs(text: str, state: State = RESET) -> tuple[list[tuple[str, State]], State]:
    """Text runs of `text` with the state that applies to each, and the
    state at the end. Only SGR sequences change the state."""
    result: list[tuple[str, State]] = []
    for token in tokens(text):
        if token[0] == "text":
            if result and result[-1][1] == state:
                result[-1] = (result[-1][0] + token[1], state)
            else:
                result.append((token[1], state))
        elif token[0] == "csi" and is_sgr(*token[1:]):
            state = apply_sgr(state, token[1])
    return result, state


def plain(text: str) -> str:
    """Visible text: escape sequences, C0 controls and DEL removed."""
    return visible("".join(run for run, _ in runs(text)[0]))
