"""Minimal IRC server: accepts one client, answers registration, JOIN and
PING, and records the text of PRIVMSG messages."""

from __future__ import annotations

import socket
import threading


class FakeIrcd:
    def __init__(self) -> None:
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]
        self.messages: list[str] = []
        self.log: list[str] = []
        self.joined = threading.Event()
        self.nick = "tester"
        self.conn: socket.socket | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> FakeIrcd:
        self._thread.start()
        return self

    def stop(self) -> None:
        for sock in (self.conn, self.server):
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()
        self._thread.join(5)

    def _send(self, line: str) -> None:
        self.conn.sendall(line.encode("utf-8", "surrogateescape") + b"\r\n")

    def _run(self) -> None:
        try:
            self.conn, _ = self.server.accept()
        except OSError:
            return
        buffer = b""
        while True:
            try:
                data = self.conn.recv(65536)
            except OSError:
                break
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                self._handle(raw.rstrip(b"\r").decode("utf-8", "surrogateescape"))

    def _handle(self, line: str) -> None:
        self.log.append(line)
        command, _, rest = line.partition(" ")
        command = command.upper()
        if command == "CAP":
            if rest.startswith("LS"):
                self._send(":ircd CAP * LS :")
            elif rest.startswith("REQ"):
                self._send(f":ircd CAP * NAK :{rest.partition(':')[2]}")
        elif command == "NICK":
            self.nick = rest.split()[0].lstrip(":")
        elif command == "USER":
            self._send(f":ircd 001 {self.nick} :Welcome")
            self._send(f":ircd 376 {self.nick} :End of MOTD")
        elif command == "JOIN":
            for channel in rest.split()[0].split(","):
                self._send(f":{self.nick}!u@localhost JOIN {channel}")
                self._send(f":ircd 353 {self.nick} = {channel} :{self.nick}")
                self._send(f":ircd 366 {self.nick} {channel} :End of NAMES")
            self.joined.set()
        elif command == "PING":
            self._send(f":ircd PONG ircd {rest}")
        elif command == "PRIVMSG":
            _, _, text = rest.partition(" :")
            self.messages.append(text)
