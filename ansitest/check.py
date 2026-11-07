"""Compare the decoded output of a case with its expected states."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase

from .divergences import DIVERGENCES, Divergence
from .model import BYTE_PATHS, Case, State, path_skip, visible
from .project import project


@dataclass
class Result:
    case: Case
    path: str
    status: str  # "pass", "diverge", "fail" or "skip"
    detail: str = ""
    got: list | None = None
    expected: list | None = None  # Expected characters, when not from the case (display paths)


def _chars(runs, path: str | None = None) -> list[tuple[str, dict | None]]:
    """Characters of text runs with their state: reference states projected
    on `path`, or (path None) states that are already projected."""
    return [(char, project(state, path) if path is not None and state is not None else state)
            for text, state in runs for char in text]


def expected_chars(expect, path: str) -> list[tuple[str, dict | None]]:
    return _chars(expect, path)


def case_expected(case: Case, path: str) -> list[tuple[str, dict | None]]:
    """Expected characters of a case on a path (irc_expect on the irc path)."""
    if path == "irc" and case.irc_expect is not None:
        return _chars(case.irc_expect)
    return _chars(case.expect, path)


def divergence_expected(divergence: Divergence, case: Case, path: str):
    """WeeChat's expected characters for a divergence on a path: "any" if
    the divergence accepts any output, None if it gives no expectation for
    this path (then it does not apply)."""
    if path == "irc" and divergence.irc_expect is not None:
        return _chars(divergence.irc_expect)
    # expect and transform are built on the reference (terminal) states, so
    # they do not apply where the case expects IRC formatting (irc_expect).
    uses_irc_expect = path == "irc" and case.irc_expect is not None
    if divergence.expect is not None and not uses_irc_expect:
        return _chars(divergence.expect, path)
    if divergence.transform is not None and not uses_irc_expect:
        return _chars([(text, divergence.transform(state) if state is not None else None)
                       for text, state in case.expect], path)
    if (divergence.irc_expect is None and divergence.expect is None
            and divergence.transform is None):
        return "any"
    return None


def compare(expected, got) -> str | None:
    """None if equal, else a description of the first difference."""
    expected_text = "".join(char for char, _ in expected)
    got_text = "".join(char for char, _ in got)
    if expected_text != got_text:
        return f"text differs: expected {expected_text!r}, got {got_text!r}"
    for index, ((char, wanted), (_, actual)) in enumerate(zip(expected, got)):
        if wanted is not None and wanted != actual:
            diffs = ", ".join(f"{name} expected {wanted[name]!r} got {actual.get(name)!r}"
                              for name in wanted if wanted[name] != actual.get(name))
            return f"char {index} {char!r}: {diffs}"
    return None


def find_divergence(case: Case, path: str) -> Divergence | None:
    for pattern, divergence in DIVERGENCES.items():
        if path in divergence.paths and fnmatchcase(case.key, pattern):
            return divergence
    return None


# IRC formatting bytes: -color strip adds none (only those of the input remain).
IRC_FORMAT_BYTES = b"\x02\x03\x04\x0f\x11\x16\x1d\x1e\x1f"


def keep_expected(case: Case, path: str) -> bytes:
    """Expected bytes with -color ansi: the line as written, after its ID. In a
    buffer line (gui-keep), WeeChat replaces each byte that is not valid UTF-8
    with "?" (lines are stored as valid UTF-8)."""
    data = case.line()[len(case.id) + 1:]
    if path == "gui-keep":
        text = data.decode("utf-8", "surrogateescape")
        data = "".join("?" if "\udc80" <= char <= "\udcff" else char
                       for char in text).encode("utf-8")
    return data


def compare_bytes(case: Case, path: str, got: bytes) -> str | None:
    """None if the bytes of a byte path are right, else what is wrong."""
    if path.endswith("-keep"):
        expected = keep_expected(case, path)
        if got != expected:
            return f"bytes differ: expected {expected!r}, got {got!r}"
        return None
    text = visible(got.decode("utf-8", "surrogateescape"))
    if text != case.expected_text():
        return f"text differs: expected {case.expected_text()!r}, got {text!r}"
    if b"\x1b" in got:
        return "ESC left in the output"
    if path == "gui-strip" and any(byte in got for byte in b"\x19\x1a\x1b\x1c"):
        return "WeeChat code left in the output"
    for byte in IRC_FORMAT_BYTES:
        if got.count(byte) > case.payload.count(byte):
            return f"IRC formatting byte \\x{byte:02x} added"
    return None


def evaluate(case: Case, path: str, got) -> Result:
    reason = path_skip(case, path)
    if reason:
        return Result(case, path, "skip", reason)
    if got is None:
        return Result(case, path, "fail", "line not received")
    if path in BYTE_PATHS:
        error = compare_bytes(case, path, got)
        return Result(case, path, "pass" if error is None else "fail", error or "", got)
    error = compare(case_expected(case, path), got)
    divergence = find_divergence(case, path)
    alternative = divergence_expected(divergence, case, path) if divergence else None
    if alternative is None:
        return Result(case, path, "pass" if error is None else "fail", error or "", got)
    if error is None:
        return Result(case, path, "fail",
                      f"divergence no longer needed: {divergence.reason}", got)
    if alternative == "any":
        return Result(case, path, "diverge", divergence.reason, got)
    error2 = compare(alternative, got)
    if error2 is None:
        return Result(case, path, "diverge", divergence.reason, got)
    return Result(case, path, "fail",
                  f"{error} (divergence '{divergence.reason}' expects: {error2})", got)
