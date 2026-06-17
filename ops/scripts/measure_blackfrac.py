# -*- coding: utf-8 -*-
"""Measure rendered black fraction of SVGs (composited on white)."""
import sys, io
import numpy as np
import resvg_py
from PIL import Image

for p in sys.argv[1:]:
    try:
        png = bytes(resvg_py.svg_to_bytes(svg_path=p))
        im = Image.open(io.BytesIO(png)).convert('RGBA')
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        comp = Image.alpha_composite(bg, im).convert('L')
        a = np.asarray(comp)
        bf = float((a < 128).mean())
        print(f"  {p.split('/')[-1]:28s} render_black_frac={bf:.3f}")
    except Exception as e:
        print(f"  {p}: ERR {e}")
