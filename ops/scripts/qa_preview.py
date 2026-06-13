# -*- coding: utf-8 -*-
"""QA preview tool: renders each released SVG beside its source raster.

Usage:  python ops/scripts/qa_preview.py
Output: ops/qa_previews/_verify_COMP-NNN.png  (слева оригинал | справа рендер SVG)
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hifi_vectorize import load_image_flattened, render_svg

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

for index_path in sorted(glob.glob('03_knowledge_graph/COMP-*.json')):
    pid = os.path.splitext(os.path.basename(index_path))[0]
    svg_path = f'05_output_svg/{pid}.svg'
    if not os.path.exists(svg_path):
        print(f'{pid}: no released SVG, skipped')
        continue
    with open(index_path, encoding='utf-8') as f:
        data = json.load(f)
    src = None
    for d in ['01_input_raster/high_contrast', '01_input_raster/complex_gradients', 'input']:
        p = os.path.join(d, data['source_file'])
        if os.path.exists(p):
            src = p
            break
    if not src:
        print(f'{pid}: source raster {data["source_file"]} not found, skipped')
        continue
    rgb = load_image_flattened(src)
    h, w = rgb.shape[:2]
    with open(svg_path, encoding='utf-8') as f:
        rendered = render_svg(f.read(), w, h)
    sep = np.full((h, 8, 3), 255, np.uint8)
    side = np.concatenate([rgb, sep, rendered], axis=1)
    os.makedirs('ops/qa_previews', exist_ok=True)
    out = f'ops/qa_previews/_verify_{pid}.png'
    Image.fromarray(side).save(out)
    print(f'{pid}: {data["source_file"]} -> {out}')
