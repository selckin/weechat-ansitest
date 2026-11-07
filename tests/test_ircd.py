import socket
import time
import unittest

from ansitest.capture.ircd import FakeIrcd


class FakeIrcdTest(unittest.TestCase):
    def test_session(self):
        ircd = FakeIrcd().start()
        try:
            with socket.create_connection(("127.0.0.1", ircd.port), timeout=5) as conn:
                conn.sendall(b"CAP LS 302\r\nNICK tester\r\nUSER u 0 * :real\r\n")
                received = b""
                while b" 376 " not in received:
                    received += conn.recv(4096)
                self.assertIn(b":ircd CAP * LS :", received)
                self.assertIn(b":ircd 001 tester :", received)
                conn.sendall(b"JOIN #t\r\nPING :tok\r\n"
                             b"PRIVMSG #t :T00001 \x02a1\xff\r\n")
                self.assertTrue(ircd.joined.wait(5))
                deadline = time.monotonic() + 5
                while not ircd.messages and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(ircd.messages, ["T00001 \x02a1\udcff"])
                received = b""
                while b"PONG" not in received:
                    received += conn.recv(4096)
                self.assertIn(b":ircd PONG ircd :tok", received)
        finally:
            ircd.stop()


if __name__ == "__main__":
    unittest.main()
