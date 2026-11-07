"""Cases from the recorded output of real programs (ansitest/cases/programs.json,
written by tools/record_programs.py): one case per output line. The
expected states come from the reference model (ansitest/sgr.py). For output
in IRC format (toilet --irc), the irc path expects the IRC formatting of the
line, which /exec -o passes through; the other paths expect what a terminal
shows (the codes are invisible, the digits of a color code are text)."""

from __future__ import annotations

import json
from pathlib import Path

from ..decode.irc import decode_irc_chars
from ..model import Case, visible
from ..sgr import runs

FILE = Path(__file__).resolve().parent / "programs.json"


def cases_from_records(records: list[dict]) -> list[Case]:
    result = []
    for record in records:
        fixes = ", ".join(str(number) for number in record["fixes"])
        suffix = f"; fix {fixes}" if fixes else ""
        for number, line_hex in enumerate(record["lines"], 1):
            payload = bytes.fromhex(line_hex)
            text_runs, _ = runs(payload.decode("utf-8", "surrogateescape"))
            expect = [(visible(text), state) for text, state in text_runs if visible(text)]
            irc_expect = None
            if record.get("format") == "irc":
                irc_expect = _runs(decode_irc_chars(payload.decode("utf-8", "surrogateescape")))
            result.append(Case("prog", f"prog/{record['name']}/{number}",
                               f"{record['command']} ({record['version']}), line {number}{suffix}",
                               payload, expect, irc_expect=irc_expect))
    return result


def _runs(chars: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    """Group characters with the same state into runs."""
    runs_out: list[tuple[str, dict]] = []
    for char, state in chars:
        if runs_out and runs_out[-1][1] == state:
            runs_out[-1] = (runs_out[-1][0] + char, state)
        else:
            runs_out.append((char, state))
    return runs_out


def cases() -> list[Case]:
    return cases_from_records(json.loads(FILE.read_text(encoding="utf-8")))
