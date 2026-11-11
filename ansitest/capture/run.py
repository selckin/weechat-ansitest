"""Run cases through /exec on the gui, gui-ansi and irc paths."""

from __future__ import annotations

import re
import time

from ..decode.gui import decode_gui, decode_print
from ..decode.irc import decode_irc
from ..decode import split_id_bytes
from ..decode.weechat import RAW_MARKER, decode_weechat, raw_message
from ..model import GUI_PATHS
from .ircd import FakeIrcd
from .weechat import WeeChat, WeeChatError

ID_BYTES = re.compile(rb"T\d{5} ")

# Print trigger that writes each case line as stored by WeeChat (raw color
# codes), hex-encoded so that the codes are not interpreted again.
RAW_TRIGGER = ('/trigger add ansitest_raw print "core.weechat" '
               '"${tg_message_nocolor} =~ ^T[0-9]{5} " "" '
               f'"/print -core {RAW_MARKER}${{base_encode:16,${{tg_message}}}}"')


def write_lines(path, cases) -> None:
    path.write_bytes(b"".join(case.line() + b"\n" for case in cases))


def wait_idle(count, total: int, idle: float = 10.0, timeout: float = 1800.0) -> None:
    """Wait until count() reaches total, or does not change for `idle` seconds."""
    start = last_change = time.monotonic()
    last = -1
    while True:
        number = count()
        now = time.monotonic()
        if number >= total or now - start > timeout:
            return
        if number != last:
            last, last_change = number, now
        elif now - last_change > idle:
            return
        time.sleep(0.2)


def run_gui(weechat: WeeChat, cases, raw: bool = True, color: str = "auto") -> dict[str, dict]:
    """Plain /exec -color <color> in the core buffer. Return the decoded lines
    per path: "gui-ansi" from the logger (colors as ANSI), "gui" from the raw
    color codes captured by a print trigger (if raw), and "bytes": the raw
    bytes of each stored line after its ID (if raw)."""
    got: dict = {path: {} for path in GUI_PATHS if raw or path != "gui"}
    if raw:
        got["bytes"] = {}
    if not cases:
        return got
    if raw:
        if "trigger" not in weechat.plugins:
            raise WeeChatError("the gui path needs the trigger plugin")
        weechat.send(RAW_TRIGGER)
    path = weechat.dir / "gui-lines.bin"
    write_lines(path, cases)
    log = weechat.log_path("core.weechat")
    marker = RAW_MARKER.encode()

    def count() -> int:
        if not log.exists():
            return 0
        data = log.read_bytes()
        return data.count(marker) if raw else len(ID_BYTES.findall(data))

    weechat.send(f"/exec -norc -color {color} cat {path}")
    wait_idle(count, len(cases))
    for line in weechat.log_lines("core.weechat"):
        if RAW_MARKER in line:
            message = raw_message(line)
            if message is not None and raw:
                decoded = decode_weechat(message)
                if decoded:
                    got["gui"].setdefault(decoded[0], decoded[1])
                split = split_id_bytes(message)
                if split:
                    got["bytes"].setdefault(split[0], split[1])
            continue
        decoded = decode_gui(line)
        if decoded:
            got["gui-ansi"].setdefault(decoded[0], decoded[1])
    return got


def run_irc(weechat: WeeChat, cases, version: tuple[int, int],
            color: str = "auto", options=()) -> dict[str, dict]:
    """/exec -o -color <color> on a channel of the fake IRC server. Return
    "irc": the decoded PRIVMSG texts, and "bytes": their raw bytes after the
    ID."""
    got: dict = {"irc": {}, "bytes": {}}
    if not cases:
        return got
    ircd = FakeIrcd().start()
    try:
        commands = ["/set irc.server_default.tls off",
                    f"/server add x 127.0.0.1/{ircd.port}",
                    "/set irc.server.x.nicks tester",
                    "/set irc.server.x.autojoin #t"]
        if version >= (4, 2):
            commands.append("/set irc.server.x.anti_flood 0")
        else:
            commands += ["/set irc.server.x.anti_flood_prio_high 0",
                         "/set irc.server.x.anti_flood_prio_low 0"]
        commands += list(options)
        commands.append("/connect x")
        for command in commands:
            weechat.send(command)
        if not ircd.joined.wait(30):
            raise WeeChatError("WeeChat did not join #t on the fake IRC server")
        time.sleep(1)  # Let WeeChat create the channel buffer.
        path = weechat.dir / "irc-lines.bin"
        write_lines(path, cases)
        weechat.send(f"/exec -o -norc -color {color} cat {path}", buffer="irc.x.#t")
        wait_idle(lambda: len(ircd.messages), len(cases))
        for message in list(ircd.messages):
            decoded = decode_irc(message)
            if decoded:
                got["irc"].setdefault(decoded[0], decoded[1])
            split = split_id_bytes(message.encode("utf-8", "surrogateescape"))
            if split:
                got["bytes"].setdefault(split[0], split[1])
        return got
    finally:
        ircd.stop()


def run_print(weechat: WeeChat, cases) -> dict:
    """/print cases: run the setup commands and /eval /print of each case in
    the core buffer, read back through the logger."""
    for case in cases:
        for command in case.setup:
            weechat.send(command)
        weechat.send(f"/eval /print {case.id} {case.payload.decode()}")
    log = weechat.log_path("core.weechat")
    wait_idle(lambda: len(re.findall(rb"P\d{5} ", log.read_bytes())) if log.exists() else 0,
              len(cases), idle=5.0)
    got: dict = {}
    for line in weechat.log_lines("core.weechat"):
        decoded = decode_print(line)
        if decoded:
            got.setdefault(decoded[0], decoded[1])
    return got
