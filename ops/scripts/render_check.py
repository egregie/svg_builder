# -*- coding: utf-8 -*-
"""Quick: rasterize released SVGs to PNG for a visual sanity check.

Composites the (transparent) SVG onto WHITE so the preview matches how a black
line drawing actually looks — otherwise transparent pixels display as black and
a perfectly good drawing looks like a solid blob."""
import os, io, sys
import resvg_py
from PIL import Image
out = 'ops/qa_previews/render_check'
os.makedirs(out, exist_ok=True)
for p in sys.argv[1:]:
    try:
        png = bytes(resvg_py.svg_to_bytes(svg_path=p))
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        comp = Image.alpha_composite(bg, im).convert('RGB')
        dst = os.path.join(out, os.path.splitext(os.path.basename(p))[0] + '.png')
        comp.save(dst)
        print(f"[OK] {p} -> {dst}")
    except Exception as e:
        print(f"[ERR] {p}: {e}")
