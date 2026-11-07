"""Reference attribute state, test cases and per-path skip rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace

# gui: buffer line as stored (raw WeeChat color codes); gui-ansi: the same
# line through the logger (WeeChat's ANSI encoder); irc: /exec -o to IRC.
# These use the default /exec -color auto. The other paths check the bytes
# of the result with -color strip (gui-strip, irc-strip: all ANSI removed)
# and -color ansi (gui-keep, irc-keep: kept as is).
# print: lines printed with /print (cases "print/*" only), through the logger.
# display, display-headless: generated lines of WeeChat colors printed in a
# curses WeeChat in tmux; the screen is expected from the logger of that
# WeeChat and of weechat-headless (cases "display/*", needs tmux).
PATHS = ("gui", "gui-ansi", "irc", "gui-strip", "irc-strip", "gui-keep", "irc-keep", "print",
         "display", "display-headless")
GUI_PATHS = ("gui", "gui-ansi")
BYTE_PATHS = ("gui-strip", "irc-strip", "gui-keep", "irc-keep")
# Option -color of /exec for each path.
PATH_COLOR = {"gui": "auto", "gui-ansi": "auto", "irc": "auto", "gui-strip": "strip",
              "irc-strip": "strip", "gui-keep": "ansi", "irc-keep": "ansi"}

# Longest line (ID, payload and reset) on the irc path: WeeChat splits longer
# messages, which would separate text from its ID.
MAX_IRC_LINE = 400


@dataclass(frozen=True)
class State:
    """Reference attribute state (ECMA-48 / xterm).

    Colors: None is the default color, an int is a palette index (0-255), a
    str "#rrggbb" is a RGB color.
    """

    fg: int | str | None = None
    bg: int | str | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    strike: bool = False

    def set(self, **changes) -> State:
        return replace(self, **changes)

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(data: dict) -> State:
        return State(**data)


RESET = State()


def marker(index: int) -> str:
    """Text of step `index` in a case made by build_case: a1..a9, b1, ..."""
    return chr(ord("a") + (index // 9) % 26) + str(index % 9 + 1)


@dataclass
class Case:
    """One test case: one output line "<id> <payload>\\e[0m".

    `expect` lists the visible text runs and the state that applies to each
    run (None: the state is not checked). `irc_expect`, if set, replaces it on
    the irc path, with IRC states (as decoded from IRC formatting codes): for
    input that holds IRC formatting, which /exec -o passes through on purpose.
    """

    source: str
    key: str
    desc: str
    payload: bytes
    expect: list[tuple[str, State | None]]
    skip: str | None = None
    id: str = ""
    irc_expect: list[tuple[str, dict]] | None = None

    def line(self) -> bytes:
        return self.id.encode() + b" " + self.payload + b"\x1b[0m"

    def expected_text(self) -> str:
        return "".join(text for text, _ in self.expect)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "key": self.key,
            "desc": self.desc,
            "payload": self.payload.hex(),
            "expect": [[text, state.to_json() if state else None]
                       for text, state in self.expect],
            "skip": self.skip,
            "irc_expect": ([[text, state] for text, state in self.irc_expect]
                           if self.irc_expect is not None else None),
        }

    @staticmethod
    def from_json(data: dict) -> Case:
        return Case(
            source=data["source"],
            key=data["key"],
            desc=data["desc"],
            payload=bytes.fromhex(data["payload"]),
            expect=[(text, State.from_json(state) if state else None)
                    for text, state in data["expect"]],
            skip=data["skip"],
            id=data["id"],
            irc_expect=([(text, state) for text, state in data["irc_expect"]]
                        if data.get("irc_expect") is not None else None),
        )


def build_case(source: str, key: str, desc: str,
               steps: list[tuple[bytes, State]], skip: str | None = None) -> Case:
    """Make a case where each step is a sequence followed by a marker text."""
    payload = b""
    expect = []
    for index, (seq, state) in enumerate(steps):
        text = marker(index)
        payload += seq + text.encode()
        expect.append((text, state))
    return Case(source, key, desc, payload, expect, skip)


def path_skip(case: Case, path: str) -> str | None:
    """Return why the case cannot run on this path, None if it can."""
    if case.skip:
        return case.skip
    payload = case.payload
    if b"\x00" in payload:
        return "contains NUL (ends the line in WeeChat)"
    if b"\n" in payload or b"\r" in payload:
        return "contains LF or CR (splits the /exec line)"
    if b"\t" in payload:
        return "contains TAB (the logger separates fields with TAB)"
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError:
        # Invalid UTF-8 is fine inside a sequence that is removed (e.g. a
        # window title in ISO-8859-1), not in the visible text.
        from .sgr import runs
        text_runs, _ = runs(payload.decode("utf-8", "surrogateescape"))
        if any("\udc80" <= char <= "\udcff" for text, _ in text_runs for char in text):
            return "visible text is not valid UTF-8 (/exec output is read as UTF-8)"
    if path.startswith("irc"):
        if len(case.line()) > MAX_IRC_LINE:
            return f"line longer than {MAX_IRC_LINE} bytes (one IRC message)"
    return None


def visible(text: str) -> str:
    """Remove C0 controls and DEL: a terminal does not print them."""
    return "".join(char for char in text if ord(char) >= 0x20 and char != "\x7f")


def describe(state) -> str:
    """Short description of a State or a projected state (dict)."""
    if state is None:
        return "(any)"
    data = state.to_json() if isinstance(state, State) else state
    parts = []
    for name, value in data.items():
        if value is True:
            parts.append(name)
        elif value is not None and value is not False:
            parts.append(f"{name}={value}")
    return " ".join(parts) or "(default)"


def unique_key(key: str, seen: Counter) -> str:
    """Return key, or key#N if it was already used N-1 times."""
    seen[key] += 1
    return key if seen[key] == 1 else f"{key}#{seen[key]}"
