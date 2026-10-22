"""Lectura del GeoPackage (GADM) y utilidades de geometría, sin GDAL."""
import struct
import numpy as np

B = 8  # tamaño de bloque en píxeles


def parse_geom(blob):
    """Devuelve una lista de polígonos; cada uno es una lista de anillos (arrays Nx2 lon/lat)."""
    flags = blob[3]
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
    polys = []

    def rd(off):
        bo = '<' if blob[off] == 1 else '>'
        t = struct.unpack_from(bo + 'I', blob, off + 1)[0] % 1000
        off += 5
        if t == 6:  # MultiPolygon
            n = struct.unpack_from(bo + 'I', blob, off)[0]; off += 4
            for _ in range(n):
                off = rd(off)
            return off
        if t == 3:  # Polygon
            nr = struct.unpack_from(bo + 'I', blob, off)[0]; off += 4
            rings = []
            for _ in range(nr):
                npnt = struct.unpack_from(bo + 'I', blob, off)[0]; off += 4
                a = np.frombuffer(blob, dtype=bo + 'f8', count=npnt * 2, offset=off).reshape(npnt, 2).astype(np.float64)
                off += npnt * 16
                rings.append(a)
            polys.append(rings)
            return off
        raise ValueError('tipo WKB %d' % t)

    rd(8 + env)
    return polys


def dp(points, tol):
    """Simplificación Douglas-Peucker."""
    n = len(points)
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p = points[a + 1:b]; A = points[a]; Bp = points[b]
        d = Bp - A; L = float(np.hypot(d[0], d[1]))
        if L == 0:
            dist = np.hypot(p[:, 0] - A[0], p[:, 1] - A[1])
        else:
            dist = np.abs(d[0] * (p[:, 1] - A[1]) - d[1] * (p[:, 0] - A[0])) / L
        i = int(np.argmax(dist))
        if dist[i] > tol:
            k = a + 1 + i; keep[k] = True
            stack.append((a, k)); stack.append((k, b))
    return points[keep]


def ring_area(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def ring_centroid(r):
    x, y = r[:, 0], r[:, 1]
    cr = x[:-1] * y[1:] - x[1:] * y[:-1]
    a = 0.5 * cr.sum()
    if abs(a) < 1e-12:
        return float(x.mean()), float(y.mean())
    return float(((x[:-1] + x[1:]) * cr).sum() / (6 * a)), float(((y[:-1] + y[1:]) * cr).sum() / (6 * a))
