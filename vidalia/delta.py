"""Decodificacao delta do GoldSrc (delta.lst transmitido via svc_deltadescription)."""
from .bitreader import ParseError

DT_BYTE = 1
DT_SHORT = 2
DT_FLOAT = 4
DT_INTEGER = 8
DT_ANGLE = 16
DT_TIMEWINDOW_8 = 32
DT_TIMEWINDOW_BIG = 64
DT_STRING = 128
DT_SIGNED = 0x80000000


class Field:
    __slots__ = ("name", "type", "bits", "pre", "post")

    def __init__(self, name, ftype, bits, pre=1.0, post=1.0):
        self.name = name
        self.type = ftype
        self.bits = bits
        self.pre = pre or 1.0
        self.post = post or 1.0

    def __repr__(self):
        return "Field(%s,%#x,%d)" % (self.name, self.type, self.bits)


# Meta-descricao fixa usada para transmitir as proprias descricoes delta.
META = [
    Field("fieldType", DT_INTEGER, 32),
    Field("fieldName", DT_STRING, 8),
    Field("fieldOffset", DT_INTEGER, 16),
    Field("fieldSize", DT_INTEGER, 8),
    Field("significant_bits", DT_INTEGER, 8),
    Field("premultiply", DT_FLOAT, 32, 4000.0),
    Field("postmultiply", DT_FLOAT, 32, 4000.0),
]


def read_field(br, f):
    t = f.type & ~DT_SIGNED
    signed = bool(f.type & DT_SIGNED)
    if t in (DT_BYTE, DT_SHORT, DT_INTEGER, DT_FLOAT):
        if signed:
            v = br.sbits(f.bits) if f.bits > 0 else 0
        else:
            v = br.read(f.bits)
        if t == DT_FLOAT:
            return v / f.pre * f.post
        if f.pre != 1.0 or f.post != 1.0:
            return v / f.pre * f.post
        return v
    if t == DT_ANGLE:
        return br.read(f.bits) * (360.0 / (1 << f.bits)) if f.bits else 0.0
    if t == DT_TIMEWINDOW_8:
        return br.sbits(8) / 100.0
    if t == DT_TIMEWINDOW_BIG:
        return br.sbits(f.bits) / f.pre
    if t == DT_STRING:
        return br.string()
    raise ParseError("tipo delta desconhecido %#x em %s" % (f.type, f.name))


def read_delta(br, desc, base=None):
    """Le um delta e devolve dict novo (base copiada + campos alterados)."""
    out = dict(base) if base else {}
    nbytes = br.read(3)
    mask = 0
    for i in range(nbytes):
        mask |= br.read(8) << (8 * i)
    i = 0
    while mask:
        if mask & 1:
            if i >= len(desc):
                raise ParseError("delta referencia campo %d inexistente (%d campos)" % (i, len(desc)))
            f = desc[i]
            out[f.name] = read_field(br, f)
        mask >>= 1
        i += 1
    return out


def read_description(br, count):
    fields = []
    for _ in range(count):
        d = read_delta(br, META)
        fields.append(Field(d.get("fieldName", "?"), int(d.get("fieldType", 0)),
                            int(d.get("significant_bits", 0)),
                            d.get("premultiply", 1.0), d.get("postmultiply", 1.0)))
    return fields
