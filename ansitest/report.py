"""Text report of the results."""

from __future__ import annotations

from collections import Counter

from .check import case_expected, keep_expected
from .model import BYTE_PATHS
from .model import describe

STATUSES = ("pass", "diverge", "fail", "skip")


def escape(data: bytes) -> str:
    """Bytes with ESC as \\e and other controls as \\xNN."""
    text = data.decode("utf-8", "backslashreplace")
    return "".join("\\e" if char == "\x1b"
                   else f"\\x{ord(char):02x}" if ord(char) < 0x20 or char == "\x7f"
                   else char
                   for char in text)


def render_chars(chars) -> str:
    """Characters grouped in runs of equal state: 'a1'[bold] 'a2'[(default)]."""
    parts = []
    current = object()
    text = ""
    for char, state in chars:
        if state != current:
            if text:
                parts.append(f"{text!r}[{describe(current)}]")
            text, current = "", state
        text += char
    if text:
        parts.append(f"{text!r}[{describe(current)}]")
    return " ".join(parts) or "(empty)"


def _expected_and_got(r) -> tuple[str, str]:
    if r.path in BYTE_PATHS:
        got = escape(r.got) if r.got is not None else "(no line)"
        expected = (escape(keep_expected(r.case, r.path)) if r.path.endswith("-keep")
                    else repr(r.case.expected_text()) + " (text only, no codes)")
    elif r.expected is not None or r.case.source == "display":
        got = render_chars(r.got) if r.got is not None else "(no line)"
        expected = render_chars(r.expected) if r.expected is not None else "(no line)"
    else:
        got = render_chars(r.got) if r.got is not None else "(no line)"
        expected = render_chars(case_expected(r.case, r.path))
    return expected, got


def detail(r) -> str:
    """Input, expected and got of a result, with what the comparison found."""
    expected, got = _expected_and_got(r)
    verdict = {"pass": "correct: got is what was expected",
               "diverge": f"known divergence: {r.detail}"}.get(r.status, r.detail)
    return (f"\n{r.status.upper()} {r.case.id} [{r.path}] {r.case.key}\n"
            f"  {r.case.desc}\n"
            f"  input:    {escape(r.case.payload)}\n"
            f"  expected: {expected}\n"
            f"  got:      {got}\n"
            f"  {verdict}")


def report(results, out, verbose: bool = False, details: bool = False) -> int:
    """Counts per source and path, then the details of each failure (of
    each result that is not skipped, if details)."""
    counts = Counter((r.case.source, r.path, r.status) for r in results)
    groups = sorted({(r.case.source, r.path) for r in results})
    print(f"{'source':8} {'path':16} " + " ".join(f"{s:>7}" for s in STATUSES), file=out)
    for source, path in groups:
        print(f"{source:8} {path:16} "
              + " ".join(f"{counts[(source, path, s)]:7}" for s in STATUSES), file=out)

    failures = [r for r in results if r.status == "fail"]
    for r in results:
        if r.status == "fail" or (details and r.status != "skip"):
            print(detail(r), file=out)

    for status, title in (("diverge", "Divergences"), ("skip", "Skipped")):
        reasons = Counter((r.path, r.detail) for r in results if r.status == status)
        if reasons:
            print(f"\n{title}:", file=out)
            for (path, reason), number in sorted(reasons.items()):
                print(f"  {number:6} [{path}] {reason}", file=out)
        if verbose:
            for r in results:
                if r.status == status:
                    print(f"    {r.case.id} [{r.path}] {r.case.key}", file=out)

    print(f"\n{len(failures)} failure(s)", file=out)
    return len(failures)
