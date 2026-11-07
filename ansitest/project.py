"""Project a reference state onto what each path can represent.

gui and gui-ansi: WeeChat colors (RGB converted to the nearest of 256
colors), no strikethrough. irc: IRC colors (0-15 through WeeChat's tables), no dim and
no blink; SGR 2 removes bold, so bold is shown only without dim.
"""

from .model import GUI_PATHS, State
from .tables import rgb_to_irc, rgb_to_term, term_to_irc


def _gui_color(color):
    if isinstance(color, str):
        return rgb_to_term(int(color[1:], 16), 256)
    return color


def _irc_color(color):
    if color is None:
        return None
    if isinstance(color, str):
        return rgb_to_irc(int(color[1:], 16))
    return term_to_irc(color)


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
