"""Lector mínimo de GeoTIFF con teselas LZW + predictor 2 (sin imagecodecs/GDAL)."""
import numpy as np
import tifffile


def lzw_decode(data):
    out = bytearray()
    bitbuf = 0
    bitcnt = 0
    codesize = 9
    table = [bytes([i]) for i in range(256)] + [b'', b'']
    nextcode = 258
    prev = None
    pos = 0
    n = len(data)
    while True:
        while bitcnt < codesize:
            if pos >= n:
                return bytes(out)
            bitbuf = (bitbuf << 8) | data[pos]
            pos += 1
            bitcnt += 8
        bitcnt -= codesize
        code = (bitbuf >> bitcnt) & ((1 << codesize) - 1)
        bitbuf &= (1 << bitcnt) - 1
        if code == 257:
            break
        if code == 256:
            del table[258:]
            nextcode = 258
            codesize = 9
            prev = None
            continue
        if prev is None:
            entry = table[code]
            out += entry
            prev = entry
            continue
        if code < nextcode:
            entry = table[code]
        else:
            entry = prev + prev[:1]
        out += entry
        table.append(prev + entry[:1])
        nextcode += 1
        if nextcode >= (1 << codesize) - 1 and codesize < 12:
            codesize += 1
        prev = entry
    return bytes(out)


class Reader:
    def __init__(self, path):
        self.t = tifffile.TiffFile(path)
        p = self.t.pages[0]
        self.p = p
        self.H, self.W = p.shape
        self.th, self.tw = p.tilelength, p.tilewidth
        self.nx = -(-self.W // self.tw)
        self.ny = -(-self.H // self.th)
        self.offsets = p.dataoffsets
        self.counts = p.databytecounts
        self.fh = self.t.filehandle
        assert p.compression == 5 and p.predictor == 2 and p.dtype == np.uint8
        sc = p.tags['ModelPixelScaleTag'].value
        tp = p.tags['ModelTiepointTag'].value
        self.dx, self.dy = sc[0], sc[1]
        self.lon0, self.lat0 = tp[3], tp[4]

    def nonempty(self):
        return [i for i, c in enumerate(self.counts) if c > 0]

    def tile(self, i):
        self.fh.seek(self.offsets[i])
        raw = self.fh.read(self.counts[i])
        buf = lzw_decode(raw)
        a = np.frombuffer(buf, dtype=np.uint8)
        if a.size != self.th * self.tw:
            raise ValueError('tesela %d: %d bytes' % (i, a.size))
        a = a.reshape(self.th, self.tw)
        return np.cumsum(a, axis=1, dtype=np.uint8)

    def origin(self, i):
        ty, tx = divmod(i, self.nx)
        return ty * self.th, tx * self.tw
