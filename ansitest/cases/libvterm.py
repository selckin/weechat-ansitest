"""Cases imported from libvterm's tests (MIT, https://github.com/neovim/libvterm).

t/30state_pen.test and t/64screen_pen.test give "lvp" cases: each PUSH is
followed by a marker, whose expected state is the reference model's state
with the fields asserted by libvterm ("?pen bold = on") replaced by
libvterm's values. t/02parser.test gives "lvx" cases: the expected text is
the concatenation of the "text" events, the state is not checked.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..model import RESET, Case, marker, unique_key, visible
from ..sgr import runs

NAME = "libvterm"
PEN_FILES = ("30state_pen", "64screen_pen")
PARSER_FILE = "02parser"

_SIMPLE_ESCAPES = {"e": b"\x1b", "n": b"\n", "r": b"\r", "t": b"\t", "a": b"\x07"}
_PEN = re.compile(r"\?pen (\w+) = (.+)")
_BOOL_FIELDS = ("bold", "italic", "blink", "reverse", "strike")


def unescape(text: str) -> bytes:
    """Decode the string of a PUSH line: \\e, \\n, \\r, \\t, \\a, \\xHH,
    \\x{H...}; any other \\<char> is <char>."""
    out = bytearray()
    i = 0
    while i < len(text):
        char = text[i]
        if char != "\\":
            out += char.encode()
            i += 1
            continue
        escape = text[i + 1]
        if escape == "x" and text[i + 2] == "{":
            end = text.index("}", i)
            out.append(int(text[i + 3:end], 16))
            i = end + 1
        elif escape == "x":
            out.append(int(text[i + 2:i + 4], 16))
            i += 4
        else:
            out += _SIMPLE_ESCAPES.get(escape, escape.encode())
            i += 2
    return bytes(out)


@dataclass
class Section:
    name: str
    items: list = field(default_factory=list)  # ("push", bytes) or ("expect", str)


def parse(text: str) -> list[Section]:
    sections: list[Section] = []
    for line in text.split("\n"):
        if line.startswith("!"):
            sections.append(Section(line[1:].strip()))
        elif not sections:
            continue
        elif line.startswith("PUSH "):
            match = re.match(r'PUSH "(.*)"\s*$', line)
            sections[-1].items.append(("push", unescape(match.group(1))))
        elif line[:1].isspace() and line.strip():
            sections[-1].items.append(("expect", line.strip()))
    return sections


def _pen_color(value: str):
    if "is_default" in value:
        return None
    match = re.fullmatch(r"idx\((\d+)\)", value)
    if match:
        return int(match.group(1))
    match = re.fullmatch(r"rgb\((\d+),(\d+),(\d+)\)", value)
    if match:
        return "#%02x%02x%02x" % tuple(int(x) for x in match.groups())
    raise ValueError(f"unknown libvterm color: {value}")


def pen_assertion(expect: str) -> tuple[str, object] | None:
    """(State field, value) asserted by a "?pen" line, None if the line is
    not a pen assertion or the attribute is not in the model (font, small,
    baseline)."""
    match = _PEN.match(expect)
    if not match:
        return None
    name, value = match.group(1), match.group(2).strip()
    if name in _BOOL_FIELDS:
        return name, value == "on"
    if name == "underline":
        return "underline", value != "0"
    if name in ("foreground", "background"):
        return ("fg" if name == "foreground" else "bg"), _pen_color(value)
    return None


def pen_cases_from_text(text: str, stem: str) -> tuple[list[Case], list[tuple[str, int, str]]]:
    """Cases of a pen test file, and the places where libvterm's assertions
    differ from the reference model: (case key, push number, field)."""
    cases: list[Case] = []
    diffs: list[tuple[str, int, str]] = []
    seen: Counter = Counter()
    for section in parse(text):
        key = unique_key(f"lvp/{stem}/{section.name}", seen)
        model = RESET
        pushes = []  # [data, runs inside the push, expected state after the push]
        for kind, value in section.items:
            if kind == "push":
                push_runs, model = runs(value.decode("utf-8", "surrogateescape"), model)
                pushes.append([value, push_runs, model])
            elif pushes and (assertion := pen_assertion(value)):
                name, wanted = assertion
                if getattr(model, name) != wanted:
                    diffs.append((key, len(pushes), name))
                pushes[-1][2] = pushes[-1][2].set(**{name: wanted})
        if not pushes:
            continue
        payload = b""
        expect = []
        for index, (data, push_runs, state) in enumerate(pushes):
            payload += data
            expect.extend((visible(text_run), run_state) for text_run, run_state in push_runs
                          if visible(text_run))
            text_marker = marker(index)
            payload += text_marker.encode()
            expect.append((text_marker, state))
        cases.append(Case("lvp", key, f"libvterm {stem}: {section.name}", payload, expect))
    return cases, diffs


def _text_event(expect: str) -> str:
    match = re.fullmatch(r"text (.*)", expect)
    if not match:
        return ""
    return "".join(chr(int(value, 16)) for value in match.group(1).split(","))


def parser_cases_from_text(text: str) -> list[Case]:
    cases: list[Case] = []
    seen: Counter = Counter()
    for section in parse(text):
        payload = b"".join(value for kind, value in section.items if kind == "push")
        expected = visible("".join(_text_event(value) for kind, value in section.items
                                   if kind == "expect"))
        key = unique_key(f"lvx/{section.name}", seen)
        cases.append(Case("lvx", key, f"libvterm parser: {section.name}", payload,
                          [(expected, None)] if expected else []))
    return cases


def _read(corpora: Path, stem: str) -> str:
    return (corpora / "libvterm" / "t" / f"{stem}.test").read_text(encoding="utf-8")


def available(corpora: Path) -> bool:
    return all((corpora / "libvterm" / "t" / f"{stem}.test").exists()
               for stem in (*PEN_FILES, PARSER_FILE))


def cases(corpora: Path) -> list[Case]:
    result: list[Case] = []
    for stem in PEN_FILES:
        result += pen_cases_from_text(_read(corpora, stem), stem)[0]
    result += parser_cases_from_text(_read(corpora, PARSER_FILE))
    return result


def pen_diffs(corpora: Path) -> list[tuple[str, int, str]]:
    return [diff for stem in PEN_FILES
            for diff in pen_cases_from_text(_read(corpora, stem), stem)[1]]
