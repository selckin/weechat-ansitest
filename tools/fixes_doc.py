#!/usr/bin/env python3
"""Write docs/fixes.md from the summary written by tools/fixes_by_commit.py.

Usage: tools/fixes_doc.py OUTPUT_DIR/summary.json docs/fixes.md

The description and the reproduction of each fix (from the description of
the pull request) are below; the cases fixed by each commit come from the
summary.
"""

import json
import sys
from collections import Counter, defaultdict

summary_path, output_path = sys.argv[1:]
summary = json.load(open(summary_path))

# (what it fixes, [(reproduction, main, branch)], why no case if none)
FIXES = {
    1: ("An empty parameter means 0 (reset, ECMA-48); empty parameters were ignored. Empty "
        "arguments of 38/48 are 0 too.",
        [("/exec printf '\\033[1mbold\\033[;m normal\\n'", '"normal" is bold', '"normal" is not bold')], None),
    2: ("`58;5;N` and `58;2;R;G;B` (underline color) are consumed as a unit and ignored; their "
        "arguments were decoded as other attributes.",
        [("/exec printf '\\033[4;58;2;255;0;0munderline\\033[0m normal\\n'",
          '"underline" is not underlined (`2` dim, `0` reset)', '"underline" is underlined')], None),
    3: ("Removing an attribute cleared all the attributes tracked for the current color "
        "(`&= !style` instead of `&= ~style`, since 2008).",
        [("/eval /print ${color:reverse}rev1 ${color:-italic}x${esc:\\x01}y rev2",
          '"y rev2" loses reverse video', "all reverse video")],
        "The bug is in the curses display's tracking of attributes, not in the stored line "
        "that the gui path reads, and `/exec` does not produce this input."),
    4: ("On a terminal with less than 16 colors (or with `weechat.look.color_basic_force_bold`), "
        "light colors are displayed with bold; this bold is now tracked separately from the bold "
        "attribute (for custom colors and colors of options), so removing the bold attribute "
        "keeps a light color light, and another color drops the bold of the previous one (also "
        "for a light option color with the bold attribute, like `*lightred`).",
        [("/eval /print ${color:darkgray}gray ${color:bold}bold${color:-bold} gray",
          'last "gray" is black', 'last "gray" is gray', "with `TERM=xterm`, 8 colors"),
         ("/eval /print ${color:chat_highlight}hl ${color:bold}b${color:-bold} after",
          '"after" is brown', '"after" is yellow', "with `TERM=xterm`, 8 colors")],
        "Display only, on terminals with 8 colors; the gui path models a terminal with 16 colors "
        "or more and reads the stored line."),
    5: ("22 (normal intensity) removed only dim. The encoder (`color_encode_ansi`, used by the "
        "relay api and the logger) uses 22 instead of 21 (double underline in most terminals) "
        "for `-bold`, and sets bold or dim again if the other one is still set.",
        [("/exec printf '\\033[1mbold\\033[22m normal\\n'", '"normal" is bold', '"normal" is not bold'),
         ("/exec node -e \"console.log(require('util').inspect({a:null,b:1},{colors:true}))\"",
          "`null, b: 1 }` is bold", "only `null` is bold")], None),
    6: ("39 is decoded as `|default` like 30-37; it removed all attributes. Programs often end "
        "bold colored text with `\\e[39m\\e[22m`.",
        [("/exec printf '\\033[1mbold \\033[31mred\\033[39m bold\\n'", 'last "bold" is not bold', 'last "bold" is bold'),
         ("/exec -sh echo '{\"key\":[1]}' | jq -C -c .", "braces and `:` are not bold", "braces and `:` are bold (`1;39`)")], None),
    7: ("The regex follows the ECMA-48 grammar of control sequences, so they are all removed "
        "(for example cursor style `\\e[2 q`); only SGR sequences with parameters made of digits, "
        "`;` and `:` are decoded (`\\e[?4m` and `\\e[1;>4m` were decoded as resets). The regex is "
        "also the value of info `color_ansi_regex`.",
        [("/exec printf 'A\\033[2 qB\\033[?4mC\\033[=5uD\\n'", "`A2 qBC=5uD`", "`ABCD`")], None),
    8: ("A RGB component > 255 overflowed into the other components; components are clamped "
        "to 0-255.",
        [("/exec printf '\\033[38;2;0;256;0mgreen\\033[0m\\n'", "black", "green")], None),
    9: ("IRC colors are sent unambiguously: a background with the text color (`^CFF,BB`), colors "
        "only when they change, `^B^B` before text starting with `,<digit>` after a text color "
        "sent alone, and the end of a background as `^C^CFF` so that `irc.color.mirc_remap` "
        "still applies. `\\e[m` also resets attributes.",
        [("/exec -o msgcat --color=test", "backgrounds sent alone (`^C,01`): `,01` shown as text", "no stray text",
          "in an IRC channel"),
         ("/exec -o -sh printf 'a,5 b\\n' | grep --color=always ',5'", "`,5` disappears, red on red", "`,5` shown in red")], None),
    10: ("The arguments of 38, 48 and 58 are parsed by one function: an incomplete color or an "
         "unknown type ignores the remaining parameters, a terminal color > 255 is ignored, and "
         "numbers out of range are ignored instead of truncated (`4294967297` was `1`, bold).",
         [("/exec printf '\\033[31mred\\033[58;2;1;0m still red\\n'", '" still red" is not red', '" still red" is red')], None),
    11: ("Codes 7 and 27 (reverse video) were ignored when converting to IRC.",
         [("/eval /print ${modifier:irc_color_decode,1,${modifier:irc_color_decode_ansi,1,${esc:\\e[7m}rev${esc:\\e[27m} normal}}",
           "no reverse video", '"rev" in reverse video')], None),
    12: ("The bar delimiter color was converted to a background color by the encoder, although "
         "it is displayed as a text color.",
         [("/eval /exec -sh printf '%s\\n' '${modifier:color_encode_ansi,,${color:bar_delim}(}' | cat -v",
           "`^[[48;5;22m`", "`^[[38;5;22m`")],
         "In the encoder (`color_encode_ansi`) for bar colors, which `/exec` output never contains."),
    13: ("Operating system commands (window title, hyperlinks), device control strings and "
         "escape sequences like `\\e7`, `\\e=` or `\\e#8` were displayed as text.",
         [("/exec printf 'A \\033]8;;https://weechat.org\\033\\\\link\\033]8;;\\033\\\\ \\033]0;title\\007B\\n'",
           "URL and title shown as text", "`A link B`"),
          ("/exec -sh ls --hyperlink=always", "hyperlinks shown as text", "hyperlinks removed")], None),
    14: ("Sub-parameters (ITU T.416, used by kitty, foot, tmux, Neovim, `tput` with `-direct` "
         "terminals) are decoded: `38:5:N`, `38:2:R:G:B`, `38:2:<color space>:R:G:B`, underline "
         "style `4:N` (`4:0` is no underline), `58:...` ignored, other parameters use only their "
         "value (`1:2` is `1`).",
         [("/exec printf '\\033[38:2::255:136:0morange\\033[0m \\033[4:3mcurly\\033[4:0m end\\n'",
           "sequences shown as text", '"orange" in orange, "curly" underlined'),
          ("/exec -sh TERM=xterm-direct tput setaf 16711680; echo red", "sequence shown as text", '"red" in red')], None),
    15: ("Each parameter was added with `strcat`, so N parameters took a time proportional to N².",
         [("/exec -sh python3 -c \"print('\\033[' + ';'.join(['1'] * 1000000) + 'mX')\"",
           "WeeChat frozen for about 30 seconds", "decoded in less than a second")],
         "Speed: the harness checks results, not time (`hw/many-params-1000` checks that the "
         "result of 1000 parameters is right)."),
    16: ("`regexec` computed the length of the rest of the line at each sequence (and core "
         "copied the string), so N sequences took a time proportional to N²; the remaining "
         "length is given to `regexec` (`REG_STARTEND`, if available).",
         [("/exec -sh python3 -c \"print('\\0337x' * 160000)\"", "WeeChat frozen for about 4 seconds",
           "decoded in less than a second")],
         "Speed: the harness checks results, not time."),
    17: ("With a UTF-8 locale, the regex did not match bytes that are not valid UTF-8, so a "
         "window title in ISO-8859-1 was not removed. Escape sequences contain only ASCII chars: "
         "they are searched in a copy of the line where the other chars are replaced by `\\x01` "
         "(same length), and the text is copied from the original line.",
         [("/exec printf 'A\\033]0;t\\351tle\\007B\\n'", "`A0;t?tle^GB`", "`AB`")], None),
    18: ("Code 6 (rapid blink) was ignored; it is decoded like 5.",
         [("/exec printf '\\033[6mblink\\033[0m\\n'", "no blink", '"blink" blinks')], None),
    19: ("terminfo sends SI and SO with some terminals (with `TERM=screen`, `tmux-256color` or "
         "`linux`, `sgr` ends with SI); they were kept as text, and SI is the IRC reset (`^O`), so "
         "the attributes set just before it were lost on IRC. They are now removed, except SI on "
         "IRC, which is kept (text already formatted for IRC can contain it) and followed by the "
         "attributes and colors of the ANSI sequences.",
         [("/eval /print ${modifier:irc_color_decode,1,${modifier:irc_color_decode_ansi,1,${esc:\\e[1m\\x0f}bold}}",
           '"bold" is not bold (SI sent as `^O`, the IRC reset)', '"bold" is bold'),
          ("/exec -o -sh TERM=screen tput sgr 0 0 0 0 0 1; echo bold",
           '"bold" is not bold (`tput` emits `\\e[0;1m` then SI)', '"bold" is bold', "in an IRC channel")], None),
    20: ("A sequence cut before its end, cancelled by CAN, SUB or another escape sequence, and a "
         "lone ESC are removed instead of showing the rest as text; DEL is ignored after ESC "
         "and inside a control sequence (also in SGR sequences, which are still decoded), and "
         "OSC and DCS "
         "strings can also end with BEL. A char set designation without its final byte (`\\e(` "
         "followed by a newline or a multibyte char) is removed without the char after it.",
         [("/exec printf 'a1\\033]0;title\\n'", "`a10;title`", "`a1`")], None),
    21: ("The char after a set/remove attribute code is consumed by the encoder only if it is a "
         "valid attribute, like the curses display does (a stray code before a bold lost the "
         "bold in the logger and relay).",
         [("/eval /exec -sh printf '%s\\n' '${modifier:color_encode_ansi,,a1${esc:\\x1b}${color:bold}a2}' | cat -v",
           "`a1^Aa2`", "`a1^[[1ma2`")],
         "In the encoder, for a stray code in a stored line; since commit 20 removes a lone ESC, "
         "`/exec` output can no longer put one there (before commit 20, `hw/esc-esc` showed it on "
         "the gui-ansi path)."),
    22: ("On screen, a color without \"keep attributes\" (`|`), like `red` or `/cyan`, removes "
         "the attributes set before it; the encoder now tracks the attributes enabled in its "
         "output and removes them (codes 22, 23, 24, 25, 27), so bold, italic, reverse video... "
         "do not leak into the logger and relay output. This bug is also on `main`.",
         [("/eval /exec -sh printf '%s\\n' '${modifier:color_encode_ansi,,${color:!brown}a1${color:/cyan}b2}' | cat -v",
           "`^[[7m^[[33ma1^[[3m^[[36mb2` (reverse video kept)",
           "`^[[7m^[[33ma1^[[27m^[[3m^[[36mb2`")], None),
}


# Why a commit breaks cases that a later commit fixes again.
BROKEN_NOTES = {
    4: ("This commit fixes the screen, which these cases compare the logger with. For example "
        "`${color:*gray}a1${color:.yellow}b2${color:|cyan}c3` with `color_basic_force_bold`: "
        "before this commit, `|cyan` kept the bold that showed light yellow, so the screen "
        "showed `c3` in light cyan; now it is dark cyan. The logger still writes light cyan, "
        "because the encoder keeps the bold of `*gray` after `.yellow` (the bug fixed by "
        "commit 22, also on `main`)."),
}


DISCUSSION = [
    "- Commit 5: the encoder only knows the bold/dim state inside the string being encoded.",
    "- Commit 9: `^B^B` is used as separator, a common IRC idiom; colors are not sent again when",
    "  they don't change, except after IRC codes or a new line in the text (a long line split in",
    "  several IRC messages by WeeChat does not send the colors again).",
    "- Commit 11: ANSI dim (2) is still converted to \"remove bold\" for IRC (IRC has no dim), as",
    "  an existing test expects.",
    "- Commit 17: the regex is matched on an ASCII copy of each line instead of being compiled",
    "  with locale \"C\": the C libraries do not all use the locale of `regcomp` (musl, BSD and",
    "  macOS may use the locale of `regexec`), and changing the locale is global to the process.",
    "  The cost is one copy of each decoded line.",
    "- Commit 20: an unterminated OSC or DCS string is removed until the end of the line, like a",
    "  terminal which waits for the terminator.",
]

HARNESS_CHOICES = [
    "- SGR 21 is decoded as \"remove bold\" (for compatibility), while ECMA-48 and xterm use it",
    "  for double underline (`hw/sgr21`, and the encoder no longer writes 21 since commit 5).",
    "- On the irc path, SGR 2 removes bold, so the result depends on the order of 1 and 2: `2;1`",
    "  is bold, `1;2` is not (`hw/dim-then-bold`, and the 128 `ti/linux/sgr/*` cases with dim and",
    "  bold: linux's `sgr` writes `2;1`).",
    "- DECSTR (`CSI ! p`, soft reset) is removed without resetting the attributes, while a",
    "  terminal resets them (libvterm pen test).",
    "- Bold does not brighten colors 0-7 (libvterm's `bold_is_highbright`; xterm's `boldColors`).",
    "- IRC formatting codes in the output of a command pass through `/exec -o`, because a",
    "  command may print IRC formatting on purpose (`toilet --irc`, cases `prog/toilet-irc-*` and",
    "  `hw/irc-format/*`); SI is kept as the IRC reset `^O` and followed by the ANSI attributes",
    "  and colors (commit 19). A program that prints such a byte by accident changes the IRC",
    "  formatting.",
    "- C1 controls encoded in UTF-8 (U+0080-U+009F, for example U+009B as CSI) are kept as text;",
    "  terminals differ (xterm in UTF-8 mode treats them as controls) (`hw/utf8/c1-*`).",
    "- With `weechat.look.color_real_white` off, white is shown in the default color (with",
    "  `color_basic_force_bold`, plus the bold that shows a light color), but the logger and",
    "  relay keep white (15): real_white is a terminal workaround, and logs keep the real color",
    "  (display paths, reported as `diverge`).",
    "- Where ECMA-48 says nothing, the reference follows the branch: RGB components are clamped",
    "  to 0-255, values above 65535 are ignored, a palette index above 255 is ignored but its",
    "  parameters are consumed, and an incomplete or unknown color type after 38/48/58 consumes",
    "  the remaining parameters (like VTE and kitty).",
]


ALL_PATHS = ("gui", "gui-ansi", "irc", "gui-strip", "irc-strip", "gui-keep", "irc-keep",
             "print", "display", "display-headless")


def group(key: str) -> str:
    parts = key.split("/")
    if parts[0] == "hw":
        return key
    if parts[0] == "ti":
        return "/".join(parts[:3]) + "/*"
    return parts[0] + "/" + parts[1] + ("/*" if parts[0] in ("ar", "prog", "lvp") else "")


lines = []
add = lines.append
base = summary[0]
add("# Fixes on the fix-ansi-colors branch")
add("")
add(f"WeeChat branch `fix-ansi-colors` ({len(summary) - 1} commits) on its base `{base['commit']}` (origin/main).")
add("For each commit: what it fixes, how to reproduce the bug, and the cases of this")
add("harness that it makes pass.")
add("")
add("The cases are measured, not chosen by hand: `tools/fixes_by_commit.py` built the base and")
add("each commit, ran every case on every path (`gui`, `gui-ansi`, `irc` with the default")
add("`/exec -color auto`; strip: `gui-strip` and `irc-strip` with `-color strip`; keep: `gui-keep`")
add("and `irc-keep` with `-color ansi`; print: `/print` of WeeChat colors through the logger;")
add("display: generated WeeChat colors, screen of a curses WeeChat in tmux against the logger of")
add("that WeeChat and of weechat-headless; see the README),")
add("and listed the cases that each commit turns from fail to pass (or to a known divergence).")
# For each case a commit breaks: the later commit that fixes it again.
fixed_again = {}
for index, entry in enumerate(summary):
    for item in entry.get("broken", []):
        fixed_again[(entry["number"], item)] = next(
            (later["number"] for later in summary[index + 1:] if item in later["fixed"]), None)
broken_total = sum(len(entry.get("broken", [])) for entry in summary)
if not broken_total:
    add("No commit makes a passing case fail.")
else:
    add(f"{broken_total} cases fail after a commit where they passed before; each section says which,")
    add("and which later commit fixes them again.")
add("")
add("| # | Commit | Fix | Cases fixed (gui / gui-ansi / irc / strip / keep / print / display) | Failures after |")
add("|---|--------|-----|-------------------------------------------------------------------:|---------------:|")
add(f"| | `{base['commit']}` | base | | {base['failures']} |")
for entry in summary[1:]:
    counts = Counter(item.split(" ", 1)[0] for item in entry["fixed"])
    strip = counts["gui-strip"] + counts["irc-strip"]
    keep = counts["gui-keep"] + counts["irc-keep"]
    display = counts["display"] + counts["display-headless"]
    cells = " / ".join(str(value) for value in (counts["gui"], counts["gui-ansi"], counts["irc"],
                                                  strip, keep, counts["print"], display))
    if not entry["fixed"]:
        cells = "none"
    add(f"| {entry['number']} | `{entry['commit']}` | {entry['subject'].split(': ', 1)[1]} | "
        f"{cells} | {entry['failures']} |")
add("")
add("A case is counted once per path where it is fixed.")
add("")
for entry in summary[1:]:
    number = entry["number"]
    what, repros, no_case = FIXES[number]
    add(f"## {number}. {entry['subject']}")
    add("")
    add(f"Commit `{entry['commit']}`. {what}")
    add("")
    add("| Reproduce | Before | After |")
    add("|-----------|--------|-------|")
    for command, before, after, *condition in repros:
        cells = (f"`{command}`" + (f" ({condition[0]})" if condition else ""), before, after)
        add("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    add("")
    broken = entry.get("broken", [])
    if broken:
        add(f"Cases that pass before this commit and fail after it ({len(broken)}):")
        add("")
        for item in broken:
            path, key = item.split(" ", 1)
            again = fixed_again[(number, item)]
            add(f"- `{key}` ({path}), " + (f"fixed again by commit {again}" if again
                                         else "still failing at the last commit"))
        if number in BROKEN_NOTES:
            add("")
            add(BROKEN_NOTES[number])
        add("")
    if not entry["fixed"]:
        add(f"No case: {no_case}")
        add("")
        continue
    groups = defaultdict(set)
    for item in entry["fixed"]:
        path, key = item.split(" ", 1)
        groups[group(key)].add(path)
    by_group = defaultdict(Counter)
    for item in entry["fixed"]:
        path, key = item.split(" ", 1)
        by_group[group(key)][path] += 1
    add(f"Cases fixed ({len(entry['fixed'])}):")
    add("")
    for name in sorted(groups):
        counts = by_group[name]
        if name.endswith("/*") or name.startswith(("lvx/", "lvp/")):
            paths = ", ".join(f"{path} {counts[path]}" for path in ALL_PATHS if counts[path])
        else:
            paths = ", ".join(path for path in ALL_PATHS if counts[path])
        add(f"- `{name}` ({paths})")
    add("")
add("## Choices open to discussion")
add("")
add("From the description of the pull request:")
add("")
for item in DISCUSSION:
    add(item)
add("")
add("Accepted by the harness as intended behavior (listed in `ansitest/divergences.py`, reported")
add("as `diverge`, or encoded in the expected results):")
add("")
for item in HARNESS_CHOICES:
    add(item)
add("")
open(output_path, "w").write("\n".join(lines))
print(f"wrote {output_path}: {len(lines)} lines")
