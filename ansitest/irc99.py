"""IRC colors 16-98, from the IRC formatting specification
(https://modern.ircdocs.horse/formatting#colors-16-98): their RGB value and the
terminal color (0-255) that displays them on ANSI terminals.

The expected IRC colors of the "extended" and "rgb" palettes (WeeChat option
irc.server.*.ansi_colors) are computed from this table, not from WeeChat's
code: a terminal color displayed for an IRC color 16-98 is this IRC color,
other colors are converted to the nearest IRC color 16-98 by RGB value.
"""

from __future__ import annotations

# (IRC color, RGB value, terminal color)
IRC99 = (
    (16, 0x470000, 52), (17, 0x472100, 94), (18, 0x474700, 100), (19, 0x324700, 58),
    (20, 0x004700, 22), (21, 0x00472c, 29), (22, 0x004747, 23), (23, 0x002747, 24),
    (24, 0x000047, 17), (25, 0x2e0047, 54), (26, 0x470047, 53), (27, 0x47002a, 89),
    (28, 0x740000, 88), (29, 0x743a00, 130), (30, 0x747400, 142), (31, 0x517400, 64),
    (32, 0x007400, 28), (33, 0x007449, 35), (34, 0x007474, 30), (35, 0x004074, 25),
    (36, 0x000074, 18), (37, 0x4b0074, 91), (38, 0x740074, 90), (39, 0x740045, 125),
    (40, 0xb50000, 124), (41, 0xb56300, 166), (42, 0xb5b500, 184), (43, 0x7db500, 106),
    (44, 0x00b500, 34), (45, 0x00b571, 49), (46, 0x00b5b5, 37), (47, 0x0063b5, 33),
    (48, 0x0000b5, 19), (49, 0x7500b5, 129), (50, 0xb500b5, 127), (51, 0xb5006b, 161),
    (52, 0xff0000, 196), (53, 0xff8c00, 208), (54, 0xffff00, 226), (55, 0xb2ff00, 154),
    (56, 0x00ff00, 46), (57, 0x00ffa0, 86), (58, 0x00ffff, 51), (59, 0x008cff, 75),
    (60, 0x0000ff, 21), (61, 0xa500ff, 171), (62, 0xff00ff, 201), (63, 0xff0098, 198),
    (64, 0xff5959, 203), (65, 0xffb459, 215), (66, 0xffff71, 227), (67, 0xcfff60, 191),
    (68, 0x6fff6f, 83), (69, 0x65ffc9, 122), (70, 0x6dffff, 87), (71, 0x59b4ff, 111),
    (72, 0x5959ff, 63), (73, 0xc459ff, 177), (74, 0xff66ff, 207), (75, 0xff59bc, 205),
    (76, 0xff9c9c, 217), (77, 0xffd39c, 223), (78, 0xffff9c, 229), (79, 0xe2ff9c, 193),
    (80, 0x9cff9c, 157), (81, 0x9cffdb, 158), (82, 0x9cffff, 159), (83, 0x9cd3ff, 153),
    (84, 0x9c9cff, 147), (85, 0xdc9cff, 183), (86, 0xff9cff, 219), (87, 0xff94d3, 212),
    (88, 0x000000, 16), (89, 0x131313, 233), (90, 0x282828, 235), (91, 0x363636, 237),
    (92, 0x4d4d4d, 239), (93, 0x656565, 241), (94, 0x818181, 244), (95, 0x9f9f9f, 247),
    (96, 0xbcbcbc, 250), (97, 0xe2e2e2, 254), (98, 0xffffff, 231),
)

_BY_TERM = {term: number for number, _, term in IRC99}


def irc99_from_term(index: int) -> int | None:
    """IRC color 16-98 displayed with terminal color `index`, None if none."""
    return _BY_TERM.get(index)


def nearest_irc99(rgb: int) -> int:
    """Nearest IRC color 16-98 (squared RGB distance, the first one wins)."""
    red, green, blue = rgb >> 16, (rgb >> 8) & 0xFF, rgb & 0xFF
    best, best_diff = None, None
    for number, value, _ in IRC99:
        diff = (((value >> 16) - red) ** 2 + (((value >> 8) & 0xFF) - green) ** 2
                + ((value & 0xFF) - blue) ** 2)
        if best_diff is None or diff < best_diff:
            best, best_diff = number, diff
    return best
