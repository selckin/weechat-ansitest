"""Lines of WeeChat colors for the display paths: printed with /print in a
curses WeeChat inside tmux, the screen (what the user sees) is the expected
result for the logger's ANSI encoder (path "display"), and for the logger of
weechat-headless with the same settings (path "display-headless").

The lines are generated: each option color (set to light colors and colors
with attributes), each basic color with attribute flags, attributes set and
removed, resets, and (on terminals with 256 colors) terminal colors and
background colors, in fixed patterns and in seeded random sequences.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Option colors used in lines, and the value each one is set to.
OPTION_COLORS = {
    "chat_host": "lightred",
    "chat_delimiters": "*lightgreen",
    "chat_value": "_yellow",
    "chat_buffer": "white",
    "chat_server": "darkgray",
    "chat_channel": "/lightcyan",
    "chat_nick_self": "*white",
    "chat_prefix_suffix": "!lightmagenta",
}
BASIC = ("default", "black", "darkgray", "red", "lightred", "green", "lightgreen", "brown",
         "yellow", "blue", "lightblue", "magenta", "lightmagenta", "cyan", "lightcyan", "gray",
         "white")
# Attribute flags in a color name: bold, underline, italic, reverse, dim,
# blink, and "|" to keep the attributes.
PREFIXES = ("", "*", "_", "/", "!", ".", "%", "|", "*|", "_/")
ATTRIBUTES = ("bold", "-bold", "dim", "-dim", "italic", "-italic", "underline", "-underline",
              "reverse", "-reverse", "blink", "-blink")
NUMBERS = ("16", "88", "196", "231", "244", "*196", "_|88")
BACKGROUNDS = ("red,blue", "lightred,darkgray", "*yellow,red", "white,88", "196,16", "|green,default")


@dataclass(frozen=True)
class DisplayConfig:
    term: str
    force_bold: bool
    real_white: bool

    @property
    def name(self) -> str:
        return (f"{self.term}-fb{'on' if self.force_bold else 'off'}"
                f"-rw{'on' if self.real_white else 'off'}")

    @property
    def colors256(self) -> bool:
        return "256" in self.term

    def setup(self) -> list[str]:
        commands = [f"/set weechat.look.color_basic_force_bold {'on' if self.force_bold else 'off'}",
                    f"/set weechat.look.color_real_white {'on' if self.real_white else 'off'}"]
        commands += [f"/set weechat.color.{option} {value}"
                     for option, value in OPTION_COLORS.items()]
        return commands


CONFIGS = tuple(DisplayConfig(term, force_bold, real_white)
                for term in ("xterm", "xterm-256color")
                for force_bold in (False, True)
                for real_white in (False, True))


def _tokens(colors256: bool) -> list[str]:
    tokens = list(OPTION_COLORS)
    tokens += [prefix + name for prefix in PREFIXES for name in BASIC]
    tokens += list(ATTRIBUTES) + ["reset", "resetcolor"]
    if colors256:
        tokens += list(NUMBERS) + list(BACKGROUNDS)
    return tokens


def _segments(colors: list[str]) -> str:
    """Expression: each color followed by a marker word."""
    return "".join(f"${{color:{color}}}{chr(ord('a') + index % 26)}{index + 1}"
                   for index, color in enumerate(colors))


def lines(config: DisplayConfig, random_lines: int = 150) -> list[tuple[str, str]]:
    """(key, /print expression) for a terminal configuration."""
    result = []
    # Bold, dim and other attributes on and off after each color.
    for color in list(OPTION_COLORS) + list(BASIC) + ([*NUMBERS] if config.colors256 else []):
        result.append((f"bold-off/{color}", _segments([color, "bold", "-bold"])))
        result.append((f"dim-off/{color}", _segments([color, "dim", "-dim", "bold", "-dim"])))
        result.append((f"attrs/{color}", _segments([color, "italic", "underline", "-italic",
                                                    "reverse", "-underline", "-reverse"])))
    # Seeded random sequences of colors, attributes and resets.
    tokens = _tokens(config.colors256)
    rng = random.Random(1364)
    for number in range(random_lines):
        result.append((f"random/{number + 1}",
                       _segments([rng.choice(tokens) for _ in range(rng.randint(2, 7))])))
    return result
