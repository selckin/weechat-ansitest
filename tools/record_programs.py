#!/usr/bin/env python3
"""Record the colored output of real programs into ansitest/cases/programs.json.

Usage: tools/record_programs.py

The commands are the "with real programs" examples of the fix-ansi-colors
branch. Each output line becomes a case (see ansitest/cases/programs.py).
The output is recorded once and committed, so the cases do not depend on
the programs installed where the tests run; run this again to refresh it.
"""

import colorsys
import json
import os
import pathlib
import socket
import struct
import subprocess
import sys
import tempfile
from typing import NamedTuple

OUTPUT = pathlib.Path(__file__).resolve().parent.parent / "ansitest" / "cases" / "programs.json"

class Program(NamedTuple):
    name: str
    fixes: list[int]       # fixes it shows (commit numbers of the branch)
    command: str           # shell command
    version_command: str   # shell command that prints the program version
    format: str = "ansi"   # "ansi", or "irc" for IRC formatting codes (passed through by /exec -o)


PROGRAMS = [
    Program("node-inspect", [5],
            """node -e "console.log(require('util').inspect({a:null,b:1},{colors:true}))" """,
            "node --version"),
    Program("jq", [6], """echo '{"key":[1],"s":"x","n":null,"b":true}' | jq -C -c .""",
            "jq --version"),
    Program("node-styletext", [6],
            """FORCE_COLOR=1 node -e "const u=require('util'); console.log(u.styleText('bold', 'A '+u.styleText('red','B')+' C'))" """,
            "node --version"),
    Program("msgcat-test", [9], "msgcat --color=test", "msgcat --version | head -1"),
    Program("grep-comma", [9], """printf 'a,5 b\\n' | grep --color=always ',5'""",
            "grep --version | head -1"),
    Program("ls-hyperlink", [13], "ls --hyperlink=always --color=always", "ls --version | head -1"),
    Program("tput-direct", [14], "TERM=xterm-direct tput setaf 16711680; echo red; tput sgr0",
            "tput -V"),
    Program("tput-screen-sgr", [19],
            "TERM=screen tput sgr 0 0 0 0 0 1; echo bold; TERM=screen tput sgr0", "tput -V"),
]

# toilet (big text) in its export formats with ANSI or IRC colors, with its
# color filters and other filters, in several fonts. (The "utf8cr" format is
# "utf8" with CR before LF; /exec removes that CR, and so does this recorder,
# so it would only record the same lines again.)
TOILET_FORMATS = ("irc", "utf8")
TOILET_FILTERS = ("", "gay", "metal", "gay:border", "metal:flip", "gay:180")
TOILET_FONTS = ("future", "smblock", "pagga", "mono9", "ascii9", "emboss", "circle")
for export in TOILET_FORMATS:
    for filters in TOILET_FILTERS:
        for font in TOILET_FONTS:
            option = f" -F {filters}" if filters else ""
            PROGRAMS.append(Program(
                f"toilet-{export}-{filters.replace(':', '+') or 'plain'}-{font}", [],
                f"toilet -f {font}{option} -E {export} 'Hi,4'",
                "toilet --version | grep -o 'Version: [0-9.]*'",
                "irc" if export == "irc" else "ansi"))

# img2txt (libcaca) on generated images, in its ANSI, UTF-8 and IRC formats,
# with several dithering algorithms and widths. Its IRC output has digits
# right after color codes, which libcaca separates with ^B^B.
IMG2TXT_IMAGES = ("rainbow", "bars")
for export in ("ansi", "utf8", "irc"):
    for dither in ("none", "ordered4", "fstein"):
        for width in (30, 60):
            for image in IMG2TXT_IMAGES:
                PROGRAMS.append(Program(
                    f"img2txt-{export}-{dither}-{width}-{image}", [],
                    f"img2txt -W {width} -d {dither} -f {export} {image}.bmp",
                    "img2txt --version | grep -o 'Version: [0-9a-z.]*'",
                    "irc" if export == "irc" else "ansi"))

def write_bmp(path: pathlib.Path, width: int, height: int, pixel) -> None:
    """Write a 24-bit BMP; pixel(x, y) returns (red, green, blue) as 0-255."""
    rows = []
    for y in range(height):
        row = b"".join(bytes(reversed(pixel(x, y))) for x in range(width))
        rows.append(row + b"\0" * ((4 - len(row) % 4) % 4))
    data = b"".join(reversed(rows))
    header = (b"BM" + struct.pack("<IHHI", 54 + len(data), 0, 0, 54)
              + struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(data),
                            2835, 2835, 0, 0))
    path.write_bytes(header + data)


def write_images(directory: str) -> None:
    """Test images for img2txt: a rainbow that darkens downwards, and color
    bars above a gray ramp."""
    def rainbow(x, y):
        red, green, blue = colorsys.hsv_to_rgb(x / 64, 1.0, 1.0 - y / 40)
        return int(red * 255), int(green * 255), int(blue * 255)

    bars = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0), (255, 0, 255),
            (255, 0, 0), (0, 0, 255), (0, 0, 0)]

    def bars_and_ramp(x, y):
        if y < 20:
            return bars[x * len(bars) // 64]
        level = x * 255 // 63
        return level, level, level

    write_bmp(pathlib.Path(directory, "rainbow.bmp"), 64, 32, rainbow)
    write_bmp(pathlib.Path(directory, "bars.bmp"), 64, 32, bars_and_ramp)


def run(command: str, cwd: str) -> bytes:
    return subprocess.run(["sh", "-c", command], cwd=cwd, capture_output=True,
                          check=True).stdout


def main() -> None:
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        # Stable directory listing for ls: two files and a directory.
        for name in ("file.txt", "script.sh"):
            pathlib.Path(tmp, name).write_text("x\n")
        os.chmod(pathlib.Path(tmp, "script.sh"), 0o755)
        pathlib.Path(tmp, "dir").mkdir()
        write_images(tmp)
        versions: dict[str, str] = {}
        for program in PROGRAMS:
            try:
                output = run(program.command, tmp)
            except subprocess.CalledProcessError as error:
                sys.exit(f"{program.name}: {program.command!r} failed: "
                         f"{error.stderr.decode(errors='replace')}")
            # Do not record the host name and the temporary directory.
            output = output.replace(socket.gethostname().encode(), b"host")
            output = output.replace(tmp.encode(), b"/tmp/dir")
            if program.version_command not in versions:
                versions[program.version_command] = run(program.version_command,
                                                        tmp).decode().strip()
            version = versions[program.version_command]
            # Like /exec: a CR right before LF is not part of the line.
            lines = [line[:-1] if line.endswith(b"\r") else line for line in output.split(b"\n")]
            records.append({"name": program.name, "fixes": program.fixes,
                            "command": program.command.strip(), "version": version,
                            "format": program.format,
                            "lines": [line.hex() for line in lines if line]})
            print(f"{program.name}: {len(records[-1]['lines'])} lines ({version})")
    OUTPUT.write_text(json.dumps(records, indent=1) + "\n")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
