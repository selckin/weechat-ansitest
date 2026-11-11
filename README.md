# weechat-ansitest

Black-box tests for WeeChat's ANSI colors: the decoding of ANSI escape
sequences in `/exec` output, and the encoding of WeeChat colors as ANSI (logger,
relay). The harness generates thousands of escape sequences and lines of WeeChat
colors, runs them in WeeChat, and checks the colors and attributes that come out:

- plain `/exec`: the ANSI colors become WeeChat colors in the buffer
  (`gui_color_decode_ansi`), and the logger writes them back as ANSI
  (`gui_color_encode_ansi`);
- `/exec -o` on an IRC channel: the ANSI colors become IRC colors sent to
  the server (`irc_color_decode_ansi`);
- `/print` of WeeChat colors in a curses WeeChat inside tmux: what the screen
  shows is the expected result for the logger.

It was written to check the branch
[`fix-ansi-colors`](https://github.com/selckin/weechat/tree/fix-ansi-colors), which
fixes 22 bugs in this decoding and encoding. The results are documented in:

- [`docs/fixes.md`](docs/fixes.md): each commit of the branch, what it fixes, how
  to reproduce the bug, the cases it fixes on each path (measured by building
  every commit), and the choices open to discussion;
- [`docs/findings-2026-11-07.md`](docs/findings-2026-11-07.md): the bugs this
  harness found in the branch, and the commits that fixed them.

## WeeChat main versus fix-ansi-colors

Run these commands from this repository. They need git, CMake, a C compiler and
WeeChat's build dependencies (see WeeChat's `README.md`), Python 3.10 or later,
ncurses with its terminfo entries, and tmux for the display paths.

1. Get WeeChat `main` and the branch inside this repository (both directories are
   git-ignored):

   ```
   git clone https://github.com/weechat/weechat.git weechat
   git -C weechat fetch https://github.com/selckin/weechat.git fix-ansi-colors:fix-ansi-colors
   git -C weechat worktree add ../weechat-fix-ansi-colors fix-ansi-colors
   ```

2. Build both (`weechat-headless` for the tests, the curses `weechat` for the display
   paths and `./ansiview`, without the plugins the tests do not need):

   ```
   for dir in weechat weechat-fix-ansi-colors; do
       cmake -S $dir -B $dir/build -DENABLE_SCRIPTS=OFF -DENABLE_SPELL=OFF \
           -DENABLE_RELAY=OFF -DENABLE_ZSTD=OFF -DENABLE_NLS=OFF
       cmake --build $dir/build -j
   done
   ```

3. Run all the cases on both, and compare:

   ```
   ./fetch-corpora.sh
   ./ansicheck --build weechat/build --json main.json
   ./ansicheck --build weechat-fix-ansi-colors/build --json branch.json
   tools/compare.py main.json branch.json
   ```

   Each run takes about a minute. Each of the 9430 cases runs on seven paths
   (`/exec` read from the stored line and from the logger, `/exec -o`, and both
   with `-color strip` and `-color ansi`), 4 cases run on the `print` path,
   and 1884 generated lines of WeeChat colors run on the two display paths (see
   below). With `main` at `bf66d9b`, 10889 of these results
   fail on `main`, and none on the branch:

   ```
   source   path              before   after   fixed  broken
   ar       gui                   44       0      44       0
   ...
   display  display             1385       0    1385       0
   display  display-headless     739       0     739       0
   ...
   ti       irc                 6616       0    6616       0

   10889 failure(s) before, 0 after: 10889 fixed, 0 broken
   ```

   `tools/compare.py --list main.json branch.json` lists every fixed case.

4. Look at a few bugs, with the input, the expected result and what WeeChat
   produced:

   ```
   F='hw/(sgr22-bold-dim|default-fg-keeps-attrs|empty-param-middle|noise/osc8|fgrgb/38:2::255:136:0|rapid-blink) '
   ./ansicheck --build weechat/build --path gui --filter "$F"
   ./ansicheck --build weechat-fix-ansi-colors/build --path gui --filter "$F"
   ```

   On `main`, all six fail, for example:

   ```
   FAIL T07973 [gui] hw/sgr22-bold-dim
     22 removes bold and dim
     input:    \e[1;2ma1\e[22ma2
     expected: 'a1'[bold dim] 'a2'[(default)]
     got:      'a1'[bold dim] 'a2'[bold]
     char 2 'a': bold expected False got True

   FAIL T07994 [gui] hw/default-fg-keeps-attrs
     39 keeps the attributes
     input:    \e[1;3;31ma1\e[39ma2
     expected: 'a1'[fg=1 bold italic] 'a2'[bold italic]
     got:      'a1'[fg=1 bold italic] 'a2'[(default)]
     char 2 'a': bold expected True got False, italic expected True got False
   ```

   On the branch, all six pass, and each one shows the same details:

   ```
   PASS T07973 [gui] hw/sgr22-bold-dim
     22 removes bold and dim
     input:    \e[1;2ma1\e[22ma2
     expected: 'a1'[bold dim] 'a2'[(default)]
     got:      'a1'[bold dim] 'a2'[(default)]
     correct: got is what was expected
   ```

   With `--filter`, every selected case is shown like this; without it, only
   the failures are. The IRC side of the same bugs: `--path irc`.

5. See the cases in WeeChat itself, `main` and the branch side by side (needs
   tmux):

   ```
   ./ansiview --filter "$F"
   ```

   This opens a tmux session in your terminal with the curses `weechat` of each
   build in its own pane, labeled with the build and the commit it was built
   from. Each WeeChat uses a temporary directory, so your configuration is not
   touched, and runs `/exec -norc ansigen --eyeball --filter "$F"`. Before each
   case, a comment line says what it should look like:

   ```
   # T07973 hw/sgr22-bold-dim: 22 removes bold and dim
   #   expect: a1 bold dim | a2 (default)
   T07973 a1a2
   ```

   The top of each WeeChat shows `/exec` (ANSI colors decoded to WeeChat colors);
   the bottom shows `/exec -o` in the channel `#t` of a fake IRC server on
   127.0.0.1 (the IRC colors WeeChat sent, as it shows its own messages). What you
   type goes to both panes (tmux `synchronize-panes`), so PgUp/PgDn scrolls both
   WeeChats together; `Ctrl-b :setw synchronize-panes off` turns that off. Without
   `--filter`, the 139 hand-written cases are shown. Detach (`Ctrl-b d`) or quit
   both WeeChats to end; everything is removed. Inside tmux, the session is nested:
   press `Ctrl-b` twice to reach it. `--build DIR` (repeatable) picks other builds.

   For pictures made of several lines, `--plain` leaves out the comment lines, for
   example `img2txt` or `toilet` (keys in `./ansigen --list --filter prog/`):

   ```
   ./ansiview --plain --filter 'prog/img2txt-ansi-none-60-rainbow/'
   ./ansiview --plain --filter 'prog/img2txt-utf8-fstein-60-bars/'
   ./ansiview --plain --filter 'prog/toilet-irc-gay-future/'
   ```

   By hand, in a WeeChat you start yourself, with a temporary directory: `main`

   ```
   WEECHAT_EXTRA_LIBDIR=weechat/build/src weechat/build/src/gui/curses/normal/weechat --dir "$(mktemp -d)"
   ```

   and the branch (in another terminal):

   ```
   WEECHAT_EXTRA_LIBDIR=weechat-fix-ansi-colors/build/src weechat-fix-ansi-colors/build/src/gui/curses/normal/weechat --dir "$(mktemp -d)"
   ```

   then, in WeeChat (`/exec` runs in the directory WeeChat was started from, here
   this repository):

   ```
   /exec -norc ./ansigen --eyeball --filter hw/sgr22
   ```

   `/exec -o` sends every line to the current channel: use it only on a test
   server. In a terminal, `./ansigen --eyeball --filter "$F"` shows what a
   terminal makes of the same cases.

6. To find which commit of the branch fixes which case (it builds every commit
   in the worktree, and restores its checkout at the end):

   ```
   tools/fixes_by_commit.py weechat-fix-ansi-colors weechat-fix-ansi-colors/build \
       origin/main fix-ansi-colors /tmp/by-commit
   ```

WeeChat is not patched, and no script plugin is needed: the harness only
uses WeeChat's FIFO, logger and trigger plugins, so it runs against any
`weechat-headless` binary or build directory:
`./ansicheck --build DIR` or `./ansicheck --weechat BIN`.

## Requirements

- Python 3.10 or later, standard library only.
- ncurses with its terminfo entries (Python's `curses` module).
- `weechat-headless` 4.0 or later, with the plugins exec, fifo, irc and
  logger. The `gui` path also needs the trigger plugin: without it, that
  path is skipped.
- For the display paths: tmux and the curses `weechat` (in a build
  directory, `src/gui/curses/normal/weechat`); skipped without them.
- `git`, only to fetch the corpora.

The exit code of `ansicheck` is 0 if no case fails, 1 if some fail, and 2 if
WeeChat could not be run (missing plugin, version too old, timeout).

## How it works

### Cases

Each case is one line: an ID, then a series of steps. Each step is an
escape sequence followed by a short marker text (`a1`, `a2`, ...), and
each marker carries the attribute state that the sequence should give it:

```
T00042 \e[38;5;196ma1\e[39;49ma2\e[0m      a1: fg=196, a2: default
```

The expected states come from construction, not from parsing the bytes.
For terminfo cases, the harness asks ncurses for the sequence of a
capability (`setaf 196`, `sgr` with bold and underline, ...) and the
expected state is the meaning of that capability. No terminal emulator is
used as a reference: emulators like pyte lack dim, colons, SGR 58 and
`4:0`, which are exactly what is being tested.

Sources of cases (around 9,430 in total):

| Source | Key prefix | Contents |
|--------|------------|----------|
| terminfo | `ti/` | For `xterm-256color`, `xterm-direct`, `tmux-256color`, `screen`, `linux` and `rxvt-unicode-256color`: every `setaf`/`setab` color, all 512 `sgr` combinations, attributes on and off, colors combined with attributes, `Smulx`/`Setulc`, and capabilities with no color meaning (`cup`, `el`, `smcup`, `flash`, ...) that must be removed. Each TERM is read through ncurses in its own process. |
| display | `display/` | Generated lines of WeeChat colors, per terminal configuration, on the display paths only. |
| print | `print/` | Lines printed with `/print` and WeeChat colors (not `/exec`), on the `print` path only. |
| hand-written | `hw/` | What terminfo cannot produce: colon forms (`38:2::R:G:B`), empty parameters, `4:0`..`4:5`, SGR 58, out-of-range values, incomplete colors, 1000 parameters, digits right after a color, non-SGR sequences (OSC, DCS, APC, PM, SOS, private CSI, charsets, two-byte escapes, unterminated sequences), and UTF-8: 2/3/4-byte, double-width and combining characters around colors, UTF-8 inside sequences that must be removed, and C1 controls encoded in UTF-8 (kept as text). |
| programs | `prog/` | The colored output of real programs, recorded with `tools/record_programs.py` into `ansitest/cases/programs.json` (with the command and the program version): `node` (`util.inspect`, `styleText`), `jq -C`, `msgcat --color=test`, `grep --color`, `ls --hyperlink`, `tput` with `xterm-direct` and `screen`, `toilet` (big text) with ANSI and IRC colors (`--irc`), its color filters (`--gay`, `--metal`) and other filters, in several fonts, and `img2txt` (libcaca, images as text) on generated images (a rainbow, color bars and a gray ramp) in its `ansi`, `utf8` and `irc` formats, with several dithering algorithms and widths. |
| libvterm pen | `lvp/` | `t/30state_pen.test` and `t/64screen_pen.test` from libvterm; libvterm's own assertions (`?pen bold = on`) are the expected values. |
| libvterm parser | `lvx/` | `t/02parser.test`: only the visible text is checked (what must be removed and what must stay). |
| ansi-regex | `ar/` | `fixtures/ansi-codes.js` from chalk/ansi-regex: about 190 real-world codes (VT52, VT100, xterm, urxvt), each between two markers. |

The corpora are fetched by `./fetch-corpora.sh` into `corpora/`
(git-ignored), at the commits pinned in `corpora.lock`. They are read as
text and never executed. Without them, only the terminfo and hand-written
cases run.

### Paths

`ansicheck` writes the case lines to a file and replays it with
`/exec -norc cat <file>`, so WeeChat receives exactly the bytes that are
checked. With the default `-color auto`, the result is captured on three paths:

| Path | What is checked |
|------|-----------------|
| `gui` | The buffer line as WeeChat stores it (its internal color codes), captured hex-encoded by a print trigger and read the way the curses display reads it. Only the codes that the ANSI decoder writes are accepted; any other code byte shows as `<unexpected ...>`. |
| `gui-ansi` | The same line written by the logger with `logger.file.color_lines on`, so it also goes through WeeChat's ANSI encoder. |
| `irc` | `/exec -o -norc cat <file>` on a channel of a fake IRC server started by the harness; the PRIVMSG bytes are decoded as IRC formatting codes. |

The other values of `/exec -color` are checked on the bytes of the result:

| Path | Command | What is checked |
|------|---------|-----------------|
| `gui-strip` | `/exec -color strip` | The stored line: its visible text is the expected text, and it has no ESC, no WeeChat color code, and no IRC formatting code that is not in the input. |
| `irc-strip` | `/exec -o -color strip` | The same on the IRC message. An SI of the input is kept as the IRC reset `^O` (commit 19), which is allowed. |
| `gui-keep` | `/exec -color ansi` | The stored line is the input, byte for byte (WeeChat stores valid UTF-8: each byte that is not valid UTF-8 becomes `?`). |
| `irc-keep` | `/exec -o -color ansi` | The IRC message is the input, byte for byte. |

More paths check WeeChat colors that do not come from `/exec`, that is the
encoder that writes WeeChat colors as ANSI for the logger and the relay:

| Path | Command | What is checked |
|------|---------|-----------------|
| `display` | `/eval /print <id> <expression>` in the curses `weechat` inside tmux (`tmux capture-pane -e`) | Generated lines of WeeChat colors (`ansitest/cases/display.py`): option colors set to light colors and colors with attributes, the 17 basic colors with every attribute flag and `|`, 256 colors, text and background colors, attributes on and off, `reset`, `resetcolor`, in fixed patterns and seeded random sequences, for `TERM=xterm` (8 colors) and `xterm-256color` x `color_basic_force_bold` on/off x `color_real_white` on/off. The screen is the expected result for the logger of the same WeeChat, character by character: the displayed color (0-7 with bold is shown as 8-15) and the attributes. Needs tmux; skipped without it. |
| `display-headless` | the same lines in `weechat-headless` | The logger of headless WeeChat against the same screen (256-color configurations). |
| `print` | `/eval /print <id> <expression>` after the case's `/set` commands | The line through the logger's ANSI encoder (cases `print/*`, in `ansitest/cases/printing.py`): option and custom colors, bold on and off, with and without `weechat.look.color_basic_force_bold`. Only the displayed color is compared: a color 0-7 with bold counts as the light color 8-15, as on a terminal with fewer than 16 colors. |

`-color weechat` is the same as `-color auto` for `/exec`, and `-color irc` the same
as `-color auto` for `/exec -o`; the two other combinations (IRC codes in a buffer,
WeeChat codes sent to IRC) are not checked.

Each path can show fewer attributes than a terminal, so the expected state
is first reduced to what the path can represent:

- `gui`, `gui-ansi`: RGB colors become the nearest of 256 colors (WeeChat's
  own table and algorithm, copied by `tools/extract_tables.py`), or stay RGB
  colors with a WeeChat that has RGB colors ([#2375](https://github.com/weechat/weechat/pull/2375):
  `\x19F@#rrggbb` in the buffer line); no strikethrough.
- `irc`: colors become IRC colors 0-15 through WeeChat's tables; no dim and
  no blink; bold is shown only without dim, because WeeChat sends SGR 2 as
  "remove bold". With a WeeChat that has the server option
  `irc.server.*.ansi_colors`, terminal colors 16-255 and RGB colors follow its
  value: `extended` (IRC colors 16-98: the IRC color displayed with the terminal
  color, or the nearest one by RGB value) or `rgb` (RGB colors as IRC hex colors
  `^Drrggbb`); the RGB values of IRC colors 16-98 come from the
  [IRC formatting specification](https://modern.ircdocs.horse/formatting#colors-16-98)
  (`ansitest/irc99.py`), not from WeeChat. Terminal colors 0-15 are always IRC
  colors 0-15.

Before running the cases, `ansicheck` detects these features of the WeeChat
under test (RGB colors are accepted in a color option; value of
`irc.server_default.ansi_colors`) and prints them, for example
`RGB colors: yes, IRC colors for ANSI colors: extended`.

Input that is already formatted for IRC (`toilet --irc`, `img2txt -f irc`, cases
`hw/irc-format/*`)
passes through `/exec -o` on purpose: for these cases, the irc path expects the
IRC formatting of the input, and the other paths expect what a terminal shows
(the codes are invisible, the digits of a color code are text).

Then the visible text and the state of every character are compared. C0
controls (and DEL) are removed from the decoded text first: a terminal
does not print them, and the ANSI decoders are not meant to remove them.

### Skips and divergences

A case is skipped on a path when it cannot be sent through it: NUL, LF,
CR or TAB in the line, invalid UTF-8 in the visible text (it is fine inside
a sequence that is removed, like a window title in ISO-8859-1), a line longer than 400 bytes on the
irc path (WeeChat would split the IRC message), or a standout that matches
no single attribute on that TERM. Skips are counted per reason in the
report; nothing is dropped silently.

`ansitest/divergences.py` lists places where WeeChat intentionally differs
from the reference (ECMA-48 / xterm, or a corpus's own expectations), for
example SGR 21 (double underline in xterm, "remove bold" in WeeChat). Each
entry has a case key or an `fnmatch` pattern, the paths, a reason, and
WeeChat's expected result. A matching case is reported as `diverge`, not
`pass`. A divergence that is no longer needed (the case now matches the
reference) is reported as a failure, so the list cannot go stale.

## Usage

### ansicheck

```
./ansicheck --build DIR | --weechat BIN [--path all|gui|gui-ansi|irc|gui-strip|irc-strip|gui-keep|irc-keep|print|display|display-headless]
            [--filter REGEX] [--term TERM]... [--corpora DIR] [--irc-colors basic|extended|rgb]
            [--verbose] [--keep]
```

- `--build DIR`: a WeeChat build directory
  (`DIR/src/gui/curses/headless/weechat-headless`, plugins from `DIR/src`).
- `--weechat BIN`: a `weechat-headless` binary (default: the one in `PATH`).
- `--path`: run only one path (default: all ten).
- `--filter REGEX`: only the cases whose `<id> <source> <key> <description>`
  matches, e.g. `--filter 'hw/noise/'` or `--filter 'ti/xterm-direct/'`, with
  the input, expected result and result of each one (passing or not).
- `--term TERM`: TERMs for the terminfo cases (repeatable).
- `--irc-colors basic|extended|rgb`: set `irc.server_default.ansi_colors` for the
  irc paths (only with a WeeChat that has this option; default: its default
  value), to check each value.
- `--verbose`: also list every diverging and skipped case.
- `--keep`: keep WeeChat's temporary directory (logs, stdout) for debugging.
- `--json FILE`: also write the status of every case and path as JSON.

The report starts with counts per source and path (`pass`, `diverge`,
`fail`, `skip`). Each failure then shows the input with escapes visible, the
expected and decoded text runs with their attributes, and the first
difference:

```
FAIL T08072 [gui] hw/osc-unterminated
  OSC without terminator at the end of the line
  input:    a1\e]0;title
  expected: 'a1'[(default)]
  got:      'a10;title'[(default)]
  text differs: expected 'a1', got 'a10;title'
```

To investigate one failure, run it alone and keep WeeChat's directory:
`./ansicheck --build DIR --filter 'hw/osc-unterminated ' --keep`.

### ansigen

```
./ansigen [--eyeball] [--list] [--manifest FILE] [--filter REGEX] [--term TERM]...
```

Without options, it writes the case lines (raw bytes) to stdout.

- `--eyeball`: before each case, a description and the expected
  attributes, for comparing by eye. In a terminal:
  `./ansigen --eyeball --filter 'hw/' | less -R`. In WeeChat:
  `/exec -norc /path/to/ansigen --eyeball --filter hw/`.
- `--list`: one line per case (ID, key, skip reason).
- `--manifest FILE`: every case as JSON lines, with the payload in hex and
  the expected runs.

IDs (`T00001`, ...) depend on the TERMs and corpora present; keys
(`hw/sgr21`, `ti/xterm-256color/setaf/196`, ...) are stable.

### ansiview

```
./ansiview [--build DIR]... [--filter REGEX] [--term TERM]... [--plain] [--no-attach] [--keep]
```

Shows `ansigen --eyeball` in the curses `weechat` of each build, side by side
in a new tmux session, with `/exec` at the top and `/exec -o` to a fake IRC
server at the bottom (see "WeeChat main versus fix-ansi-colors", step 5).

- `--build DIR`: a build directory, repeatable (default: `weechat/build` and
  `weechat-fix-ansi-colors/build`, those that exist).
- `--filter REGEX`: the cases to show (default: `hw/`).
- `--plain`: only the case lines, without the comment lines (for pictures such
  as `img2txt` output).
- `--no-attach`: print the tmux command to attach instead of attaching, and
  wait (Ctrl-C ends the view).
- `--keep`: keep the WeeChat directories.

## Fixes on the branch

`docs/fixes.md` lists every fix of the `fix-ansi-colors` branch: what it
fixes, how to reproduce it, and which cases it makes pass. That table is
measured, not written by hand: `tools/fixes_by_commit.py` builds the base
and each commit of the branch in a WeeChat worktree, runs `ansicheck --json`
on each, and lists the cases that each commit turns from fail to pass.

```
tools/fixes_by_commit.py <weechat worktree> <its build dir> origin/main fix-ansi-colors <output dir>
tools/fixes_doc.py <output dir>/summary.json docs/fixes.md
```

The descriptions and reproductions of the fixes are in `tools/fixes_doc.py`.

## Changing the cases

- New hand-written case: add it to `ansitest/cases/handwritten.py` with its
  expected states. A unit test checks every hand-written expectation
  against the reference SGR model (`ansitest/sgr.py`), which catches typos.
- New intended difference: add an entry to `ansitest/divergences.py`, with
  the reason and WeeChat's expected result.
- Programs: edit the list in `tools/record_programs.py` and run it again
  to record their output into `ansitest/cases/programs.json`.
- WeeChat's color tables changed: run
  `tools/extract_tables.py <weechat source dir>` to regenerate
  `ansitest/tables_data.py`. An integration test compares the tables with
  the values that WeeChat prints.

## Tests

```
python3 -m unittest discover -s tests -t . -v
ANSITEST_WEECHAT_BUILD=<build dir> python3 -m unittest tests.test_weechat -v
```

The first runs the unit tests (the integration tests are skipped). The
second runs the integration tests against a WeeChat build: both gui paths
and the irc path on a few cases, and the color tables.

## Layout

```
ansigen, ansicheck        command-line tools
ansiview                  the cases in curses WeeChats side by side (tmux)
fetch-corpora.sh          fetch the corpora pinned in corpora.lock
tools/extract_tables.py   copy WeeChat's color tables
tools/record_programs.py  record the output of real programs
tools/fixes_by_commit.py  find which cases each commit of a branch fixes
tools/fixes_doc.py        write docs/fixes.md from that
tools/compare.py          compare two ansicheck --json results
ansitest/model.py         attribute state, cases, skip rules
ansitest/sgr.py           escape sequence tokenizer and reference SGR model
ansitest/tables*.py       WeeChat's color tables and conversions
ansitest/irc99.py         RGB values of IRC colors 16-98 (IRC formatting specification)
ansitest/project.py       reference state reduced to what each path shows
ansitest/cases/           terminfo, hand-written, program, libvterm and ansi-regex cases
ansitest/ti_dump.py       dump one TERM's capabilities (one process per TERM)
ansitest/capture/         headless WeeChat driver, fake IRC server, runner
ansitest/decode/          decoders: WeeChat codes, logger ANSI, IRC codes
ansitest/check.py         comparison, divergences
ansitest/report.py        report
docs/                     fixes on the branch, findings of test runs
```

## Limits

- The `gui` path models a terminal with 16 colors or more and
  `weechat.look.color_real_white on`. Terminals with 8 colors, where light
  colors are shown as bold, are not modeled.
- The harness checks results, not speed.
- IRC formatting codes in the input (`^B`, `^C`, `^O`, ...) pass through
  `/exec -o` on purpose, because a command may print IRC formatting; the
  irc path checks that they pass through, not their meaning in a terminal.
