"""Hand-written cases: sequences that terminfo cannot produce.

The expected states are written by hand from the reference semantics
(see ansitest/sgr.py); a unit test checks them against the reference model.
"""

from __future__ import annotations

from ..decode.irc import irc_state
from ..model import RESET, Case, State, build_case

E = "\x1b"
S = RESET.set
BOLD = S(bold=True)
UNDERLINE = S(underline=True)
ALL = S(bold=True, italic=True, underline=True, blink=True, reverse=True, strike=True)


def _case(key: str, desc: str, steps: list[tuple[str, State]]) -> Case:
    return build_case("hw", f"hw/{key}", desc,
                      [(seq.encode(), state) for seq, state in steps])


def _raw(key: str, desc: str, payload: str, expect) -> Case:
    return Case("hw", f"hw/{key}", desc, payload.encode(), expect)


def _attribute_cases():
    yield _case("empty-param-leading", "\\e[;1m: an empty parameter is 0",
                [(E + "[;1m", BOLD)])
    yield _case("empty-param-middle", "\\e[1;;4m: the empty parameter resets",
                [(E + "[3m", S(italic=True)), (E + "[1;;4m", UNDERLINE)])
    yield _case("empty-param-trailing", "\\e[4;m: the trailing empty parameter resets",
                [(E + "[1m", BOLD), (E + "[4;m", RESET)])
    yield _case("csi-m", "\\e[m resets", [(E + "[1;31m", S(bold=True, fg=1)), (E + "[m", RESET)])
    yield _case("reset-in-list", "\\e[0;4m: reset then underline",
                [(E + "[1;31m", S(bold=True, fg=1)), (E + "[0;4m", UNDERLINE)])
    yield _case("leading-zeros", "\\e[01;031m", [(E + "[01;031m", S(bold=True, fg=1))])
    yield _case("sgr22-bold-dim", "22 removes bold and dim",
                [(E + "[1;2m", S(bold=True, dim=True)), (E + "[22m", RESET)])
    yield _case("sgr22-keeps-color", "22 keeps the color",
                [(E + "[1;31m", S(bold=True, fg=1)), (E + "[22m", S(fg=1))])
    yield _case("sgr21", "21 is double underline (ECMA-48, xterm)",
                [(E + "[1m", BOLD), (E + "[21m", S(bold=True, underline=True))])
    yield _case("bold-then-dim", "bold then dim",
                [(E + "[1m", BOLD), (E + "[2m", S(bold=True, dim=True))])
    yield _case("dim-then-bold", "dim then bold",
                [(E + "[2m", S(dim=True)), (E + "[1m", S(bold=True, dim=True))])
    yield _case("attrs-off-one-by-one", "all attributes on, then off one by one",
                [(E + "[1;3;4;5;7;9m", ALL),
                 (E + "[23m", ALL.set(italic=False)),
                 (E + "[24m", ALL.set(italic=False, underline=False)),
                 (E + "[25m", ALL.set(italic=False, underline=False, blink=False)),
                 (E + "[27m", BOLD.set(strike=True)),
                 (E + "[29m", BOLD),
                 (E + "[22m", RESET)])
    yield _case("rapid-blink", "6 is rapid blink",
                [(E + "[6m", S(blink=True)), (E + "[25m", RESET)])
    yield _case("conceal", "8 and 28 (conceal) are not in the model",
                [(E + "[8m", RESET), (E + "[28m", RESET)])
    yield _case("reverse", "7 then 27", [(E + "[7m", S(reverse=True)), (E + "[27m", RESET)])
    yield _case("sgr-subparams-ignored", "\\e[1:2m: sub-parameters of 1 are ignored",
                [(E + "[1:2m", BOLD)])
    for value in ("0", "00", "", "1", "2", "3", "4", "5"):
        name = value if value else "empty"
        yield _case(f"underline-sub-{name}", f"4 then 4:{value}",
                    [(E + "[4m", UNDERLINE),
                     (E + f"[4:{value}m", S(underline=value.strip("0") != ""))])
    yield _case("underline-sub-in-list", "\\e[1;4:0;3m",
                [(E + "[4m", UNDERLINE), (E + "[1;4:0;3m", S(bold=True, italic=True))])


def _color_cases():
    yield _case("default-colors", "39 and 49",
                [(E + "[31;42m", S(fg=1, bg=2)), (E + "[39m", S(bg=2)), (E + "[49m", RESET)])
    yield _case("bright", "90-97 and 100-107",
                [(E + "[91;102m", S(fg=9, bg=10)), (E + "[97;107m", S(fg=15, bg=15))])
    yield _case("default-fg-keeps-attrs", "39 keeps the attributes",
                [(E + "[1;3;31m", S(bold=True, italic=True, fg=1)),
                 (E + "[39m", S(bold=True, italic=True))])
    yield _case("bold-light-color", "22 keeps a light color",
                [(E + "[1;91m", S(bold=True, fg=9)), (E + "[22m", S(fg=9))])
    for form in ("38;5;196", "38:5:196"):
        yield _case(f"fg256/{form}", f"\\e[{form}m",
                    [(E + f"[{form}m", S(fg=196)), (E + "[39m", RESET)])
    for form in ("48;5;21", "48:5:21"):
        yield _case(f"bg256/{form}", f"\\e[{form}m",
                    [(E + f"[{form}m", S(bg=21)), (E + "[49m", RESET)])
    for form in ("38;2;255;136;0", "38:2:255:136:0", "38:2::255:136:0", "38:2:0:255:136:0"):
        yield _case(f"fgrgb/{form}", f"\\e[{form}m",
                    [(E + f"[{form}m", S(fg="#ff8800")), (E + "[39m", RESET)])
    for form in ("48;2;18;52;86", "48:2:18:52:86", "48:2::18:52:86", "48:2:0:18:52:86"):
        yield _case(f"bgrgb/{form}", f"\\e[{form}m",
                    [(E + f"[{form}m", S(bg="#123456")), (E + "[49m", RESET)])
    yield _case("rgb-clamp", "RGB components above 255 are clamped",
                [(E + "[38;2;300;0;999m", S(fg="#ff00ff"))])
    yield _case("rgb-clamp-colon", "RGB components above 255 are clamped (colons)",
                [(E + "[38:2::256:65535:70000m", S(fg="#ffffff"))])
    yield _case("fg256-out-of-range", "index 256 is ignored, the next parameter is used",
                [(E + "[31m", S(fg=1)), (E + "[38;5;256;1m", S(fg=1, bold=True)),
                 (E + "[38:5:256m", S(fg=1, bold=True))])
    yield _case("fg-incomplete-5", "\\e[38;5m is ignored",
                [(E + "[31m", S(fg=1)), (E + "[38;5m", S(fg=1))])
    yield _case("fg-incomplete-rgb", "\\e[1;38;2;1;2m: incomplete RGB is ignored",
                [(E + "[1;38;2;1;2m", BOLD)])
    yield _case("fg-unknown-type", "\\e[38;7;1m: unknown type ignores the rest",
                [(E + "[38;7;1m", RESET)])
    yield _case("fg-incomplete-colon", "incomplete colon forms are ignored",
                [(E + "[31m", S(fg=1)), (E + "[38:2:1:2m", S(fg=1)), (E + "[38:5m", S(fg=1))])
    yield _case("fg256-then-attrs", "\\e[38;5;196;1;4m",
                [(E + "[38;5;196;1;4m", S(fg=196, bold=True, underline=True))])
    yield _case("rgb-then-attrs", "\\e[48;2;1;2;3;7m",
                [(E + "[48;2;1;2;3;7m", S(bg="#010203", reverse=True))])
    yield _case("ulcolor-semicolon", "58;2;R;G;B is consumed",
                [(E + "[4;58;2;255;0;0;1m", S(underline=True, bold=True))])
    yield _case("ulcolor-5", "58;5;N is consumed", [(E + "[58;5;196;3m", S(italic=True))])
    yield _case("ulcolor-colon", "58:2::R:G:B is ignored",
                [(E + "[58:2::255:0:0;3m", S(italic=True))])
    yield _case("ulcolor-default", "59 changes nothing",
                [(E + "[4m", UNDERLINE), (E + "[59m", UNDERLINE)])
    yield _case("many-params", "150 parameters",
                [(E + "[" + "1;" * 150 + "4m", S(bold=True, underline=True))])
    yield _case("many-params-1000", "1000 parameters (too long for IRC)",
                [(E + "[" + "0;" * 999 + "1m", BOLD)])
    yield _case("huge-number", "values above 65535 are ignored",
                [(E + "[99999999999999999999m", RESET),
                 (E + "[1;99999999999999999999;3m", S(bold=True, italic=True))])


NOISE = (
    ("osc0-bel", E + "]0;title\x07"),
    ("osc2-st", E + "]2;title" + E + "\\"),
    ("osc8", E + "]8;;https://weechat.org" + E + "\\"),
    ("osc8-end", E + "]8;;" + E + "\\"),
    ("osc52", E + "]52;c;aGVsbG8=\x07"),
    ("osc-empty", E + "]\x07"),
    ("dcs-sixel", E + "Pq#0;2;0;0;0#0~~@@vv@@~~$" + E + "\\"),
    ("dcs-decrqss", E + "P$qm" + E + "\\"),
    ("apc-kitty", E + "_Gf=24,s=1,v=1;AAAA" + E + "\\"),
    ("pm", E + "^privacy" + E + "\\"),
    ("sos", E + "Xsos" + E + "\\"),
    ("csi-dectcem", E + "[?25l"),
    ("csi-altscreen", E + "[?1049h"),
    ("csi-private-gt-m", E + "[>4;2m"),
    ("csi-private-q-m", E + "[?4m"),
    ("csi-private-eq-u", E + "[=5u"),
    ("csi-da2", E + "[>c"),
    ("csi-cursor-style", E + "[2 q"),
    ("csi-decstr", E + "[!p"),
    ("csi-decsca", E + "[0\"q"),
    ("csi-intermediate-m", E + "[1 m"),
    ("csi-decrqm", E + "[4$p"),
    ("csi-cup", E + "[10;20H"),
    ("csi-home", E + "[H"),
    ("csi-ed", E + "[2J"),
    ("csi-el", E + "[K"),
    ("csi-cuu", E + "[5A"),
    ("csi-dsr", E + "[6n"),
    ("charset-g0-dec", E + "(0"),
    ("charset-g0-ascii", E + "(B"),
    ("charset-g1", E + ")0"),
    ("charset-g2", E + "*B"),
    ("charset-g3", E + "+B"),
    ("esc-decsc", E + "7"),
    ("esc-decrc", E + "8"),
    ("esc-deckpam", E + "="),
    ("esc-deckpnm", E + ">"),
    ("esc-decaln", E + "#8"),
    ("esc-ris", E + "c"),
    ("esc-ri", E + "M"),
    ("esc-ind", E + "D"),
    ("esc-nel", E + "E"),
    ("esc-hts", E + "H"),
    ("esc-ss2", E + "N"),
    ("esc-ss3", E + "O"),
    ("esc-s7c1t", E + " F"),
)


def _noise_cases():
    for key, seq in NOISE:
        shown = seq.replace(E, "\\e").replace("\x07", "\\a")
        yield _case(f"noise/{key}", f"{shown} is removed", [("", RESET), (seq, RESET)])
    yield _case("noise-between-sgr", "SGR mixed with OSC, private CSI and DECSCUSR",
                [(E + "[1m", BOLD),
                 (E + "]0;t\x07" + E + "[3m", S(bold=True, italic=True)),
                 (E + "[?25l" + E + "[22m", S(italic=True)),
                 (E + "[2 q" + E + "[0m", RESET)])
    yield _case("sgr-around-hyperlink", "bold hyperlink",
                [(E + "[1m" + E + "]8;;http://x" + E + "\\", BOLD),
                 (E + "]8;;" + E + "\\" + E + "[m", RESET)])


def _raw_cases():
    yield _raw("osc-unterminated", "OSC without terminator at the end of the line",
               "a1" + E + "]0;title", [("a1", RESET)])
    yield _raw("csi-unterminated", "CSI without final byte at the end of the line",
               "a1" + E + "[1;2", [("a1", RESET)])
    yield _raw("lone-esc-end", "ESC at the end of the line", "a1" + E, [("a1", RESET)])
    yield _raw("esc-esc", "ESC ESC [1m: the first ESC is cancelled",
               "a1" + E + E + "[1ma2", [("a1", RESET), ("a2", BOLD)])
    # Text starting with digits or a comma right after a color: an IRC color
    # code must not take them as part of the color.
    yield _raw("digit-after-color", "digits and a comma right after colors",
               E + "[31m12" + E + "[42m,3" + E + "[39;49m4",
               [("12", S(fg=1)), (",3", S(fg=1, bg=2)), ("4", RESET)])
    yield _raw("comma-after-fg", "a comma and digits right after a text color",
               E + "[32m,5" + E + "[94m7,8", [(",5", S(fg=2)), ("7,8", S(fg=12))])


def _text_case(key: str, desc: str, steps: list[tuple[str, str, State]]) -> Case:
    """Case with explicit text after each sequence (instead of markers)."""
    payload = "".join(seq + text for seq, text, _ in steps)
    return Case("hw", f"hw/{key}", desc, payload.encode(),
                [(text, state) for _, text, state in steps if text])


def _utf8_cases():
    # Multibyte text (2, 3 and 4 bytes, double width, combining) around colors.
    yield _text_case("utf8/after-color", "2/3/4-byte characters right after a color",
                     [(E + "[31m", "é€漢🎨", S(fg=1)), (E + "[0m", "é", RESET)])
    yield _text_case("utf8/between-attrs", "multibyte characters between attributes",
                     [(E + "[1m", "€", BOLD), (E + "[3m", "漢", S(bold=True, italic=True)),
                      (E + "[22;23m", "🎨", RESET)])
    yield _text_case("utf8/rgb-and-256", "multibyte characters in RGB and 256 colors",
                     [(E + "[38;2;255;136;0m", "🎨x", S(fg="#ff8800")),
                      (E + "[48;5;21m", "漢", S(fg="#ff8800", bg=21)), (E + "[m", "b", RESET)])
    yield _text_case("utf8/before-reset", "multibyte character right before a reset",
                     [(E + "[4;7m", "a€", S(underline=True, reverse=True)), (E + "[0m", "b", RESET)])
    yield _text_case("utf8/colon-color", "multibyte character after a colon color",
                     [(E + "[38:2::1:2:3m", "ü", S(fg="#010203")), (E + "[39m", "ö", RESET)])
    yield _text_case("utf8/combining", "combining characters after attributes",
                     [(E + "[1m", "é", BOLD), (E + "[22m", "ñ", RESET)])
    # IRC color codes next to multibyte text and digits.
    yield _text_case("utf8/digits-after-color", "digits and comma after a color, with UTF-8",
                     [(E + "[32m", "€12", S(fg=2)), (E + "[31m", "5€", S(fg=1)),
                      (E + "[42m", ",€9", S(fg=1, bg=2))])
    # UTF-8 inside sequences that must be removed.
    yield _text_case("utf8/osc-title", "OSC title with UTF-8 is removed",
                     [("", "a1", RESET), (E + "]0;tïtle €\x07", "a2", RESET)])
    yield _text_case("utf8/osc8-link", "OSC 8 hyperlink with UTF-8 URL and text",
                     [(E + "]8;;https://example.org/é" + E + "\\", "lïnk", RESET),
                      (E + "]8;;" + E + "\\", "é", RESET)])
    yield _text_case("utf8/osc-emoji-st", "OSC with emoji ended by ST",
                     [(E + "]2;🎨🎨" + E + "\\", "x", RESET)])
    yield _text_case("utf8/dcs", "DCS with UTF-8 is removed",
                     [(E + "Pq€" + E + "\\", "y", RESET)])
    yield _raw("utf8/osc-unterminated", "unterminated OSC with UTF-8 at the end of the line",
               "a1" + E + "]0;tïtle é", [("a1", RESET)])
    yield _raw("utf8/esc-then-multibyte", "lone ESC followed by a multibyte character",
               "a1" + E + "é", [("a1é", RESET)])
    # C1 controls encoded in UTF-8: kept as text (terminals differ on these:
    # xterm in UTF-8 mode treats them as controls).
    yield _raw("utf8/c1-csi", "U+009B (C1 CSI in UTF-8) followed by 31m is kept as text",
               "x\u009b31my", [("x\u009b31my", RESET)])
    yield _raw("utf8/c1-osc", "U+009D ... U+009C (C1 OSC and ST in UTF-8) is kept as text",
               "x\u009d0;t\u009cy", [("x\u009d0;t\u009cy", RESET)])


def _branch_fix_cases():
    # Fix 9 (irc): ",5" right after a color must stay text, also after a
    # reset and a background; the end of a background keeps the text color.
    yield _text_case("comma-digit-after-reset-bg", "\\e[31m,5 apples \\e[0m\\e[41mred background",
                     [(E + "[31m", ",5 apples ", S(fg=1)), (E + "[0m" + E + "[41m",
                                                           "red background", S(bg=1))])
    yield _text_case("background-end", "\\e[30;43m WARN \\e[49m message",
                     [(E + "[30;43m", " WARN ", S(fg=0, bg=3)), (E + "[49m", " message", S(fg=0))])
    # Fix 10: a number out of range is ignored, not truncated (4294967297
    # was decoded as 1, bold).
    yield _text_case("number-out-of-range", "\\e[4294967297m is ignored (was read as 1, bold)",
                     [(E + "[4294967297m", "x", RESET), (E + "[31;4294967297m", "y", S(fg=1))])
    # Fix 20: DEL is ignored inside a control sequence, also in SGR, which is
    # still decoded; "\e(" before a multibyte char is removed, the char kept.
    yield _text_case("del-in-sgr", "DEL inside SGR is ignored: \\e[1<DEL>m is bold",
                     [(E + "[1\x7fm", "x", BOLD), (E + "[2\x7f2m", "y", RESET)])
    yield _text_case("del-after-esc", "DEL right after ESC is ignored: \\e<DEL>[1m is bold",
                     [(E + "\x7f[1m", "x", BOLD), (E + "\x7f\x7f[0m", "y", RESET)])
    yield _raw("del-after-intermediate", "DEL after an intermediate byte is ignored: \\e(<DEL>B",
               "x" + E + "(\x7fBy", [("xy", RESET)])
    yield _raw("utf8/charset-then-multibyte", "\\e( before a multibyte char keeps the char",
               "a1" + E + "(é", [("a1é", RESET)])
    # Fix 17: a window title in ISO-8859-1 (not valid UTF-8) is removed.
    yield Case("hw", "hw/osc-title-latin1", "window title in ISO-8859-1 (\\xe9) is removed",
               b"A\x1b]0;t\xe9tle\x07B", [("AB", RESET)])


def _irc_format_cases():
    # IRC formatting in the output of a command passes through /exec -o on
    # purpose (with ANSI colors in the same line): on the irc path, the IRC
    # codes apply; elsewhere they are invisible controls and their digits text.
    yield Case("hw", "hw/irc-format/reset-after-ansi", "ANSI red, then IRC bold and ^O reset",
               (E + "[31mred" + E + "[0m \x02bold\x0f plain").encode(),
               [("red", S(fg=1)), (" bold plain", RESET)],
               irc_expect=[("red", irc_state(fg=5)), (" ", irc_state()), ("bold", irc_state(bold=True)),
                           (" plain", irc_state())])
    yield Case("hw", "hw/irc-format/color-then-ansi", "IRC color and reset, then ANSI bold",
               ("\x0304red\x03 " + E + "[1mbold").encode(),
               [("04red ", RESET), ("bold", BOLD)],
               irc_expect=[("red", irc_state(fg=4)), (" ", irc_state()), ("bold", irc_state(bold=True))])
    yield Case("hw", "hw/irc-format/ansi-then-irc-bold", "ANSI green, IRC bold inside it",
               (E + "[32mg \x02b\x02 g").encode(),
               [("g b g", S(fg=2))],
               irc_expect=[("g ", irc_state(fg=3)), ("b", irc_state(fg=3, bold=True)), (" g", irc_state(fg=3))])
    # A raw IRC color, then an ANSI background: a terminal changes only the
    # background, but IRC cannot set a background alone (see divergences).
    yield Case("hw", "hw/irc-format/raw-color-then-ansi-bg", "IRC color 04, then ANSI background 44",
               ("\x0304red " + E + "[44mx").encode(),
               [("04red ", RESET), ("x", S(bg=4))],
               irc_expect=[("red ", irc_state(fg=4)), ("x", irc_state(fg=4, bg=2))])
    # Raw IRC attribute codes are not tracked (see divergences): a raw ^V
    # then ANSI reverse sends a second ^V, which turns reverse off.
    yield Case("hw", "hw/irc-format/raw-reverse-then-ansi", "IRC ^V, then ANSI reverse (7)",
               ("\x16a" + E + "[7mb").encode(),
               [("a", RESET), ("b", S(reverse=True))],
               irc_expect=[("a", irc_state(reverse=True)), ("b", irc_state(reverse=True))])


def cases() -> list[Case]:
    return [*_attribute_cases(), *_color_cases(), *_noise_cases(), *_raw_cases(),
            *_utf8_cases(), *_branch_fix_cases(), *_irc_format_cases()]
