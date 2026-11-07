"""Cases imported from chalk/ansi-regex fixtures (MIT,
https://github.com/chalk/ansi-regex): each code, prefixed with ESC, between
two markers. The expected state after the code comes from the reference
model (it changes only for SGR codes)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from ..model import RESET, Case, build_case, unique_key
from ..sgr import runs

NAME = "ansi-regex"
FILE = Path("ansi-regex") / "fixtures" / "ansi-codes.js"

_MAP = re.compile(r"export const (\w+) = new Map\(\[(.*?)\n\]\);", re.S)
_ENTRY = re.compile(r"\[\s*'((?:[^'\\]|\\.)*)'\s*,\s*\[\s*'((?:[^'\\]|\\.)*)'")
_JS_ESCAPE = re.compile(r"\\(u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)")


def js_unescape(text: str) -> str:
    def replace(match):
        escape = match.group(1)
        if escape.startswith("u{"):
            return chr(int(escape[2:-1], 16))
        if escape[0] in "ux" and len(escape) > 1:
            return chr(int(escape[1:], 16))
        return {"n": "\n", "r": "\r", "t": "\t", "0": "\0"}.get(escape, escape)
    return _JS_ESCAPE.sub(replace, text)


def cases_from_text(text: str) -> list[Case]:
    result: list[Case] = []
    seen: Counter = Counter()
    for map_name, body in _MAP.findall(text):
        for code_js, desc_js in _ENTRY.findall(body):
            code = "\x1b" + js_unescape(code_js)
            state = runs(code)[1]
            key = unique_key(f"ar/{map_name}/{code_js}", seen)
            result.append(build_case("ar", key,
                                     f"ansi-regex {map_name}: {js_unescape(desc_js)}",
                                     [(b"", RESET), (code.encode(), state)]))
    return result


def available(corpora: Path) -> bool:
    return (corpora / FILE).exists()


def cases(corpora: Path) -> list[Case]:
    return cases_from_text((corpora / FILE).read_text(encoding="utf-8"))
