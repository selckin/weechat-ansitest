"""Known differences between WeeChat and the reference (ECMA-48 / xterm,
or a corpus's own expectations).

DIVERGENCES maps a case key (or an fnmatch pattern) to the paths where
WeeChat differs, the reason, and WeeChat's expected result: either the
expected runs (reference states, projected like the normal expectation), or
a transform applied to each expected state of the case (for patterns that
cover many cases). With neither, any output is accepted.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .decode.irc import irc_state
from .model import RESET, State

S = RESET.set


@dataclass(frozen=True)
class Divergence:
    paths: tuple[str, ...]
    reason: str
    expect: tuple[tuple[str, State | None], ...] | None = None
    transform: Callable[[State], State] | None = None
    # For cases with irc_expect: WeeChat's expected IRC states on the irc path.
    irc_expect: tuple[tuple[str, dict], ...] | None = None


DIVERGENCES: dict[str, Divergence] = {
    "hw/sgr21": Divergence(
        ("gui", "gui-ansi", "irc"),
        "SGR 21 removes bold in WeeChat; ECMA-48 and xterm use it for double underline",
        (("a1", S(bold=True)), ("a2", RESET))),
    "hw/dim-then-bold": Divergence(
        ("irc",),
        "on the irc path SGR 2 removes bold, so bold after dim is kept",
        (("a1", S(dim=True)), ("a2", S(bold=True)))),
    # The linux sgr writes dim before bold ("2;1"): on the irc path SGR 2
    # removes bold, then 1 sets it, so the text is bold (as hw/dim-then-bold).
    "ti/linux/sgr/????11???": Divergence(
        ("irc",),
        "on the irc path SGR 2 removes bold, so bold after dim is kept (linux sgr: 2;1)",
        transform=lambda state: state.set(dim=False)),
    "hw/irc-format/raw-reverse-then-ansi": Divergence(
        ("irc",),
        "raw IRC attribute codes in the text are not tracked: ANSI reverse after a raw ^V "
        "sends another ^V, which turns reverse off",
        irc_expect=(("a", irc_state(reverse=True)), ("b", irc_state()))),
    "hw/irc-format/raw-color-then-ansi-bg": Divergence(
        ("irc",),
        "the text color after a raw IRC color code is unknown, and IRC cannot set a background "
        "alone, so an ANSI background change is sent with the default text color",
        irc_expect=(("red ", irc_state(fg=4)), ("x", irc_state(bg=2)))),
    "lvp/30state_pen/DECSTR resets pen attributes": Divergence(
        ("gui", "gui-ansi", "irc"),
        "WeeChat removes DECSTR (CSI ! p) without resetting the attributes",
        (("a1", S(bold=True, underline=True)), ("a2", S(bold=True, underline=True)))),
    "lvp/30state_pen/Bold+ANSI colour == highbright": Divergence(
        ("gui", "gui-ansi", "irc"),
        "libvterm brightens colors 0-7 when bold (bold_is_highbright); WeeChat keeps the color",
        (("a1", S(bold=True, fg=7)), ("a2", S(bold=True, fg=7)))),
}

# Where libvterm's ?pen assertions differ from the reference model:
# (case key, push number starting at 1, State field).
KNOWN_LIBVTERM_DIFFS: set[tuple[str, int, str]] = {
    ("lvp/30state_pen/Bold+ANSI colour == highbright", 1, "fg"),
    ("lvp/30state_pen/Bold+ANSI colour == highbright", 2, "fg"),
    ("lvp/30state_pen/DECSTR resets pen attributes", 2, "bold"),
    ("lvp/30state_pen/DECSTR resets pen attributes", 2, "underline"),
}
