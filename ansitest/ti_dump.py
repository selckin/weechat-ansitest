"""Dump the terminfo strings of one TERM as JSON.

Usage: python3 -m ansitest.ti_dump TERM

Python's curses.setupterm only takes effect once per process, so each TERM
is dumped by its own process (see ansitest/cases/terminfo.py).
"""

from __future__ import annotations

import curses
import itertools
import json
import os
import re
import sys

# Padding ("$<100/>") is for tputs only: it is never sent to the terminal.
PAD = re.compile(rb"\$<[0-9.]+[*/]*>")

ATTRIBUTE_CAPS = ("bold", "dim", "sitm", "ritm", "smul", "rmul", "blink", "rev",
                  "smso", "rmso", "smxx", "rmxx", "sgr0", "op", "invis")
NON_SGR_CAPS = ("el", "el1", "ed", "clear", "home", "smcup", "rmcup", "civis",
                "cnorm", "cvvis", "sc", "rc", "flash", "smkx", "rmkx", "smam",
                "rmam", "enacs", "smacs", "rmacs", "smir", "rmir", "ri", "hts",
                "tbc", "dsl")
PARAM_CAPS = {
    "cup": [(0, 0), (1, 1), (23, 79), (254, 254), (9999, 9999)],
    "csr": [(0, 23), (5, 10)],
    **{cap: [(0,), (1,), (255,), (9999,)]
       for cap in ("cub", "cuf", "cuu", "cud", "ech", "ich", "dch", "il", "dl",
                   "indn", "rin", "hpa", "vpa")},
    "Smulx": [(n,) for n in range(6)],
    "Setulc": [(0x000000,), (0xff0000,), (0x123456,)],
}
RGB_VALUES = (0x000008, 0x010101, 0x0000ff, 0x00ff00, 0xff0000, 0xff8800,
              0x123456, 0x7f7f7f, 0x808080, 0xfffffe, 0xffffff)
SGR_PARAMS = ("standout", "underline", "reverse", "blink", "dim", "bold",
              "invis", "protect", "altcharset")


def _hex(value: bytes | None) -> str | None:
    return None if value is None else PAD.sub(b"", value).hex()


def _tparm(template: bytes, *params: int) -> str | None:
    try:
        return _hex(curses.tparm(template, *params))
    except curses.error:
        return None


def color_values(colors: int, rgb: bool) -> list[int]:
    """setaf/setab values: with direct colors (RGB), values below 8 are
    palette indexes and the others are 0xRRGGBB."""
    if rgb:
        return list(range(8)) + list(RGB_VALUES)
    return list(range(min(colors, 256)))


def dump(term: str) -> dict:
    curses.setupterm(term, os.open(os.devnull, os.O_WRONLY))
    colors = curses.tigetnum("colors")
    rgb = curses.tigetflag("RGB") == 1 or colors > 256
    info = {"term": term, "colors": colors, "rgb": rgb, "strings": {},
            "setaf": {}, "setab": {}, "sgr": {}, "params": {}}
    for cap in ATTRIBUTE_CAPS + NON_SGR_CAPS:
        value = curses.tigetstr(cap)
        if value is not None:
            info["strings"][cap] = _hex(value)
    for cap in ("setaf", "setab"):
        template = curses.tigetstr(cap)
        if template is None:
            continue
        for value in color_values(colors, rgb):
            seq = _tparm(template, value)
            if seq is not None:
                info[cap][str(value)] = seq
    template = curses.tigetstr("sgr")
    if template is not None:
        for bits in itertools.product((0, 1), repeat=9):
            seq = _tparm(template, *bits)
            if seq is not None:
                info["sgr"]["".join(map(str, bits))] = seq
    for cap, param_list in PARAM_CAPS.items():
        template = curses.tigetstr(cap)
        if template is None:
            continue
        info["params"][cap] = [[list(params), seq] for params in param_list
                               if (seq := _tparm(template, *params)) is not None]
    return info


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python3 -m ansitest.ti_dump TERM")
    try:
        info = dump(sys.argv[1])
    except curses.error as error:
        sys.exit(f"{sys.argv[1]}: {error}")
    json.dump(info, sys.stdout)


if __name__ == "__main__":
    main()
