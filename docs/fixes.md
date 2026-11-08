# Fixes on the fix-ansi-colors branch

WeeChat branch `fix-ansi-colors` (22 commits) on its base `bf66d9b2bc53` (origin/main).
For each commit: what it fixes, how to reproduce the bug, and the cases of this
harness that it makes pass.

The cases are measured, not chosen by hand: `tools/fixes_by_commit.py` built the base and
each commit, ran every case on every path (`gui`, `gui-ansi`, `irc` with the default
`/exec -color auto`; strip: `gui-strip` and `irc-strip` with `-color strip`; keep: `gui-keep`
and `irc-keep` with `-color ansi`; print: `/print` of WeeChat colors through the logger;
display: generated WeeChat colors, screen of a curses WeeChat in tmux against the logger of
that WeeChat and of weechat-headless; see the README),
and listed the cases that each commit turns from fail to pass (or to a known divergence).
6 cases fail after a commit where they passed before; each section says which,
and which later commit fixes them again.

| # | Commit | Fix | Cases fixed (gui / gui-ansi / irc / strip / keep / print / display) | Failures after |
|---|--------|-----|-------------------------------------------------------------------:|---------------:|
| | `bf66d9b2bc53` | base | | 10889 |
| 1 | `3cbb9c06214f` | fix empty parameters in ANSI colors | 2 / 2 / 2 / 0 / 0 / 0 / 0 | 10883 |
| 2 | `0925412490d5` | ignore underline color in ANSI colors | 2 / 2 / 1 / 0 / 0 / 0 / 0 | 10878 |
| 3 | `aa058997ee88` | fix tracking of attributes when an attribute is removed | none | 10878 |
| 4 | `a9ed000b171e` | keep bold of light colors when bold attribute is removed | 0 / 0 / 0 / 0 / 0 / 0 / 10 | 10874 |
| 5 | `282c4e60f1cd` | fix ANSI code 22 to remove both bold and dim | 8 / 1 / 0 / 0 / 0 / 0 / 599 | 10266 |
| 6 | `18a1df8e731e` | keep attributes when decoding ANSI default text color | 3 / 0 / 0 / 0 / 0 / 0 / 0 | 10263 |
| 7 | `b70a8d323084` | remove control sequences when decoding ANSI colors | 53 / 54 / 53 / 516 / 0 / 0 / 0 | 9587 |
| 8 | `fc5c0e79d76b` | clamp RGB components of ANSI colors to 0-255 | 1 / 1 / 0 / 0 / 0 / 0 / 0 | 9585 |
| 9 | `ea97b4d3b0aa` | send unambiguous color codes when converting ANSI colors | 0 / 0 / 4128 / 0 / 0 / 0 / 0 | 5457 |
| 10 | `0e2c1db7db39` | ignore invalid colors in ANSI colors | 5 / 4 / 4 / 0 / 0 / 0 / 0 | 5444 |
| 11 | `62af5e7011dc` | convert ANSI reverse video to IRC reverse video | 0 / 0 / 2084 / 0 / 0 / 0 / 0 | 3360 |
| 12 | `4a19bdc01618` | convert bar delimiter color to ANSI text color | none | 3360 |
| 13 | `97a14a1f6b44` | remove other escape sequences when decoding ANSI colors | 121 / 48 / 121 / 242 / 0 / 0 / 0 | 2828 |
| 14 | `17bac2b6be2e` | decode ANSI colors with colons (issue #1364) | 204 / 204 / 204 / 0 / 0 / 0 / 0 | 2216 |
| 15 | `14b9c10c6973` | fix slow decoding of ANSI colors with many parameters | none | 2216 |
| 16 | `ebc08760468a` | fix slow decoding of ANSI colors with many escape sequences | none | 2216 |
| 17 | `c823a8e09c4e` | remove ANSI escape sequences containing non-UTF-8 bytes | 2 / 2 / 2 / 4 / 0 / 0 / 0 | 2206 |
| 18 | `bd6b317d829d` | decode ANSI rapid blink as blink | 1 / 1 / 0 / 0 / 0 / 0 / 0 | 2204 |
| 19 | `5893f484d5ce` | fix chars SI and SO when decoding ANSI colors | 0 / 0 / 577 / 0 / 0 / 0 / 0 | 1627 |
| 20 | `618b3cdf165c` | remove unterminated and cancelled ANSI escape sequences | 22 / 21 / 19 / 44 / 0 / 0 / 0 | 1521 |
| 21 | `8775c5e26dcd` | keep char after invalid attribute when encoding ANSI colors | none | 1521 |
| 22 | `8cc5464f79a5` | fix attributes kept after a color when encoding ANSI colors | 0 / 0 / 0 / 0 / 0 / 0 / 1521 | 0 |

A case is counted once per path where it is fixed.

## 1. core, irc: fix empty parameters in ANSI colors

Commit `3cbb9c06214f`. An empty parameter means 0 (reset, ECMA-48); empty parameters were ignored. Empty arguments of 38/48 are 0 too.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[1mbold\033[;m normal\n'` | "normal" is bold | "normal" is not bold |

Cases fixed (6):

- `hw/empty-param-middle` (gui, gui-ansi, irc)
- `hw/empty-param-trailing` (gui, gui-ansi, irc)

## 2. core, irc: ignore underline color in ANSI colors

Commit `0925412490d5`. `58;5;N` and `58;2;R;G;B` (underline color) are consumed as a unit and ignored; their arguments were decoded as other attributes.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[4;58;2;255;0;0munderline\033[0m normal\n'` | "underline" is not underlined (`2` dim, `0` reset) | "underline" is underlined |

Cases fixed (5):

- `hw/ulcolor-5` (gui, gui-ansi)
- `hw/ulcolor-semicolon` (gui, gui-ansi, irc)

## 3. core: fix tracking of attributes when an attribute is removed

Commit `aa058997ee88`. Removing an attribute cleared all the attributes tracked for the current color (`&= !style` instead of `&= ~style`, since 2008).

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /print ${color:reverse}rev1 ${color:-italic}x${esc:\x01}y rev2` | "y rev2" loses reverse video | all reverse video |

No case: The bug is in the curses display's tracking of attributes, not in the stored line that the gui path reads, and `/exec` does not produce this input.

## 4. core: keep bold of light colors when bold attribute is removed

Commit `a9ed000b171e`. On a terminal with less than 16 colors (or with `weechat.look.color_basic_force_bold`), light colors are displayed with bold; this bold is now tracked separately from the bold attribute (for custom colors and colors of options), so removing the bold attribute keeps a light color light, and another color drops the bold of the previous one (also for a light option color with the bold attribute, like `*lightred`).

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /print ${color:darkgray}gray ${color:bold}bold${color:-bold} gray` (with `TERM=xterm`, 8 colors) | last "gray" is black | last "gray" is gray |
| `/eval /print ${color:chat_highlight}hl ${color:bold}b${color:-bold} after` (with `TERM=xterm`, 8 colors) | "after" is brown | "after" is yellow |

Cases that pass before this commit and fail after it (6):

- `display/xterm-256color-fbon-rwoff/random/1` (display), fixed again by commit 22
- `display/xterm-256color-fbon-rwon/random/1` (display), fixed again by commit 22
- `display/xterm-fbon-rwoff/random/1` (display), fixed again by commit 22
- `display/xterm-fbon-rwon/random/1` (display), fixed again by commit 22
- `display/xterm-256color-fbon-rwoff/random/1` (display-headless), fixed again by commit 22
- `display/xterm-256color-fbon-rwon/random/1` (display-headless), fixed again by commit 22

This commit fixes the screen, which these cases compare the logger with. For example `${color:*gray}a1${color:.yellow}b2${color:|cyan}c3` with `color_basic_force_bold`: before this commit, `|cyan` kept the bold that showed light yellow, so the screen showed `c3` in light cyan; now it is dark cyan. The logger still writes light cyan, because the encoder keeps the bold of `*gray` after `.yellow` (the bug fixed by commit 22, also on `main`).

Cases fixed (10):

- `display/xterm-256color-fbon-rwoff` (display, display-headless)
- `display/xterm-256color-fbon-rwon` (display, display-headless)
- `display/xterm-fbon-rwoff` (display)
- `display/xterm-fbon-rwon` (display)

## 5. core: fix ANSI code 22 to remove both bold and dim

Commit `282c4e60f1cd`. 22 (normal intensity) removed only dim. The encoder (`color_encode_ansi`, used by the relay api and the logger) uses 22 instead of 21 (double underline in most terminals) for `-bold`, and sets bold or dim again if the other one is still set.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[1mbold\033[22m normal\n'` | "normal" is bold | "normal" is not bold |
| `/exec node -e "console.log(require('util').inspect({a:null,b:1},{colors:true}))"` | `null, b: 1 }` is bold | only `null` is bold |

Cases fixed (608):

- `display/xterm-256color-fboff-rwoff` (display, display-headless)
- `display/xterm-256color-fboff-rwon` (display, display-headless)
- `display/xterm-256color-fbon-rwoff` (display, display-headless)
- `display/xterm-256color-fbon-rwon` (display, display-headless)
- `display/xterm-fboff-rwoff` (display)
- `display/xterm-fboff-rwon` (display)
- `display/xterm-fbon-rwoff` (display)
- `display/xterm-fbon-rwon` (display)
- `hw/attrs-off-one-by-one` (gui)
- `hw/bold-light-color` (gui)
- `hw/sgr21` (gui-ansi)
- `hw/sgr22-bold-dim` (gui)
- `hw/sgr22-keeps-color` (gui)
- `hw/utf8/between-attrs` (gui)
- `hw/utf8/combining` (gui)
- `lvp/30state_pen/*` (gui 1)
- `prog/node-inspect/*` (gui 1)

## 6. core: keep attributes when decoding ANSI default text color

Commit `18a1df8e731e`. 39 is decoded as `|default` like 30-37; it removed all attributes. Programs often end bold colored text with `\e[39m\e[22m`.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[1mbold \033[31mred\033[39m bold\n'` | last "bold" is not bold | last "bold" is bold |
| `/exec -sh echo '{"key":[1]}' \| jq -C -c .` | braces and `:` are not bold | braces and `:` are bold (`1;39`) |

Cases fixed (3):

- `hw/default-fg-keeps-attrs` (gui)
- `prog/jq/*` (gui 1)
- `prog/node-styletext/*` (gui 1)

## 7. core, irc: remove control sequences when decoding ANSI colors

Commit `b70a8d323084`. The regex follows the ECMA-48 grammar of control sequences, so they are all removed (for example cursor style `\e[2 q`); only SGR sequences with parameters made of digits, `;` and `:` are decoded (`\e[?4m` and `\e[1;>4m` were decoded as resets). The regex is also the value of info `color_ansi_regex`.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf 'A\033[2 qB\033[?4mC\033[=5uD\n'` | `A2 qBC=5uD` | `ABCD` |

Cases fixed (676):

- `ar/urxvt/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `hw/bg256/48:5:21` (gui-strip, irc-strip)
- `hw/bgrgb/48:2:0:18:52:86` (gui-strip, irc-strip)
- `hw/bgrgb/48:2:18:52:86` (gui-strip, irc-strip)
- `hw/bgrgb/48:2::18:52:86` (gui-strip, irc-strip)
- `hw/fg-incomplete-colon` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/fg256-out-of-range` (gui-ansi, gui-strip, irc-strip)
- `hw/fg256/38:5:196` (gui-strip, irc-strip)
- `hw/fgrgb/38:2:0:255:136:0` (gui-strip, irc-strip)
- `hw/fgrgb/38:2:255:136:0` (gui-strip, irc-strip)
- `hw/fgrgb/38:2::255:136:0` (gui-strip, irc-strip)
- `hw/noise/csi-cursor-style` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-da2` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-decrqm` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-decsca` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-decstr` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-intermediate-m` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-private-eq-u` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/csi-private-gt-m` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/rgb-clamp-colon` (gui-strip, irc-strip)
- `hw/sgr-subparams-ignored` (gui-strip, irc-strip)
- `hw/ulcolor-colon` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/underline-sub-0` (gui-strip, irc-strip)
- `hw/underline-sub-00` (gui-strip, irc-strip)
- `hw/underline-sub-1` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/underline-sub-2` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/underline-sub-3` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/underline-sub-4` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/underline-sub-5` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/underline-sub-empty` (gui-strip, irc-strip)
- `hw/underline-sub-in-list` (gui-strip, irc-strip)
- `hw/utf8/colon-color` (gui-strip, irc-strip)
- `lvp/30state_pen/*` (gui 1, gui-ansi 1, irc 1, gui-strip 4, irc-strip 4)
- `lvp/64screen_pen/*` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/CSI 1 arg 1 sub` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/CSI SP` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/CSI greater` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `prog/tput-direct/*` (gui-strip 1, irc-strip 1)
- `ti/linux/param/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/rxvt-unicode-256color/param/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/screen/param/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/tmux-256color/Smulx/*` (gui 5, gui-ansi 5, irc 5, gui-strip 6, irc-strip 6)
- `ti/tmux-256color/param/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/xterm-256color/param/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/xterm-direct/combo/*` (gui-strip 162, irc-strip 162)
- `ti/xterm-direct/param/*` (gui 4, gui-ansi 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/xterm-direct/setab/*` (gui-strip 11, irc-strip 11)
- `ti/xterm-direct/setaf/*` (gui-strip 11, irc-strip 11)

## 8. core, irc: clamp RGB components of ANSI colors to 0-255

Commit `fc5c0e79d76b`. A RGB component > 255 overflowed into the other components; components are clamped to 0-255.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[38;2;0;256;0mgreen\033[0m\n'` | black | green |

Cases fixed (2):

- `hw/rgb-clamp` (gui, gui-ansi)

## 9. irc: send unambiguous color codes when converting ANSI colors

Commit `ea97b4d3b0aa`. IRC colors are sent unambiguously: a background with the text color (`^CFF,BB`), colors only when they change, `^B^B` before text starting with `,<digit>` after a text color sent alone, and the end of a background as `^C^CFF` so that `irc.color.mirc_remap` still applies. `\e[m` also resets attributes.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec -o msgcat --color=test` (in an IRC channel) | backgrounds sent alone (`^C,01`): `,01` shown as text | no stray text |
| `/exec -o -sh printf 'a,5 b\n' \| grep --color=always ',5'` | `,5` disappears, red on red | `,5` shown in red |

Cases fixed (4128):

- `ar/commonCodes/*` (irc 10)
- `hw/background-end` (irc)
- `hw/bg256/48;5;21` (irc)
- `hw/bgrgb/48;2;18;52;86` (irc)
- `hw/bright` (irc)
- `hw/comma-after-fg` (irc)
- `hw/comma-digit-after-reset-bg` (irc)
- `hw/default-colors` (irc)
- `hw/default-fg-keeps-attrs` (irc)
- `hw/digit-after-color` (irc)
- `hw/fg256/38;5;196` (irc)
- `hw/fgrgb/38;2;255;136;0` (irc)
- `hw/irc-format/raw-color-then-ansi-bg` (irc)
- `hw/utf8/digits-after-color` (irc)
- `hw/utf8/rgb-and-256` (irc)
- `lvp/30state_pen/*` (irc 1)
- `lvp/64screen_pen/*` (irc 1)
- `prog/grep-comma/*` (irc 1)
- `prog/img2txt-ansi-fstein-30-bars/*` (irc 9)
- `prog/img2txt-ansi-fstein-30-rainbow/*` (irc 9)
- `prog/img2txt-ansi-fstein-60-bars/*` (irc 17)
- `prog/img2txt-ansi-fstein-60-rainbow/*` (irc 4)
- `prog/img2txt-ansi-none-30-bars/*` (irc 9)
- `prog/img2txt-ansi-none-30-rainbow/*` (irc 9)
- `prog/img2txt-ansi-none-60-bars/*` (irc 18)
- `prog/img2txt-ansi-none-60-rainbow/*` (irc 18)
- `prog/img2txt-ansi-ordered4-30-bars/*` (irc 9)
- `prog/img2txt-ansi-ordered4-30-rainbow/*` (irc 9)
- `prog/img2txt-ansi-ordered4-60-bars/*` (irc 11)
- `prog/img2txt-ansi-ordered4-60-rainbow/*` (irc 1)
- `prog/img2txt-utf8-fstein-30-bars/*` (irc 9)
- `prog/img2txt-utf8-fstein-30-rainbow/*` (irc 6)
- `prog/img2txt-utf8-fstein-60-bars/*` (irc 16)
- `prog/img2txt-utf8-fstein-60-rainbow/*` (irc 3)
- `prog/img2txt-utf8-none-30-bars/*` (irc 9)
- `prog/img2txt-utf8-none-30-rainbow/*` (irc 9)
- `prog/img2txt-utf8-none-60-bars/*` (irc 18)
- `prog/img2txt-utf8-none-60-rainbow/*` (irc 14)
- `prog/img2txt-utf8-ordered4-30-bars/*` (irc 6)
- `prog/img2txt-utf8-ordered4-30-rainbow/*` (irc 8)
- `prog/img2txt-utf8-ordered4-60-bars/*` (irc 11)
- `prog/jq/*` (irc 1)
- `prog/msgcat-test/*` (irc 149)
- `prog/node-inspect/*` (irc 1)
- `prog/node-styletext/*` (irc 1)
- `ti/linux/combo/*` (irc 36)
- `ti/linux/setab/*` (irc 8)
- `ti/linux/setaf/*` (irc 8)
- `ti/rxvt-unicode-256color/combo/*` (irc 576)
- `ti/rxvt-unicode-256color/setab/*` (irc 256)
- `ti/rxvt-unicode-256color/setaf/*` (irc 256)
- `ti/screen/combo/*` (irc 36)
- `ti/screen/setab/*` (irc 8)
- `ti/screen/setaf/*` (irc 8)
- `ti/tmux-256color/combo/*` (irc 720)
- `ti/tmux-256color/setab/*` (irc 256)
- `ti/tmux-256color/setaf/*` (irc 256)
- `ti/xterm-256color/combo/*` (irc 720)
- `ti/xterm-256color/setab/*` (irc 256)
- `ti/xterm-256color/setaf/*` (irc 256)
- `ti/xterm-direct/combo/*` (irc 45)
- `ti/xterm-direct/setab/*` (irc 8)
- `ti/xterm-direct/setaf/*` (irc 8)

## 10. core, irc: ignore invalid colors in ANSI colors

Commit `0e2c1db7db39`. The arguments of 38, 48 and 58 are parsed by one function: an incomplete color or an unknown type ignores the remaining parameters, a terminal color > 255 is ignored, and numbers out of range are ignored instead of truncated (`4294967297` was `1`, bold).

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[31mred\033[58;2;1;0m still red\n'` | " still red" is not red | " still red" is red |

Cases fixed (13):

- `hw/fg-incomplete-5` (gui, gui-ansi)
- `hw/fg-incomplete-rgb` (gui, gui-ansi, irc)
- `hw/fg-unknown-type` (gui, gui-ansi, irc)
- `hw/fg256-out-of-range` (gui, irc)
- `hw/number-out-of-range` (gui, gui-ansi, irc)

## 11. irc: convert ANSI reverse video to IRC reverse video

Commit `62af5e7011dc`. Codes 7 and 27 (reverse video) were ignored when converting to IRC.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /print ${modifier:irc_color_decode,1,${modifier:irc_color_decode_ansi,1,${esc:\e[7m}rev${esc:\e[27m} normal}}` | no reverse video | "rev" in reverse video |

Cases fixed (2084):

- `ar/commonCodes/*` (irc 1)
- `hw/attrs-off-one-by-one` (irc)
- `hw/irc-format/raw-reverse-then-ansi` (irc)
- `hw/reverse` (irc)
- `hw/rgb-then-attrs` (irc)
- `hw/utf8/before-reset` (irc)
- `lvp/30state_pen/*` (irc 1)
- `lvp/64screen_pen/*` (irc 1)
- `ti/linux/all-attributes/*` (irc 1)
- `ti/linux/combo/*` (irc 9)
- `ti/linux/rev-sgr0/*` (irc 1)
- `ti/linux/sgr/*` (irc 192)
- `ti/linux/smso-rmso/*` (irc 1)
- `ti/rxvt-unicode-256color/all-attributes/*` (irc 1)
- `ti/rxvt-unicode-256color/combo/*` (irc 144)
- `ti/rxvt-unicode-256color/rev-sgr0/*` (irc 1)
- `ti/rxvt-unicode-256color/sgr/*` (irc 384)
- `ti/rxvt-unicode-256color/smso-rmso/*` (irc 1)
- `ti/screen/all-attributes/*` (irc 1)
- `ti/screen/combo/*` (irc 9)
- `ti/screen/rev-sgr0/*` (irc 1)
- `ti/screen/sgr/*` (irc 64)
- `ti/tmux-256color/all-attributes/*` (irc 1)
- `ti/tmux-256color/combo/*` (irc 144)
- `ti/tmux-256color/rev-sgr0/*` (irc 1)
- `ti/tmux-256color/sgr/*` (irc 192)
- `ti/tmux-256color/smso-rmso/*` (irc 1)
- `ti/xterm-256color/all-attributes/*` (irc 1)
- `ti/xterm-256color/combo/*` (irc 144)
- `ti/xterm-256color/rev-sgr0/*` (irc 1)
- `ti/xterm-256color/sgr/*` (irc 384)
- `ti/xterm-256color/smso-rmso/*` (irc 1)
- `ti/xterm-direct/all-attributes/*` (irc 1)
- `ti/xterm-direct/combo/*` (irc 9)
- `ti/xterm-direct/rev-sgr0/*` (irc 1)
- `ti/xterm-direct/sgr/*` (irc 384)
- `ti/xterm-direct/smso-rmso/*` (irc 1)

## 12. core: convert bar delimiter color to ANSI text color

Commit `4a19bdc01618`. The bar delimiter color was converted to a background color by the encoder, although it is displayed as a text color.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /exec -sh printf '%s\n' '${modifier:color_encode_ansi,,${color:bar_delim}(}' \| cat -v` | `^[[48;5;22m` | `^[[38;5;22m` |

No case: In the encoder (`color_encode_ansi`) for bar colors, which `/exec` output never contains.

## 13. core, irc: remove other escape sequences when decoding ANSI colors

Commit `97a14a1f6b44`. Operating system commands (window title, hyperlinks), device control strings and escape sequences like `\e7`, `\e=` or `\e#8` were displayed as text.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf 'A \033]8;;https://weechat.org\033\\link\033]8;;\033\\ \033]0;title\007B\n'` | URL and title shown as text | `A link B` |
| `/exec -sh ls --hyperlink=always` | hyperlinks shown as text | hyperlinks removed |

Cases fixed (532):

- `ar/ansiCompatible/*` (gui 9, gui-ansi 5, irc 9, gui-strip 9, irc-strip 9)
- `ar/commonCodes/*` (gui 6, irc 6, gui-strip 6, irc-strip 6)
- `ar/otherCode/*` (gui 8, gui-ansi 5, irc 8, gui-strip 8, irc-strip 8)
- `ar/urxvt/*` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `ar/vt52Codes/*` (gui 16, irc 16, gui-strip 16, irc-strip 16)
- `hw/noise-between-sgr` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/apc-kitty` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/charset-g2` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/charset-g3` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/dcs-decrqss` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/dcs-sixel` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/esc-decaln` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/esc-deckpam` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-decrc` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-decsc` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-hts` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-ind` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-nel` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-ri` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-ris` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-s7c1t` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/esc-ss2` (gui, irc, gui-strip, irc-strip)
- `hw/noise/esc-ss3` (gui, irc, gui-strip, irc-strip)
- `hw/noise/osc-empty` (gui, irc, gui-strip, irc-strip)
- `hw/noise/osc0-bel` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/osc2-st` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/osc52` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/osc8` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/osc8-end` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/pm` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/noise/sos` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/sgr-around-hyperlink` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/utf8/dcs` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/utf8/osc-emoji-st` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/utf8/osc-title` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/utf8/osc8-link` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `lvx/APC ST (7bit)` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/C1 7bit` (gui 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/DCS ST (7bit)` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/Escape` (gui 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/OSC BEL` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/OSC BEL without semicolon` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/OSC ST (7bit)` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/OSC ST without semicolon` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/OSC in parts` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/PM ST (7bit)` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/SOS ST (7bit)` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/Split write of 7bit ST` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `prog/ls-hyperlink/*` (gui 5, gui-ansi 5, irc 5, gui-strip 5, irc-strip 5)
- `ti/linux/str/*` (gui 4, irc 4, gui-strip 4, irc-strip 4)
- `ti/rxvt-unicode-256color/str/*` (gui 6, gui-ansi 1, irc 6, gui-strip 6, irc-strip 6)
- `ti/screen/str/*` (gui 6, irc 6, gui-strip 6, irc-strip 6)
- `ti/tmux-256color/str/*` (gui 7, gui-ansi 1, irc 7, gui-strip 7, irc-strip 7)
- `ti/xterm-256color/str/*` (gui 5, irc 5, gui-strip 5, irc-strip 5)
- `ti/xterm-direct/str/*` (gui 5, irc 5, gui-strip 5, irc-strip 5)

## 14. core, irc: decode ANSI colors with colons (issue #1364)

Commit `17bac2b6be2e`. Sub-parameters (ITU T.416, used by kitty, foot, tmux, Neovim, `tput` with `-direct` terminals) are decoded: `38:5:N`, `38:2:R:G:B`, `38:2:<color space>:R:G:B`, underline style `4:N` (`4:0` is no underline), `58:...` ignored, other parameters use only their value (`1:2` is `1`).

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[38:2::255:136:0morange\033[0m \033[4:3mcurly\033[4:0m end\n'` | sequences shown as text | "orange" in orange, "curly" underlined |
| `/exec -sh TERM=xterm-direct tput setaf 16711680; echo red` | sequence shown as text | "red" in red |

Cases fixed (612):

- `hw/bg256/48:5:21` (gui, gui-ansi, irc)
- `hw/bgrgb/48:2:0:18:52:86` (gui, gui-ansi, irc)
- `hw/bgrgb/48:2:18:52:86` (gui, gui-ansi, irc)
- `hw/bgrgb/48:2::18:52:86` (gui, gui-ansi, irc)
- `hw/fg256/38:5:196` (gui, gui-ansi, irc)
- `hw/fgrgb/38:2:0:255:136:0` (gui, gui-ansi, irc)
- `hw/fgrgb/38:2:255:136:0` (gui, gui-ansi, irc)
- `hw/fgrgb/38:2::255:136:0` (gui, gui-ansi, irc)
- `hw/rgb-clamp-colon` (gui, gui-ansi, irc)
- `hw/sgr-subparams-ignored` (gui, gui-ansi, irc)
- `hw/underline-sub-0` (gui, gui-ansi, irc)
- `hw/underline-sub-00` (gui, gui-ansi, irc)
- `hw/underline-sub-empty` (gui, gui-ansi, irc)
- `hw/underline-sub-in-list` (gui, gui-ansi, irc)
- `hw/utf8/colon-color` (gui, gui-ansi, irc)
- `lvp/30state_pen/*` (gui 3, gui-ansi 3, irc 3)
- `prog/tput-direct/*` (gui 1, gui-ansi 1, irc 1)
- `ti/tmux-256color/Smulx/*` (gui 1, gui-ansi 1, irc 1)
- `ti/xterm-direct/combo/*` (gui 162, gui-ansi 162, irc 162)
- `ti/xterm-direct/setab/*` (gui 11, gui-ansi 11, irc 11)
- `ti/xterm-direct/setaf/*` (gui 11, gui-ansi 11, irc 11)

## 15. core, irc: fix slow decoding of ANSI colors with many parameters

Commit `14b9c10c6973`. Each parameter was added with `strcat`, so N parameters took a time proportional to N².

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec -sh python3 -c "print('\033[' + ';'.join(['1'] * 1000000) + 'mX')"` | WeeChat frozen for about 30 seconds | decoded in less than a second |

No case: Speed: the harness checks results, not time (`hw/many-params-1000` checks that the result of 1000 parameters is right).

## 16. core, irc: fix slow decoding of ANSI colors with many escape sequences

Commit `ebc08760468a`. `regexec` computed the length of the rest of the line at each sequence (and core copied the string), so N sequences took a time proportional to N²; the remaining length is given to `regexec` (`REG_STARTEND`, if available).

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec -sh python3 -c "print('\0337x' * 160000)"` | WeeChat frozen for about 4 seconds | decoded in less than a second |

No case: Speed: the harness checks results, not time.

## 17. core, irc: remove ANSI escape sequences containing non-UTF-8 bytes

Commit `c823a8e09c4e`. With a UTF-8 locale, the regex did not match bytes that are not valid UTF-8, so a window title in ISO-8859-1 was not removed. Escape sequences contain only ASCII chars: they are searched in a copy of the line where the other chars are replaced by `\x01` (same length), and the text is copied from the original line.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf 'A\033]0;t\351tle\007B\n'` | `A0;t?tle^GB` | `AB` |

Cases fixed (10):

- `hw/osc-title-latin1` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `lvx/SOS can contain any C0 or C1 code` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)

## 18. core: decode ANSI rapid blink as blink

Commit `bd6b317d829d`. Code 6 (rapid blink) was ignored; it is decoded like 5.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf '\033[6mblink\033[0m\n'` | no blink | "blink" blinks |

Cases fixed (2):

- `hw/rapid-blink` (gui, gui-ansi)

## 19. core, irc: fix chars SI and SO when decoding ANSI colors

Commit `5893f484d5ce`. terminfo sends SI and SO with some terminals (with `TERM=screen`, `tmux-256color` or `linux`, `sgr` ends with SI); they were kept as text, and SI is the IRC reset (`^O`), so the attributes set just before it were lost on IRC. They are now removed, except SI on IRC, which is kept (text already formatted for IRC can contain it) and followed by the attributes and colors of the ANSI sequences.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /print ${modifier:irc_color_decode,1,${modifier:irc_color_decode_ansi,1,${esc:\e[1m\x0f}bold}}` | "bold" is not bold (SI sent as `^O`, the IRC reset) | "bold" is bold |
| `/exec -o -sh TERM=screen tput sgr 0 0 0 0 0 1; echo bold` (in an IRC channel) | "bold" is not bold (`tput` emits `\e[0;1m` then SI) | "bold" is bold |

Cases fixed (577):

- `prog/tput-screen-sgr/*` (irc 1)
- `ti/linux/sgr/*` (irc 240)
- `ti/screen/sgr/*` (irc 104)
- `ti/tmux-256color/sgr/*` (irc 232)

## 20. core, irc: remove unterminated and cancelled ANSI escape sequences

Commit `618b3cdf165c`. A sequence cut before its end, cancelled by CAN, SUB or another escape sequence, and a lone ESC are removed instead of showing the rest as text; DEL is ignored after ESC and inside a control sequence (also in SGR sequences, which are still decoded), and OSC and DCS strings can also end with BEL. A char set designation without its final byte (`\e(` followed by a newline or a multibyte char) is removed without the char after it.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/exec printf 'a1\033]0;title\n'` | `a10;title` | `a1` |

Cases fixed (106):

- `hw/csi-unterminated` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/del-after-esc` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/del-after-intermediate` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/del-in-sgr` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/esc-esc` (gui, gui-ansi, gui-strip, irc-strip)
- `hw/lone-esc-end` (gui, gui-strip, irc-strip)
- `hw/osc-unterminated` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/utf8/charset-then-multibyte` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `hw/utf8/esc-then-multibyte` (gui, gui-ansi, gui-strip, irc-strip)
- `hw/utf8/osc-unterminated` (gui, gui-ansi, irc, gui-strip, irc-strip)
- `lvx/APC BEL` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/CAN cancels CSI, returns to normal mode` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/CAN cancels DCS, returns to normal mode` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/CAN cancels OSC, returns to normal mode` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/DCS BEL` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/DEL ignored within CSI` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/Escape cancels CSI, starts Escape` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/Escape cancels DCS, starts Escape` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/Escape cancels Escape, starts another` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/Escape cancels OSC, starts Escape` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/PM BEL` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)
- `lvx/SOS BEL` (gui 1, gui-ansi 1, irc 1, gui-strip 1, irc-strip 1)

## 21. core: keep char after invalid attribute when encoding ANSI colors

Commit `8775c5e26dcd`. The char after a set/remove attribute code is consumed by the encoder only if it is a valid attribute, like the curses display does (a stray code before a bold lost the bold in the logger and relay).

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /exec -sh printf '%s\n' '${modifier:color_encode_ansi,,a1${esc:\x1b}${color:bold}a2}' \| cat -v` | `a1^Aa2` | `a1^[[1ma2` |

No case: In the encoder, for a stray code in a stored line; since commit 20 removes a lone ESC, `/exec` output can no longer put one there (before commit 20, `hw/esc-esc` showed it on the gui-ansi path).

## 22. core: fix attributes kept after a color when encoding ANSI colors

Commit `8cc5464f79a5`. On screen, a color without "keep attributes" (`|`), like `red` or `/cyan`, removes the attributes set before it; the encoder now tracks the attributes enabled in its output and removes them (codes 22, 23, 24, 25, 27), so bold, italic, reverse video... do not leak into the logger and relay output. This bug is also on `main`.

| Reproduce | Before | After |
|-----------|--------|-------|
| `/eval /exec -sh printf '%s\n' '${modifier:color_encode_ansi,,${color:!brown}a1${color:/cyan}b2}' \| cat -v` | `^[[7m^[[33ma1^[[3m^[[36mb2` (reverse video kept) | `^[[7m^[[33ma1^[[27m^[[3m^[[36mb2` |

Cases fixed (1521):

- `display/xterm-256color-fboff-rwoff` (display, display-headless)
- `display/xterm-256color-fboff-rwon` (display, display-headless)
- `display/xterm-256color-fbon-rwoff` (display, display-headless)
- `display/xterm-256color-fbon-rwon` (display, display-headless)
- `display/xterm-fboff-rwoff` (display)
- `display/xterm-fboff-rwon` (display)
- `display/xterm-fbon-rwoff` (display)
- `display/xterm-fbon-rwon` (display)

## Choices open to discussion

From the description of the pull request:

- Commit 5: the encoder only knows the bold/dim state inside the string being encoded.
- Commit 9: `^B^B` is used as separator, a common IRC idiom; colors are not sent again when
  they don't change, except after IRC codes or a new line in the text (a long line split in
  several IRC messages by WeeChat does not send the colors again).
- Commit 11: ANSI dim (2) is still converted to "remove bold" for IRC (IRC has no dim), as
  an existing test expects.
- Commit 17: the regex is matched on an ASCII copy of each line instead of being compiled
  with locale "C": the C libraries do not all use the locale of `regcomp` (musl, BSD and
  macOS may use the locale of `regexec`), and changing the locale is global to the process.
  The cost is one copy of each decoded line.
- Commit 20: an unterminated OSC or DCS string is removed until the end of the line, like a
  terminal which waits for the terminator.

Accepted by the harness as intended behavior (listed in `ansitest/divergences.py`, reported
as `diverge`, or encoded in the expected results):

- SGR 21 is decoded as "remove bold" (for compatibility), while ECMA-48 and xterm use it
  for double underline (`hw/sgr21`, and the encoder no longer writes 21 since commit 5).
- On the irc path, SGR 2 removes bold, so the result depends on the order of 1 and 2: `2;1`
  is bold, `1;2` is not (`hw/dim-then-bold`, and the 128 `ti/linux/sgr/*` cases with dim and
  bold: linux's `sgr` writes `2;1`).
- DECSTR (`CSI ! p`, soft reset) is removed without resetting the attributes, while a
  terminal resets them (libvterm pen test).
- Bold does not brighten colors 0-7 (libvterm's `bold_is_highbright`; xterm's `boldColors`).
- IRC formatting codes in the output of a command pass through `/exec -o`, because a
  command may print IRC formatting on purpose (`toilet --irc`, cases `prog/toilet-irc-*` and
  `hw/irc-format/*`); SI is kept as the IRC reset `^O` and followed by the ANSI attributes
  and colors (commit 19). A program that prints such a byte by accident changes the IRC
  formatting.
- C1 controls encoded in UTF-8 (U+0080-U+009F, for example U+009B as CSI) are kept as text;
  terminals differ (xterm in UTF-8 mode treats them as controls) (`hw/utf8/c1-*`).
- With `weechat.look.color_real_white` off, white is shown in the default color (with
  `color_basic_force_bold`, plus the bold that shows a light color), but the logger and
  relay keep white (15): real_white is a terminal workaround, and logs keep the real color
  (display paths, reported as `diverge`).
- Where ECMA-48 says nothing, the reference follows the branch: RGB components are clamped
  to 0-255, values above 65535 are ignored, a palette index above 255 is ignored but its
  parameters are consumed, and an incomplete or unknown color type after 38/48/58 consumes
  the remaining parameters (like VTE and kitty).
