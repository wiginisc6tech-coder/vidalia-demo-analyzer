"""Edicao de demos: insere comandos de console em tempos escolhidos.

O CS 1.6 executa os frames de comando (tipo 3) gravados na demo quando a reproducao chega no tempo
deles. Com isso uma copia da demo pode, sozinha, avancar rapido ate o momento apontado, gravar o
trecho e fechar o jogo. A demo original nunca e alterada.
"""
import struct

from .bitreader import ParseError
from .demo import DIR_ENTRY, EVENT_FRAME, FRAME_HDR, HEADER_SIZE, NETINFO_SIZE, read_header

CMD_SIZE = 64


def frame_bounds(data, start, end):
    """Lista (offset, tipo, tempo, frame) de cada frame do segmento [start, end)."""
    out = []
    p = start
    while p + 9 <= end:
        kind, t, fr = FRAME_HDR.unpack_from(data, p)
        out.append((p, kind, t, fr))
        q = p + 9
        if kind in (0, 1):
            ln = struct.unpack_from("<i", data, q + NETINFO_SIZE + 28)[0]
            if ln < 0 or q + NETINFO_SIZE + 32 + ln > end:
                raise ParseError("frame de rede invalido em %d" % p)
            q += NETINFO_SIZE + 32 + ln
        elif kind == 2:
            pass
        elif kind == 3:
            q += CMD_SIZE
        elif kind == 4:
            q += 32
        elif kind == 5:
            break
        elif kind == 6:
            q += EVENT_FRAME.size
        elif kind == 7:
            q += 8
        elif kind == 8:
            ln = struct.unpack_from("<i", data, q + 4)[0]
            if ln < 0 or ln > 1024:
                raise ParseError("frame de som invalido em %d" % p)
            q += 8 + ln + 16
        elif kind == 9:
            ln = struct.unpack_from("<i", data, q)[0]
            if ln < 0 or q + 4 + ln > end:
                raise ParseError("buffer invalido em %d" % p)
            q += 4 + ln
        else:
            raise ParseError("tipo de frame desconhecido %d em %d" % (kind, p))
        p = q
    return out


def console_frame(t, fr, cmd):
    raw = cmd.encode("latin-1", "replace")
    if len(raw) >= CMD_SIZE:
        raise ValueError("comando longo demais para um frame de demo: %r" % cmd)
    return FRAME_HDR.pack(3, t, fr) + raw.ljust(CMD_SIZE, b"\0")


def split_commands(cmds):
    """Divide 'a; b; c' em pedacos que cabem em 63 bytes."""
    parts, cur = [], ""
    for c in [c.strip() for c in cmds.split(";") if c.strip()]:
        nxt = c if not cur else cur + ";" + c
        if len(nxt) < CMD_SIZE:
            cur = nxt
        else:
            if cur:
                parts.append(cur)
            cur = c
    if cur:
        parts.append(cur)
    return parts


def playback_segment(hdr):
    """Indice do segmento de reproducao (o primeiro que nao e LOADING)."""
    for k, e in enumerate(hdr.entries):
        if e.type != 0:
            return k
    return len(hdr.entries) - 1


def inject_commands(src, dst, commands):
    """Copia `src` para `dst` inserindo comandos. `commands` = [(tempo_da_demo, "cmd1; cmd2"), ...].

    O tempo e o mesmo usado pelos frames da demo (o de Timeline.t). Um tempo antes do inicio da
    reproducao executa logo no primeiro frame; depois do fim, no ultimo."""
    hdr = read_header(src)
    with open(src, "rb") as f:
        data = f.read()
    seg = playback_segment(hdr)
    entry = hdr.entries[seg]
    start = entry.offset
    end = len(data) if entry.type == -1 else min(len(data), entry.offset + entry.length)
    frames = frame_bounds(data, start, end)
    if not frames:
        raise ParseError("segmento de reproducao vazio")
    # ponto de insercao: antes do primeiro frame (que nao seja o separador) com tempo >= t
    inserts = {}
    for t, cmds in sorted(commands, key=lambda c: c[0]):
        pos, fr = None, frames[-1][3]
        for off, kind, ft, fnum in frames:
            if kind == 5:
                pos, fr = off, fnum
                break
            if ft >= t:
                pos, fr = off, fnum
                break
        if pos is None:
            last = frames[-1]
            pos = end if last[1] != 5 else last[0]
        tt = max(t, frames[0][2])
        blob = b"".join(console_frame(tt, fr, c) for c in split_commands(cmds))
        inserts.setdefault(pos, []).append(blob)
    added = sum(len(b) for bl in inserts.values() for b in bl)
    nframes = sum(len(split_commands(c)) for _, c in commands)

    out = bytearray(data[:start])
    p = start
    for pos in sorted(inserts):
        out += data[p:pos]
        for b in inserts[pos]:
            out += b
        p = pos
    out += data[p:end]
    tail = data[end:]
    shift = added
    # reescreve o diretorio (os segmentos depois do editado andam `shift` bytes)
    if hdr.entries and hdr.entries[0].type != -1 and 544 <= hdr.dir_offset <= len(data) - 4:
        body_end = hdr.dir_offset
        if body_end > end:
            out += data[end:body_end]
            tail = data[body_end:]
        else:
            tail = b""
        new_dir_off = len(out)
        d = bytearray(struct.pack("<i", len(hdr.entries)))
        for k, e in enumerate(hdr.entries):
            off = e.offset + (shift if e.offset > start else 0)
            ln = e.length + (shift if k == seg else 0)
            frs = e.frames + (nframes if k == seg else 0)
            d += DIR_ENTRY.pack(e.type, e.description.encode("latin-1")[:63], e.flags, e.cd_track, e.duration,
                                frs, off, ln)
        out += d
        struct.pack_into("<i", out, 540, new_dir_off)
    else:
        out += tail
    with open(dst, "wb") as f:
        f.write(out)
    return dst
