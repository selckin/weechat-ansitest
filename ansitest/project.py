"""Project a reference state onto what each path can represent.

gui and gui-ansi: WeeChat colors (RGB converted to the nearest of 256
colors, or kept as RGB colors by WeeChat with RGB colors), no strikethrough.
irc: IRC colors (see PROFILE.irc_colors), no dim and no blink; SGR 2 removes
bold, so bold is shown only without dim.

The profile describes the WeeChat under test (ansicheck detects it):

- rgb: WeeChat keeps RGB colors ("#rrggbb", WeeChat with PR #2375);
- irc_colors: IRC colors used for ANSI colors (server option "ansi_colors"):
  "basic" (0-15, through WeeChat's tables), "extended" (terminal colors
  16-255 and RGB colors are IRC colors 16-98) or "rgb" (like extended, but
  RGB colors and terminal colors not displayed for an IRC color 16-98 are
  RGB colors, sent as IRC hex colors).
"""

from __future__ import annotations

from dataclasses import dataclass

from .irc99 import irc99_from_term, nearest_irc99
from .model import GUI_PATHS, State
from .tables import TERM256, rgb_to_irc, rgb_to_term, term_to_irc

IRC_COLORS = ("basic", "extended", "rgb")


@dataclass
class Profile:
    rgb: bool = False
    irc_colors: str = "basic"


PROFILE = Profile()


def set_profile(rgb: bool = False, irc_colors: str = "basic") -> None:
    if irc_colors not in IRC_COLORS:
        raise ValueError(f"unknown IRC colors: {irc_colors}")
    PROFILE.rgb = rgb
    PROFILE.irc_colors = irc_colors


def _gui_color(color):
    if isinstance(color, str):
        return color if PROFILE.rgb else rgb_to_term(int(color[1:], 16), 256)
    return color


def _irc_color(color):
    if color is None:
        return None
    palette = PROFILE.irc_colors
    if isinstance(color, str):
        rgb = int(color[1:], 16)
        if palette == "rgb":
            return color
        return nearest_irc99(rgb) if palette == "extended" else rgb_to_irc(rgb)
    # Terminal colors 0-15 (like the terminal theme) are always IRC colors 0-15.
    if palette == "basic" or color < 16:
        return term_to_irc(color)
    number = irc99_from_term(color)
    if number is not None:
        return number
    if palette == "rgb":
        return "#%06x" % TERM256[color]
    return nearest_irc99(TERM256[color])


def displayed_color(state: State):
    """Color displayed when bold makes a basic color light: 0-7 with bold is
    8-15 (path "print")."""
    color = _gui_color(state.fg)
    if isinstance(color, int) and color < 8 and state.bold:
        return color + 8
    return color


def project(state: State, path: str) -> dict:
    if path in GUI_PATHS:
        return {
            "fg": _gui_color(state.fg),
            "bg": _gui_color(state.bg),
            "bold": state.bold,
            "dim": state.dim,
            "italic": state.italic,
            "underline": state.underline,
            "blink": state.blink,
            "reverse": state.reverse,
        }
    if path == "irc":
        return {
            "fg": _irc_color(state.fg),
            "bg": _irc_color(state.bg),
            "bold": state.bold and not state.dim,
            "italic": state.italic,
            "underline": state.underline,
            "reverse": state.reverse,
            "strike": state.strike,
        }
    if path == "print":
        return {"fg": displayed_color(state)}
    raise ValueError(f"unknown path: {path}")
