"""WeeChat's color conversions, on the tables copied by tools/extract_tables.py."""

from .tables_data import TERM256, TERM2IRC

__all__ = ["TERM256", "TERM2IRC", "rgb_to_term", "rgb_to_irc", "term_to_irc"]


def rgb_to_term(rgb: int, limit: int = 256) -> int:
    """gui_color_convert_rgb_to_term (src/gui/gui-color.c): closest of the
    first `limit` terminal colors, the first exact match wins."""
    limit = min(limit, 256)
    red, green, blue = rgb >> 16, (rgb >> 8) & 0xFF, rgb & 0xFF
    best_diff = None
    best_color = 0
    for index in range(limit):
        color = TERM256[index]
        diff = (((color >> 16) - red) ** 2
                + (((color >> 8) & 0xFF) - green) ** 2
                + ((color & 0xFF) - blue) ** 2)
        if diff == 0:
            return index
        if best_diff is None or diff < best_diff:
            best_color, best_diff = index, diff
    return best_color


def rgb_to_irc(rgb: int) -> int:
    """irc_color_convert_rgb2irc (src/plugins/irc/irc-color.c)."""
    return TERM2IRC[rgb_to_term(rgb, len(TERM2IRC))]


def term_to_irc(index: int) -> int:
    """irc_color_convert_term2irc (src/plugins/irc/irc-color.c)."""
    return rgb_to_irc(TERM256[index])
