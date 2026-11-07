"""Cases that are not /exec output: lines printed with /print and WeeChat
colors (option colors, attributes), read back through the logger's ANSI
encoder (path "print"). Each case sets the options it needs first.

On a terminal with fewer than 16 colors, or with
weechat.look.color_basic_force_bold, a light color is displayed as the
basic color with bold. So the expected state of each character is its
displayed color: a color 0-7 with bold counts as the light color 8-15.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import RESET, Case

S = RESET.set
LIGHT_RED = S(fg=9)

FORCE_BOLD_ON = "/set weechat.look.color_basic_force_bold on"
FORCE_BOLD_OFF = "/set weechat.look.color_basic_force_bold off"


@dataclass
class PrintCase(Case):
    """Case printed with /eval /print <id> <expression>; payload is the
    expression, setup the commands run before."""

    setup: tuple[str, ...] = field(default_factory=tuple)


def _case(key: str, desc: str, setup: tuple[str, ...], expression: str, expect) -> PrintCase:
    return PrintCase("print", f"print/{key}", desc, expression.encode(), expect, setup=setup)


def cases() -> list[PrintCase]:
    bold_on_off = "light ${color:bold}b${color:-bold} after"
    expect = [("light b after", LIGHT_RED)]
    return [
        _case("force-bold/option-lightred", "option color lightred, bold on and off, "
              "with color_basic_force_bold: light red throughout",
              (FORCE_BOLD_ON, "/set weechat.color.chat_host lightred"),
              "${color:chat_host}" + bold_on_off, expect),
        _case("force-bold/option-bold-lightred", "option color *lightred (light and bold), "
              "bold on and off, with color_basic_force_bold: light red throughout",
              (FORCE_BOLD_ON, "/set weechat.color.chat_host *lightred"),
              "${color:chat_host}" + bold_on_off, expect),
        _case("force-bold/custom-lightred", "custom color lightred, bold on and off, "
              "with color_basic_force_bold: light red throughout",
              (FORCE_BOLD_ON,), "${color:lightred}" + bold_on_off, expect),
        _case("option-lightred", "option color lightred, bold on and off, "
              "without color_basic_force_bold: light red throughout",
              (FORCE_BOLD_OFF, "/set weechat.color.chat_host lightred"),
              "${color:chat_host}" + bold_on_off, expect),
    ]
