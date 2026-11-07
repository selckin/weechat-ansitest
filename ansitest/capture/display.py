"""Display paths: lines printed in a curses WeeChat inside tmux; the screen
is the expected result for the logger of the same WeeChat ("display") and
for the logger of weechat-headless with the same settings
("display-headless")."""

from __future__ import annotations

import re
import time

from ..cases.display import CONFIGS, DisplayConfig, lines
from ..check import Result
from ..decode.gui import message
from ..model import Case, State, visible
from ..sgr import runs
from .run import wait_idle
from .weechat import TmuxWeeChat, WeeChat

ID = re.compile(r"(D\d{5}) ")
BATCH = 100
SETUP = ('/set weechat.look.buffer_time_format ""', "/set weechat.look.prefix_align none")


def displayed(state: State) -> dict:
    """What a character looks like: a basic color 0-7 with bold is shown as
    the light color 8-15."""
    fg = state.fg
    light_by_bold = isinstance(fg, int) and fg < 8 and state.bold
    return {"fg": fg + 8 if light_by_bold else fg, "bg": state.bg, "bold": state.bold,
            "dim": state.dim, "italic": state.italic, "underline": state.underline,
            "reverse": state.reverse, "blink": state.blink}


def parse(text: str) -> tuple[str, list[tuple[str, dict]]] | None:
    """(ID, characters after "<id> " with how they look), trailing spaces
    removed, for a screen line or a logger message."""
    chars = []
    for run_text, state in runs(text)[0]:
        look = displayed(state)
        chars.extend((char, look) for char in visible(run_text))
    match = ID.search("".join(char for char, _ in chars))
    if not match:
        return None
    chars = chars[match.end():]
    while chars and chars[-1][0] == " ":
        chars.pop()
    return match.group(1), chars


REAL_WHITE = ("with weechat.look.color_real_white off, white is shown in the default "
              "color; the logger writes white (15)")


def compare_display(expected, got, real_white: bool = True,
                    force_bold: bool = False) -> str | None:
    """None if the characters look the same. Bold is not compared on a light
    color (8-15), where it may only be how the light color is shown. Without
    real_white, white on the screen is the default color (with force_bold,
    plus the bold that shows a light color): if that is the only difference,
    return REAL_WHITE."""
    expected_text = "".join(char for char, _ in expected)
    got_text = "".join(char for char, _ in got)
    if expected_text != got_text:
        return f"text differs: expected {expected_text!r}, got {got_text!r}"
    if not real_white:
        as_shown = []
        for (char, look), (_, want) in zip(got, expected):
            if look["fg"] == 15:
                look = dict(look, fg=None,
                            bold=look["bold"] or (force_bold and want["fg"] is None
                                                  and want["bold"]))
            as_shown.append((char, look))
        if (compare_display(expected, as_shown) is None
                and compare_display(expected, got) is not None):
            return REAL_WHITE
    for index, ((char, want), (_, have)) in enumerate(zip(expected, got)):
        keys = [key for key in want
                if not (key == "bold" and any(isinstance(look["fg"], int) and 8 <= look["fg"] <= 15
                                              for look in (want, have)))]
        diffs = [f"{key} expected {want[key]!r} got {have[key]!r}" for key in keys
                 if want[key] != have[key]]
        if diffs:
            return f"char {index} {char!r}: " + ", ".join(diffs)
    return None


def _print_lines(weechat: WeeChat, config: DisplayConfig, items, screen: bool) -> dict:
    """Print the lines; return {id: screen characters} if screen, else {}."""
    for command in (*SETUP, *config.setup()):
        weechat.send(command)
    log = weechat.log_path("core.weechat")
    shown: dict = {}
    for start in range(0, len(items), BATCH):
        batch = items[start:start + BATCH]
        for case_id, (_, expression) in batch:
            weechat.send(f"/eval /print {case_id} {expression}")
        last = batch[-1][0].encode()
        wait_idle(lambda: 1 if log.exists() and last + b" " in log.read_bytes() else 0, 1,
                  idle=10.0)
        if screen:
            time.sleep(0.5)  # Let the screen be drawn.
            for line in weechat.capture():
                parsed = parse(line)
                if parsed:
                    shown.setdefault(parsed[0], parsed[1])
            weechat.send("/buffer clear")
    return shown


def _logged(weechat: WeeChat) -> dict:
    got: dict = {}
    for line in weechat.log_lines("core.weechat"):
        parsed = parse(message(line))
        if parsed:
            got.setdefault(parsed[0], parsed[1])
    return got


def run_display(curses_binary: str, headless_binary: str | None, libdir: str | None,
                pattern=None, keep: bool = False, configs=CONFIGS) -> list[Result]:
    """Run every configuration; results for paths display and display-headless
    (headless is compared with the screen of the 256-color terminal)."""
    results = []
    for config in configs:
        items = [(f"D{number:05d}", item) for number, item in enumerate(lines(config), 1)]
        cases = {case_id: Case("display", f"display/{config.name}/{key}", expression,
                               expression.encode(), [], id=case_id)
                 for case_id, (key, expression) in items}
        if pattern:
            items = [(case_id, item) for case_id, item in items
                     if pattern.search(f"{case_id} display {cases[case_id].key} {item[1]}")]
        if not items:
            continue
        print(f"display {config.name}: {len(items)} lines", flush=True)
        with TmuxWeeChat(curses_binary, libdir, keep=keep, term=config.term) as weechat:
            screen = _print_lines(weechat, config, items, screen=True)
            logged = _logged(weechat)
        headless = None
        if headless_binary and config.colors256:
            with WeeChat(headless_binary, libdir, keep=keep) as weechat:
                _print_lines(weechat, config, items, screen=False)
                headless = _logged(weechat)
        for case_id, _ in items:
            case = cases[case_id]
            for path, got in (("display", logged), ("display-headless", headless)):
                if got is None:
                    continue
                expected = screen.get(case_id)
                if expected is None:
                    results.append(Result(case, path, "fail", "line not on the screen"))
                elif got.get(case_id) is None:
                    results.append(Result(case, path, "fail", "line not in the log"))
                else:
                    error = compare_display(expected, got[case_id], config.real_white,
                                            config.force_bold)
                    status = ("pass" if error is None
                              else "diverge" if error == REAL_WHITE else "fail")
                    results.append(Result(case, path, status, error or "", got[case_id],
                                          expected=expected))
    return results
