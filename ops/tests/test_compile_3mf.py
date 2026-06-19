# -*- coding: utf-8 -*-
"""Regression tests for compile_3mf (Stage 4).

Run from the project root:  python ops/tests/test_compile_3mf.py
Exits non-zero on the first failed assertion.

Per the TZ T5.3:
  1. square-with-hole  -> through-hole is solid-free, linear dimensions correct
  2. islands + base_plate (raised) -> disjoint contours fused into one body
  3. broken mesh -> the manifold validator (T3) rejects it
Plus: cutout through-holes, and 3MF export reimports watertight with unit=mm.
"""
import os
import sys
import io
import zipfile

import trimesh
from shapely.geometry import Polygon, MultiPolygon

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'ops', 'scripts'))

import pipeline_config as pc          # noqa: E402
import compile_3mf as C               # noqa: E402

PASS = 0


def check(name, cond):
    global PASS
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}")
        sys.exit(1)


def cfg(**over):
    c = pc.three_mf_config()
    c.update(over)
    return c


# ---- T0: config from SSOT ------------------------------------------------
c0 = pc.three_mf_config()
check("T0 three_mf from SSOT (cutout, 500mm, 4mm)",
      c0['polarity'] == 'cutout' and c0['target_long_side_mm'] == 500.0
      and c0['extrusion_height_mm'] == 4.0)
check("T0 override hierarchy (COMP > config)",
      pc.three_mf_config(comp_override={'polarity': 'raised'})['polarity'] == 'raised')

# ---- 1. square with a hole (raised): through-hole + dimensions -----------
# target 100mm so 100px -> 100mm (within the 550x450x450 printer bounds).
VW = VH = 100.0
C1 = cfg(polarity='raised', base_plate=False, target_long_side_mm=100.0)
frame = MultiPolygon([Polygon([(0, 0), (100, 0), (100, 100), (0, 100)],
                              [[(30, 30), (70, 30), (70, 70), (30, 70)]])])
m, px = C.build_mesh(frame, VW, VH, C1)
ok, diag = C.validate_mesh(m, C1)
check("1 square-with-hole is watertight volume>0", ok and diag['watertight'])
check("1 px_to_mm = 100/100 = 1.0", abs(px - 1.0) < 1e-9)
check("1 dimensions: 100px*1 = 100mm each side",
      abs(diag['bbox_mm'][0] - 100.0) < 1e-3 and abs(diag['bbox_mm'][1] - 100.0) < 1e-3)
# through-hole proven by volume: (outer 100x100 - hole 40x40) * 4mm. A blind
# pocket or filled hole would not match this.
exp1 = (100 * 100 - 40 * 40) * 4
check("1 through-hole: volume == (outer-hole)*height",
      abs(diag['volume_mm3'] - exp1) < exp1 * 0.02)

# ---- 2. two islands + base plate (raised) -> one connected body ----------
islands = MultiPolygon([Polygon([(0, 0), (20, 0), (20, 20), (0, 20)]),
                        Polygon([(40, 0), (60, 0), (60, 20), (40, 20)])])
mb, _ = C.build_mesh(islands, 60.0, 20.0, cfg(polarity='raised', base_plate=True))
okb, dgb = C.validate_mesh(mb, cfg(polarity='raised', base_plate=True))
check("2 base plate fuses islands: watertight", okb and dgb['watertight'])
check("2 islands are one connected body", mb.body_count == 1)

# ---- 3. broken mesh -> validator (T3) rejects it -------------------------
boxm = trimesh.creation.box(extents=[10, 10, 10])
broken = trimesh.Trimesh(vertices=boxm.vertices, faces=boxm.faces[:-2])  # holes
okx, dgx = C.validate_mesh(broken, cfg())
check("3 broken mesh fails validator", not okx)
check("3 broken mesh flagged not watertight",
      any('watertight' in r for r in dgx['reasons']))

# ---- 4. cutout through-hole + 3MF export roundtrip -----------------------
# a solid black square -> the plate gets a through-hole shaped like it.
solid = MultiPolygon([Polygon([(20, 20), (80, 20), (80, 80), (20, 80)])])
C4 = cfg(polarity='cutout', target_long_side_mm=100.0)
mc, _ = C.build_mesh(solid, VW, VH, C4)
okc, dgc = C.validate_mesh(mc, C4)
check("4 cutout plate is watertight", okc and dgc['watertight'])
# through-hole proven by volume: plate 100x100 minus the 60x60 shape, *4mm.
exp4 = (100 * 100 - 60 * 60) * 4
check("4 cutout through-hole: volume == (plate-shape)*height",
      abs(dgc['volume_mm3'] - exp4) < exp4 * 0.02)
data = C.set_3mf_unit(bytes(mc.export(file_type='3mf')), 'millimeter')
z = zipfile.ZipFile(io.BytesIO(data))
model = [n for n in z.namelist() if n.endswith('3dmodel.model')][0]
check("4 exported 3MF declares unit=millimeter", b'millimeter' in z.read(model))
re_m = trimesh.load(io.BytesIO(data), file_type='3mf')
re_m = re_m.to_geometry() if hasattr(re_m, 'to_geometry') else re_m
check("4 3MF reimports watertight", re_m.is_watertight)

print(f"\nAll {PASS} compile_3mf assertions passed.")
