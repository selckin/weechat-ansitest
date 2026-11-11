"""Drive a headless WeeChat through its FIFO, read its logs."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..sgr import plain

STARTUP = (
    "/set logger.file.color_lines on",
    "/set logger.file.flush_delay 0",
    '/set logger.file.time_format ""',
    "/set logger.file.info_lines off",
)
REQUIRED_PLUGINS = ("exec", "fifo", "irc", "logger")
MIN_VERSION = (4, 0)


class WeeChatError(Exception):
    pass


def binary_for_build(build: str) -> tuple[str, str]:
    """weechat-headless binary of a build directory, and its plugin directory."""
    build_dir = Path(build).resolve()
    return (str(build_dir / "src" / "gui" / "curses" / "headless" / "weechat-headless"),
            str(build_dir / "src"))


def curses_binary_for(headless: str) -> str | None:
    """The curses weechat next to a weechat-headless binary (build tree:
    src/gui/curses/normal/weechat; installed: weechat), None if not found."""
    path = Path(headless)
    for candidate in (path.parent.parent / "normal" / "weechat", path.parent / "weechat"):
        if candidate.is_file():
            return str(candidate)
    return None


def version(binary: str) -> tuple[str, tuple[int, int]]:
    """Version string and (major, minor) of a WeeChat binary."""
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True,
                             check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise WeeChatError(f"cannot run {binary} --version: {error}") from error
    match = re.search(r"(\d+)\.(\d+)", out)
    if not match:
        raise WeeChatError(f"unknown version: {out!r}")
    return out, (int(match.group(1)), int(match.group(2)))


class WeeChat:
    """A weechat-headless process in a temporary directory."""

    def __init__(self, binary: str, extra_libdir: str | None = None, keep: bool = False):
        self.binary = binary
        self.extra_libdir = extra_libdir
        self.keep = keep
        self.dir = Path(tempfile.mkdtemp(prefix="ansitest-weechat-"))
        self.process: subprocess.Popen | None = None
        self.fifo: Path | None = None
        self.plugins: set[str] = set()

    def __enter__(self) -> WeeChat:
        try:
            self.start()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
        if self.keep:
            print(f"WeeChat directory kept: {self.dir}", file=sys.stderr)
        else:
            shutil.rmtree(self.dir, ignore_errors=True)

    def command_line(self) -> list[str]:
        return [self.binary, "--dir", str(self.dir), "--run-command", ";".join(STARTUP)]

    def launch(self) -> None:
        env = dict(os.environ)
        if self.extra_libdir:
            env["WEECHAT_EXTRA_LIBDIR"] = self.extra_libdir
        with open(self.dir / "stdout.txt", "wb") as stdout:
            self.process = subprocess.Popen(
                self.command_line(), stdin=subprocess.DEVNULL, stdout=stdout,
                stderr=subprocess.STDOUT, env=env)

    def start(self, timeout: float = 30.0) -> None:
        self.launch()
        deadline = time.monotonic() + timeout
        while True:
            fifos = sorted(self.dir.glob("weechat_fifo*"))
            if fifos:
                self.fifo = fifos[0]
                break
            self._check_alive()
            if time.monotonic() > deadline:
                raise WeeChatError(f"no FIFO in {self.dir} (is the fifo plugin available?)")
            time.sleep(0.1)
        self.send("/print ansitest-ready")
        lines = self.wait_log(lambda lines: any("ansitest-ready" in line for line in lines),
                              timeout)
        loaded = next((plain(line) for line in lines if "Plugins loaded:" in plain(line)), None)
        if loaded is None:
            raise WeeChatError("the list of loaded plugins is not in the core log")
        names = {name.strip() for name in loaded.split("Plugins loaded:", 1)[1].split(",")}
        self.plugins = names
        missing = [name for name in REQUIRED_PLUGINS if name not in names]
        if missing:
            raise WeeChatError(f"missing WeeChat plugins: {', '.join(missing)}")

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        try:
            self.send("/quit")
            self.process.wait(10)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()
            self.process.wait()

    def _check_alive(self) -> None:
        if self.process is not None and self.process.poll() is not None:
            output = (self.dir / "stdout.txt").read_text(errors="replace")[-2000:]
            raise WeeChatError(f"WeeChat exited with code {self.process.returncode}: {output}")

    def send(self, command: str, buffer: str | None = None) -> None:
        """Run a command, in the current buffer or in `buffer` (full name)."""
        line = f"{buffer} *{command}\n" if buffer else f"*{command}\n"
        with open(self.fifo, "w", encoding="utf-8") as fifo:
            fifo.write(line)

    def log_path(self, buffer: str = "core.weechat") -> Path:
        return self.dir / "logs" / f"{buffer}.weechatlog"

    def log_lines(self, buffer: str = "core.weechat") -> list[str]:
        """Lines of a buffer's log (split on LF only: lines can hold other
        control characters)."""
        path = self.log_path(buffer)
        if not path.exists():
            return []
        lines = path.read_bytes().decode("utf-8", "surrogateescape").split("\n")
        return lines[:-1] if lines and lines[-1] == "" else lines

    def wait_log(self, predicate, timeout: float, buffer: str = "core.weechat") -> list[str]:
        deadline = time.monotonic() + timeout
        while True:
            lines = self.log_lines(buffer)
            if predicate(lines):
                return lines
            self._check_alive()
            if time.monotonic() > deadline:
                raise WeeChatError(f"timeout waiting for the {buffer} log; "
                                   f"last lines: {lines[-5:]}")
            time.sleep(0.2)


FEATURES_MARKER = "ansitest-features"
FEATURE_COMMANDS = (
    # Accepted only by a WeeChat with RGB colors (PR #2375).
    "/set weechat.color.chat_nick_self #ff8800",
    "/unset weechat.color.chat_nick_self",
    # IRC colors used for ANSI colors (option added with the 99 IRC colors;
    # the expression is empty if the option does not exist).
    "/eval /print -core ansitest-irc-colors=${irc.server_default.ansi_colors}",
    f"/print -core {FEATURES_MARKER}",
)


def parse_features(lines) -> dict:
    """Features of WeeChat from the core log after FEATURE_COMMANDS:
    "rgb" (RGB colors in color options) and "irc_colors" (value of option
    irc.server_default.ansi_colors, None if the option does not exist)."""
    text = [plain(line) for line in lines]
    rgb = any("weechat.color.chat_nick_self = #ff8800" in line for line in text)
    irc_colors = None
    for line in text:
        match = re.search(r"ansitest-irc-colors=(\w+)", line)
        if match:
            irc_colors = match.group(1)
    return {"rgb": rgb, "irc_colors": irc_colors}


def features(weechat: "WeeChat", timeout: float = 30.0) -> dict:
    """Detect features of a running WeeChat (see parse_features)."""
    for command in FEATURE_COMMANDS:
        weechat.send(command)
    lines = weechat.wait_log(
        lambda lines: any(FEATURES_MARKER in plain(line) for line in lines), timeout)
    return parse_features(lines)


class TmuxWeeChat(WeeChat):
    """The curses WeeChat in a detached tmux session (its own tmux server),
    with the given TERM; capture() returns what the screen shows."""

    WIDTH = 240
    HEIGHT = 130

    def __init__(self, binary: str, extra_libdir: str | None = None, keep: bool = False,
                 term: str = "xterm-256color"):
        super().__init__(binary, extra_libdir, keep)
        self.term = term
        self.socket = f"ansitest-{os.getpid()}-{id(self)}"

    def tmux(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["tmux", "-L", self.socket, "-f", "/dev/null", *args],
                              capture_output=True, text=True, errors="surrogateescape")

    def launch(self) -> None:
        env = ["-e", f"TERM={self.term}"]
        if self.extra_libdir:
            env += ["-e", f"WEECHAT_EXTRA_LIBDIR={self.extra_libdir}"]
        result = self.tmux("new-session", "-d", "-x", str(self.WIDTH), "-y", str(self.HEIGHT),
                           *env, shlex.join(self.command_line()))
        if result.returncode != 0:
            raise WeeChatError(f"tmux failed: {result.stderr.strip()}")

    def _check_alive(self) -> None:
        if self.tmux("has-session").returncode != 0:
            raise WeeChatError("WeeChat in tmux exited")

    def stop(self) -> None:
        if self.fifo is not None and self.tmux("has-session").returncode == 0:
            try:
                self.send("/quit")
            except OSError:
                pass
            deadline = time.monotonic() + 10
            while self.tmux("has-session").returncode == 0 and time.monotonic() < deadline:
                time.sleep(0.2)
        self.tmux("kill-server")

    def capture(self) -> list[str]:
        """Lines of the screen, with colors and attributes as SGR sequences."""
        return self.tmux("capture-pane", "-e", "-p", "-t", "0").stdout.split("\n")
