"""Prepara los datos del mapa 3D.

Entradas (no van al repositorio, son pesadas):
  - mbfire_col1_peru_accumulated_burned-fire_accumulated_2013_2024.tif  (MapBiomas Fuego Perú, 30 m, 0/1)
  - gadm41_PER.gpkg  (límites departamentales GADM 4.1)
Salida:
  - data/geo-mapa3d.json  (departamentos simplificados, hectáreas por departamento y columnas de ~10 km)

Uso:  python pipeline/preparar_mapa3d.py RUTA_TIF RUTA_GPKG
"""
import json, sqlite3, sys
import numpy as np
from PIL import Image, ImageDraw
from lzwtif import Reader
from geoproc import B, parse_geom, dp, ring_area, ring_centroid

tif, gpkg = sys.argv[1], sys.argv[2]
R = Reader(tif)
LON0, LAT0, DX, DY = R.lon0, R.lat0, R.dx, R.dy

# 1) Suma de píxeles quemados por bloques de 8x8 (240 m)
grid = np.zeros((R.H // B + 1, R.W // B + 1), np.uint8)
for i in R.nonempty():
    t = R.tile(i); y0, x0 = R.origin(i)
    s = t.reshape(t.shape[0] // B, B, t.shape[1] // B, B).sum(axis=(1, 3), dtype=np.uint8)
    r0, c0 = y0 // B, x0 // B
    s = s[:grid.shape[0] - r0, :grid.shape[1] - c0]  # teselas del borde
    grid[r0:r0 + s.shape[0], c0:c0 + s.shape[1]] = s
gh, gw = grid.shape
lat = LAT0 - (np.arange(gh) * B + B / 2) * DY
ha_px = (DX * 111.320 * np.cos(np.radians(lat))) * (DY * 110.574) * 100  # hectáreas por píxel
hab = grid.astype(np.float64) * ha_px[:, None]
print('Área quemada acumulada: %.0f ha' % hab.sum())

# 2) Departamentos: rasterizar a la malla de bloques y sumar hectáreas
con = sqlite3.connect('file:' + gpkg + '?mode=ro', uri=True)
rows = con.execute('select NAME_1, geom from ADM_ADM_1 order by NAME_1').fetchall()
nombre = {'Ancash': 'Áncash', 'Lima Province': 'Lima'}
dep, claves = {}, {}
label = np.zeros((gh, gw), np.uint8)  # un solo departamento por bloque (evita contar dos veces los bordes)
for k, (name, blob) in enumerate(rows, 1):
    polys = parse_geom(blob)
    im = Image.new('L', (gw, gh), 0); d = ImageDraw.Draw(im)
    for rings in polys:
        for j, r in enumerate(rings):
            d.polygon([((x - LON0) / (DX * B), (LAT0 - y) / (DY * B)) for x, y in r], fill=255 if j == 0 else 0)
    label[np.array(im) > 0] = k
    n = nombre.get(name, name); claves.setdefault(n, []).append(k)
    out = []
    for rings in polys:
        if abs(ring_area(rings[0])) < 0.004:
            continue  # islotes menores a ~45 km²
        s = dp(rings[0], 0.012)
        if len(s) >= 4:
            out.append([[round(float(x), 3), round(float(y), 3)] for x, y in s])
    e = dep.setdefault(n, {'p': [], 'ha': 0.0})
    e['p'] += out
for n, ks in claves.items():
    dep[n]['ha'] = float(hab[np.isin(label, ks)].sum())
for n, e in dep.items():
    best = max(e['p'], key=lambda r: abs(ring_area(np.array(r))))
    cx, cy = ring_centroid(np.array(best))
    e['c'] = [round(cx, 3), round(cy, 3)]; e['ha'] = round(e['ha'])

# 3) Columnas: celdas de 40x40 bloques (~9,6 km)
K = 40
H2, W2 = -(-gh // K), -(-gw // K)
pad = np.zeros((H2 * K, W2 * K)); pad[:gh, :gw] = hab
cell = pad.reshape(H2, K, W2, K).sum(axis=(1, 3))
cel = [[round(LON0 + (c + .5) * K * B * DX, 3), round(LAT0 - (r + .5) * K * B * DY, 3), int(round(cell[r, c]))]
       for r, c in zip(*np.nonzero(cell >= 30))]

json.dump({'celda': round(K * B * DX, 4), 'dep': dep, 'cel': cel}, open('data/geo-mapa3d.json', 'w'),
          ensure_ascii=False, separators=(',', ':'))
print('Departamentos:', len(dep), '| celdas:', len(cel))
