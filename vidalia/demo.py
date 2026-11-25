"""Leitura do container .dem do GoldSrc (protocolo de demo 5)."""
import os
import struct
from dataclasses import dataclass, field

from .bitreader import ParseError

HEADER_SIZE = 544
DIR_ENTRY = struct.Struct("<i64siifiii")
FRAME_HDR = struct.Struct("<Bfi")

# ref_params_t (58 valores de 4 bytes)
REF_FMT = struct.Struct("<" + "f" * 17 + "i" * 5 + "f" * 10 + "f" * 3 + "i" + "f" * 3 + "f" + "f" * 3 + "i" * 9 + "i" * 4 + "ii")
USERCMD = struct.Struct("<hBx3f3fbxHbbxxi3f")
MOVEVARS_SIZE = 132
NETINFO_SIZE = 4 + REF_FMT.size + USERCMD.size + MOVEVARS_SIZE + 16  # 436
EVENT_FRAME = struct.Struct("<iifii3f3f3fiffiiii")  # 84 bytes

IN_ATTACK = 1
IN_JUMP = 2
IN_DUCK = 4
IN_ATTACK2 = 2048

assert REF_FMT.size == 232 and USERCMD.size == 52 and NETINFO_SIZE == 436


@dataclass
class DirEntry:
    type: int
    description: str
    flags: int
    cd_track: int
    duration: float
    frames: int
    offset: int
    length: int


@dataclass
class DemoHeader:
    demo_protocol: int
    net_protocol: int
    map_name: str
    game_dir: str
    map_crc: int
    dir_offset: int
    entries: list = field(default_factory=list)
    file_size: int = 0


@dataclass
class NetFrame:
    segment: int
    time: float
    frame: int
    kind: int
    # ref_params
    vieworg: tuple
    viewangles: tuple
    frametime: float
    onground: int
    waterlevel: int
    simvel: tuple
    simorg: tuple
    health: float
    punchangle: tuple
    playernum: int
    viewentity: int
    cl_viewangles: tuple
    # usercmd
    msec: int
    cmd_angles: tuple
    forwardmove: float
    sidemove: float
    upmove: float
    buttons: int
    weaponselect: int
    incoming_sequence: int
    outgoing_sequence: int
    msg: bytes


@dataclass
class EventFrame:
    segment: int
    time: float
    frame: int
    index: int
    delay: float
    flags: int
    entindex: int
    origin: tuple
    angles: tuple
    velocity: tuple
    ducking: int
    fparam1: float
    fparam2: float
    iparam1: int
    iparam2: int
    bparam1: int
    bparam2: int


@dataclass
class ClientDataFrame:
    segment: int
    time: float
    frame: int
    origin: tuple
    viewangles: tuple
    weaponbits: int
    fov: float


@dataclass
class ConsoleFrame:
    segment: int
    time: float
    frame: int
    command: str


def _cstr(b):
    return b.split(b"\0", 1)[0].decode("latin-1")


def read_header(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        h = f.read(HEADER_SIZE)
        if len(h) != HEADER_SIZE or h[:8] != b"HLDEMO\0\0":
            raise ParseError("Arquivo nao e uma demo GoldSrc (cabecalho HLDEMO ausente).")
        dp, np_ = struct.unpack_from("<ii", h, 8)
        crc, off = struct.unpack_from("<Ii", h, 536)
        hdr = DemoHeader(dp, np_, _cstr(h[16:276]), _cstr(h[276:536]), crc, off, file_size=size)
        if dp != 5:
            raise ParseError("Protocolo de demo %d nao suportado (esperado 5)." % dp)
        if 544 <= off <= size - 4:
            f.seek(off)
            count = struct.unpack("<i", f.read(4))[0]
            if 0 <= count <= 1024:
                for _ in range(count):
                    raw = f.read(DIR_ENTRY.size)
                    if len(raw) < DIR_ENTRY.size:
                        break
                    t, d, fl, cd, du, fr, o, ln = DIR_ENTRY.unpack(raw)
                    hdr.entries.append(DirEntry(t, _cstr(d), fl, cd, du, fr, o, ln))
        if not hdr.entries:
            # diretorio corrompido (demo interrompida): varre a partir do cabecalho
            hdr.entries.append(DirEntry(-1, "RECUPERADO", 0, 0, 0.0, 0, HEADER_SIZE, size - HEADER_SIZE))
    return hdr


def iter_frames(path, hdr=None, warnings=None, pos=None):
    """Gera frames (NetFrame, EventFrame, ClientDataFrame, ConsoleFrame, ...).

    Se `pos` for uma lista, pos[0] recebe o offset (em bytes) do frame atual,
    o que permite calcular o progresso real da leitura."""
    hdr = hdr or read_header(path)
    with open(path, "rb") as f:
        data = f.read()
    for seg, entry in enumerate(hdr.entries):
        start = entry.offset
        end = min(len(data), entry.offset + entry.length) if entry.type != -1 else len(data)
        if start < HEADER_SIZE or start >= len(data):
            if warnings is not None:
                warnings.append("Segmento %d fora dos limites; ignorado." % seg)
            continue
        p = start
        while p + 9 <= end:
            if pos is not None:
                pos[0] = p
            kind, t, fr = FRAME_HDR.unpack_from(data, p)
            p += 9
            try:
                if kind in (0, 1):
                    if p + NETINFO_SIZE + 32 > end:
                        raise ParseError("frame de rede truncado")
                    ts = struct.unpack_from("<f", data, p)[0]
                    r = REF_FMT.unpack_from(data, p + 4)
                    c = USERCMD.unpack_from(data, p + 4 + REF_FMT.size)
                    q = p + NETINFO_SIZE
                    seqs = struct.unpack_from("<7i", data, q)
                    ln = struct.unpack_from("<i", data, q + 28)[0]
                    q += 32
                    if ln < 0 or ln > 65536 or q + ln > end:
                        raise ParseError("tamanho de mensagem invalido (%d)" % ln)
                    yield NetFrame(
                        seg, t, fr, kind,
                        vieworg=r[0:3], viewangles=r[3:6], frametime=r[15],
                        onground=r[20], waterlevel=r[21], simvel=r[22:25], simorg=r[25:28],
                        cl_viewangles=r[32:35], health=r[35], punchangle=r[40:43],
                        viewentity=r[44], playernum=r[45],
                        msec=c[1], cmd_angles=c[2:5], forwardmove=c[5], sidemove=c[6], upmove=c[7],
                        buttons=c[9], weaponselect=c[11],
                        incoming_sequence=seqs[0], outgoing_sequence=seqs[4],
                        msg=data[q:q + ln])
                    p = q + ln
                elif kind == 2:
                    pass
                elif kind == 3:
                    yield ConsoleFrame(seg, t, fr, _cstr(data[p:p + 64]))
                    p += 64
                elif kind == 4:
                    v = struct.unpack_from("<6fif", data, p)
                    yield ClientDataFrame(seg, t, fr, v[0:3], v[3:6], v[6], v[7])
                    p += 32
                elif kind == 5:
                    break
                elif kind == 6:
                    v = EVENT_FRAME.unpack_from(data, p)
                    yield EventFrame(seg, t, fr, index=v[1], delay=v[2], flags=v[0], entindex=v[4],
                                     origin=v[5:8], angles=v[8:11], velocity=v[11:14], ducking=v[14],
                                     fparam1=v[15], fparam2=v[16], iparam1=v[17], iparam2=v[18],
                                     bparam1=v[19], bparam2=v[20])
                    p += EVENT_FRAME.size
                elif kind == 7:
                    p += 8
                elif kind == 8:
                    ln = struct.unpack_from("<i", data, p + 4)[0]
                    if ln < 0 or ln > 1024:
                        raise ParseError("frame de som invalido")
                    p += 8 + ln + 16
                elif kind == 9:
                    ln = struct.unpack_from("<i", data, p)[0]
                    if ln < 0 or p + 4 + ln > end:
                        raise ParseError("buffer de demo invalido")
                    p += 4 + ln
                else:
                    raise ParseError("tipo de frame desconhecido %d" % kind)
            except (ParseError, struct.error) as e:
                if warnings is not None:
                    warnings.append("Segmento %d, offset %d: %s; leitura do segmento interrompida." % (seg, p, e))
                break
