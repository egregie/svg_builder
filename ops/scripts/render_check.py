# -*- coding: utf-8 -*-
"""Quick: rasterize released SVGs to PNG for a visual sanity check."""
import os, sys
import resvg_py
out = 'ops/qa_previews/render_check'
os.makedirs(out, exist_ok=True)
for p in sys.argv[1:]:
    try:
        png = resvg_py.svg_to_bytes(svg_path=p)
        dst = os.path.join(out, os.path.splitext(os.path.basename(p))[0] + '.png')
        with open(dst, 'wb') as f:
            f.write(bytes(png))
        print(f"[OK] {p} -> {dst}")
    except Exception as e:
        print(f"[ERR] {p}: {e}")
