"""Leitores de bytes e de bits no formato usado pela engine GoldSrc.

Os bits sao lidos LSB-first dentro de cada byte (mesma convencao de MSG_ReadBits).
"""
import struct


class ParseError(Exception):
    pass


class ByteReader:
    __slots__ = ("data", "pos", "end")

    def __init__(self, data, pos=0, end=None):
        self.data = data
        self.pos = pos
        self.end = len(data) if end is None else end

    def remaining(self):
        return self.end - self.pos

    def _need(self, n):
        if self.pos + n > self.end:
            raise ParseError("leitura alem do fim da mensagem (%d+%d>%d)" % (self.pos, n, self.end))

    def u8(self):
        self._need(1)
        v = self.data[self.pos]
        self.pos += 1
        return v

    def s8(self):
        v = self.u8()
        return v - 256 if v > 127 else v

    def u16(self):
        self._need(2)
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def s16(self):
        self._need(2)
        v = struct.unpack_from("<h", self.data, self.pos)[0]
        self.pos += 2
        return v

    def s32(self):
        self._need(4)
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def u32(self):
        self._need(4)
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def f32(self):
        self._need(4)
        v = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        return v

    def coord(self):
        return self.s16() / 8.0

    def angle(self):
        return self.u8() * (360.0 / 256.0)

    def skip(self, n):
        self._need(n)
        self.pos += n

    def raw(self, n):
        self._need(n)
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def string(self):
        i = self.data.find(b"\0", self.pos, self.end)
        if i < 0:
            raise ParseError("string sem terminador")
        s = self.data[self.pos:i].decode("utf-8", "replace")
        self.pos = i + 1
        return s


class BitReader:
    """Leitor de bits sobre um buffer, iniciando no byte `pos`."""

    __slots__ = ("data", "bit", "endbit")

    def __init__(self, data, pos=0, end=None):
        self.data = data
        self.bit = pos * 8
        self.endbit = (len(data) if end is None else end) * 8

    def read(self, n):
        if n == 0:
            return 0
        if self.bit + n > self.endbit:
            raise ParseError("leitura de bits alem do fim da mensagem")
        byte = self.bit >> 3
        off = self.bit & 7
        nbytes = (off + n + 7) >> 3
        chunk = int.from_bytes(self.data[byte:byte + nbytes], "little")
        self.bit += n
        return (chunk >> off) & ((1 << n) - 1)

    def peek(self, n):
        b = self.bit
        try:
            return self.read(n)
        finally:
            self.bit = b

    def sbits(self, n):
        """Sinal + magnitude (MSG_ReadSBits)."""
        sign = self.read(1)
        v = self.read(n - 1)
        return -v if sign else v

    def string(self):
        out = bytearray()
        while True:
            c = self.read(8)
            if c == 0:
                break
            out.append(c)
            if len(out) > 4096:
                raise ParseError("string de bits longa demais")
        return out.decode("utf-8", "replace")

    def coord(self):
        has_int = self.read(1)
        has_frac = self.read(1)
        if not (has_int or has_frac):
            return 0.0
        sign = self.read(1)
        iv = self.read(12) if has_int else 0
        fv = self.read(3) if has_frac else 0
        v = iv + fv / 8.0
        return -v if sign else v

    def vec3coord(self):
        fx, fy, fz = self.read(1), self.read(1), self.read(1)
        return (self.coord() if fx else 0.0,
                self.coord() if fy else 0.0,
                self.coord() if fz else 0.0)

    def byte_pos(self):
        """Posicao em bytes apos alinhar (MSG_EndBitReading)."""
        return (self.bit + 7) >> 3
