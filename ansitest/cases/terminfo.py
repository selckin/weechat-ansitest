"""Cases built from terminfo capabilities expanded by ncurses.

The expected state of each step comes from the meaning of the capability
(terminfo(5)), never from parsing its bytes.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..model import RESET, Case, build_case
from ..ti_dump import NON_SGR_CAPS, SGR_PARAMS

DEFAULT_TERMS = ("xterm-256color", "xterm-direct", "tmux-256color", "screen",
                 "linux", "rxvt-unicode-256color")
ROOT = Path(__file__).resolve().parents[2]

# Capabilities that turn an attribute on, and the State field they set.
ENTER = {"bold": "bold", "dim": "dim", "sitm": "italic", "smul": "underline",
         "blink": "blink", "rev": "reverse", "smxx": "strike"}
# (enter, exit) pairs: the exit is the matching capability, or sgr0.
ON_OFF = (("bold", "sgr0"), ("dim", "sgr0"), ("sitm", "ritm"), ("smul", "rmul"),
          ("blink", "sgr0"), ("rev", "sgr0"), ("smxx", "rmxx"))
COMBO_ATTRS = ("bold", "dim", "sitm", "smul", "rev", "blink")
COMBO_COLORS = (0, 1, 7, 8, 9, 15, 16, 88, 196, 231, 232, 255)
COMBO_COLORS_RGB = (0, 1, 7, 0x000008, 0xff8800, 0xffffff)
PARAM_NON_SGR = ("cup", "csr", "cub", "cuf", "cuu", "cud", "ech", "ich", "dch",
                 "il", "dl", "indn", "rin", "hpa", "vpa")
# sgr parameters that are attributes of the model, and their enter capability.
SGR_ATTRIBUTES = (("underline", "smul"), ("reverse", "rev"), ("blink", "blink"),
                  ("dim", "dim"), ("bold", "bold"))
NO_STANDOUT ="standout: smso matches no single attribute capability"


def dump(term: str) -> dict | None:
    """Terminfo strings of a TERM (see ansitest/ti_dump.py), None if missing."""
    proc = subprocess.run([sys.executable, "-m", "ansitest.ti_dump", term],
                          cwd=ROOT, capture_output=True, text=True)
    return json.loads(proc.stdout) if proc.returncode == 0 else None


def cases(terms=DEFAULT_TERMS) -> list[Case]:
    result = []
    for term in terms:
        info = dump(term)
        if info is None:
            result.append(Case("ti", f"ti/{term}", f"{term}: terminfo entry", b"", [],
                               skip=f"terminfo entry {term} not found"))
        else:
            result.extend(_TermCases(term, info).build())
    return result


class _TermCases:
    def __init__(self, term: str, info: dict):
        self.term = term
        self.info = info
        self.s = {cap: bytes.fromhex(value) for cap, value in info["strings"].items()}
        self.sgr0 = self.s.get("sgr0", b"")
        self.cases: list[Case] = []
        # Attribute shown by standout: the one whose capability has the same
        # bytes as smso (e.g. rev on xterm), None if there is none.
        self.standout = next((ENTER[cap] for cap in ("rev", "sitm", "smul", "bold",
                                                     "blink", "dim")
                              if cap in self.s and self.s.get("smso") == self.s[cap]),
                             None)

    def color(self, value: int):
        """Color set by setaf/setab with this value."""
        if self.info["rgb"] and value >= 8:
            return f"#{value:06x}"
        return value

    def add(self, key: str, desc: str, steps, skip: str | None = None) -> None:
        self.cases.append(build_case("ti", f"ti/{self.term}/{key}",
                                     f"{self.term}: {desc}", steps, skip=skip))

    def build(self) -> list[Case]:
        self.colors()
        self.attributes()
        self.sgr()
        self.combos()
        self.underline_extensions()
        self.non_sgr()
        return self.cases

    def colors(self) -> None:
        reset_colors = self.s.get("op") or self.sgr0
        for cap, field in (("setaf", "fg"), ("setab", "bg")):
            for value, seq in self.info[cap].items():
                number = int(value)
                self.add(f"{cap}/{number}", f"{cap} {number} then op",
                         [(bytes.fromhex(seq), RESET.set(**{field: self.color(number)})),
                          (reset_colors, RESET)])

    def attributes(self) -> None:
        for on, off in ON_OFF:
            if on in self.s and off in self.s:
                self.add(f"{on}-{off}", f"{on} then {off}",
                         [(self.s[on], RESET.set(**{ENTER[on]: True})), (self.s[off], RESET)])
        if "smso" in self.s and "rmso" in self.s:
            if self.standout:
                self.add("smso-rmso", f"smso (same bytes as {self.standout}) then rmso",
                         [(self.s["smso"], RESET.set(**{self.standout: True})),
                          (self.s["rmso"], RESET)])
            else:
                self.add("smso-rmso", "smso then rmso", [], skip=NO_STANDOUT)
        caps = [on for on, _ in ON_OFF if on in self.s]
        if caps and self.sgr0:
            state = RESET
            steps = []
            for cap in caps:
                state = state.set(**{ENTER[cap]: True})
                steps.append((self.s[cap], state))
            steps.append((self.sgr0, RESET))
            self.add("all-attributes", "every attribute, one after the other, then sgr0", steps)

    def sgr(self) -> None:
        for bits, seq in self.info["sgr"].items():
            flags = dict(zip(SGR_PARAMS, (bit == "1" for bit in bits)))
            # An attribute the terminal does not have (no enter capability,
            # e.g. dim on rxvt-unicode) is not set by sgr either.
            state = RESET.set(**{name: flags[name] and cap in self.s
                                 for name, cap in SGR_ATTRIBUTES})
            skip = None
            if flags["standout"]:
                if self.standout:
                    state = state.set(**{self.standout: True})
                else:
                    skip = NO_STANDOUT
            names = ",".join(name for name in SGR_PARAMS if flags[name]) or "none"
            self.add(f"sgr/{bits}", f"sgr {names} then sgr0",
                     [(bytes.fromhex(seq), state), (self.sgr0, RESET)], skip=skip)

    def combos(self) -> None:
        values = COMBO_COLORS_RGB if self.info["rgb"] else COMBO_COLORS
        fgs = [v for v in values if str(v) in self.info["setaf"]]
        bgs = [v for v in values if str(v) in self.info["setab"]]
        for fg in fgs:
            for bg in bgs:
                for cap in COMBO_ATTRS:
                    if cap not in self.s:
                        continue
                    with_fg = RESET.set(fg=self.color(fg))
                    with_bg = with_fg.set(bg=self.color(bg))
                    with_attr = with_bg.set(**{ENTER[cap]: True})
                    self.add(f"combo/{fg}/{bg}/{cap}", f"setaf {fg}, setab {bg}, {cap}, sgr0",
                             [(bytes.fromhex(self.info["setaf"][str(fg)]), with_fg),
                              (bytes.fromhex(self.info["setab"][str(bg)]), with_bg),
                              (self.s[cap], with_attr),
                              (self.sgr0, RESET)])

    def underline_extensions(self) -> None:
        if "smul" not in self.s:
            return
        underline = RESET.set(underline=True)
        for params, seq in self.info["params"].get("Smulx", []):
            style = params[0]
            self.add(f"Smulx/{style}", f"smul then Smulx {style}",
                     [(self.s["smul"], underline),
                      (bytes.fromhex(seq), RESET.set(underline=style != 0))])
        for params, seq in self.info["params"].get("Setulc", []):
            self.add(f"Setulc/{params[0]:06x}",
                     f"smul then Setulc {params[0]:06x} (underline color: no change)",
                     [(self.s["smul"], underline), (bytes.fromhex(seq), underline),
                      (self.sgr0, RESET)])

    def non_sgr(self) -> None:
        for cap in NON_SGR_CAPS:
            if cap in self.s:
                self.add(f"str/{cap}", f"{cap} (no SGR meaning: removed)",
                         [(b"", RESET), (self.s[cap], RESET)])
        for cap in PARAM_NON_SGR:
            for params, seq in self.info["params"].get(cap, []):
                self.add(f"param/{cap}/{'-'.join(map(str, params))}",
                         f"{cap} {params} (no SGR meaning: removed)",
                         [(b"", RESET), (bytes.fromhex(seq), RESET)])
