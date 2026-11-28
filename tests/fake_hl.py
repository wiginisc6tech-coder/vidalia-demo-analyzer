"""CS 1.6 falso para testes: le a demo passada em +playdemo, executa os comandos de console
inseridos pelo Vidalia (startmovie/endmovie/quit) e grava quadros BMP como o jogo faria."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("VIDALIA_SRC", os.path.dirname(HERE)))

from vidalia.demo import ConsoleFrame, iter_frames  # noqa: E402


def bmp(path, w, h, k):
    stride = ((w * 3 + 3) // 4) * 4
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            row += bytes(((x * 255 // w) & 0xFF, (k * 7) & 0xFF, (y * 255 // h) & 0xFF))
        rows.append(bytes(row).ljust(stride, b"\0"))
    data = b"".join(rows)
    hdr = b"BM" + struct.pack("<IHHI", 54 + len(data), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(hdr + info + data)


def main(argv):
    root = os.path.dirname(os.path.abspath(argv[0]))
    mod = argv[argv.index("-game") + 1]
    w = int(argv[argv.index("-w") + 1]) // 4
    h = int(argv[argv.index("-h") + 1]) // 4
    demo = os.path.join(root, mod, argv[argv.index("+playdemo") + 1].replace("/", os.sep) + ".dem")
    with open(os.path.join(root, "video.txt"), "w") as f:
        f.write("alterado pelo jogo")
    rec = None
    for fr in iter_frames(demo):
        if not isinstance(fr, ConsoleFrame):
            continue
        for cmd in fr.command.split(";"):
            parts = cmd.split()
            if parts and parts[0] == "startmovie":
                rec = (parts[1], int(parts[2]), fr.time)
            elif parts and parts[0] == "endmovie" and rec:
                tag, fps, t0 = rec
                for k in range(int((fr.time - t0) * fps)):
                    bmp(os.path.join(root, mod, "%s%04d.bmp" % (tag, k)), w, h, k)
                rec = None
            elif parts and parts[0] == "quit":
                return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
