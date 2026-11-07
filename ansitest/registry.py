"""All test cases, with their IDs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .cases import ansiregex, handwritten, libvterm, printing, programs, terminfo
from .model import Case

DEFAULT_CORPORA = Path(__file__).resolve().parent.parent / "corpora"
CORPORA = (libvterm, ansiregex)


def all_cases(terms=None, corpora: Path = DEFAULT_CORPORA, warn=None) -> list[Case]:
    """All cases, numbered T00001, T00002, ... (the numbers depend on the
    TERMs and on the corpora present)."""
    warn = warn or sys.stderr
    cases = terminfo.cases(tuple(terms) if terms else terminfo.DEFAULT_TERMS)
    cases += handwritten.cases()
    cases += programs.cases()
    for module in CORPORA:
        if module.available(corpora):
            cases += module.cases(corpora)
        else:
            print(f"warning: corpus {module.NAME} not found in {corpora} "
                  "(run ./fetch-corpora.sh)", file=warn)
    for number, case in enumerate(cases, 1):
        case.id = f"T{number:05d}"
    return cases


def select(cases: list[Case], pattern: str | None) -> list[Case]:
    """Cases whose "<id> <source> <key> <desc>" matches the regex pattern."""
    if not pattern:
        return cases
    regex = re.compile(pattern)
    return [case for case in cases
            if regex.search(f"{case.id} {case.source} {case.key} {case.desc}")]


def print_cases() -> list:
    """Cases of the print path (/print, not /exec), numbered P00001, ..."""
    cases = printing.cases()
    for number, case in enumerate(cases, 1):
        case.id = f"P{number:05d}"
    return cases
