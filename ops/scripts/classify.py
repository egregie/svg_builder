# -*- coding: utf-8 -*-
"""A07: Image classifier (TZ v3.1).

Deterministic, offline, free. Classifies an input raster into one of 7 classes
and derives the render mode, detail level, aspect ratio and target canvas.

Taxonomy: HUMAN_PHOTO, OBJECT_PHOTO, LOGO, ICON, ILLUSTRATION,
          PACKAGE_DESIGN, TECHNICAL_GRAPHIC.

Signals (all local): OpenCV Haar cascades (faces/bodies), colour count,
gradient/tonality, edge sharpness, alpha presence, aspect ratio, size.

API:
    classify(image_path) -> dict with keys:
        input_type, render_mode, vector_detail_level, is_tonal,
        source_width, source_height, aspect_ratio, target_canvas,
        preserve_aspect_ratio, signals
CLI:
    python ops/scripts/classify.py <image_path>
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

CANVAS_BASE = 1024

DETAIL_BY_CLASS = {
    'HUMAN_PHOTO': 'HIGH', 'OBJECT_PHOTO': 'HIGH', 'ILLUSTRATION': 'HIGH',
    'LOGO': 'ULTRA', 'ICON': 'ULTRA', 'PACKAGE_DESIGN': 'ULTRA',
    'TECHNICAL_GRAPHIC': 'ULTRA',
}

# Classes whose render mode follows tonality; others are fixed in MODE_BY_CLASS.
TONAL_SENSITIVE = {'ILLUSTRATION', 'PACKAGE_DESIGN'}
MODE_BY_CLASS = {
    'HUMAN_PHOTO': 'SKETCH_VECTOR', 'OBJECT_PHOTO': 'SKETCH_VECTOR',
    'LOGO': 'STANDARD_VECTOR', 'ICON': 'STANDARD_VECTOR',
    'TECHNICAL_GRAPHIC': 'STANDARD_VECTOR',
}

_CASCADES = None


def _load_cascades():
    global _CASCADES
    if _CASCADES is None:
        base = cv2.data.haarcascades
        names = ['haarcascade_frontalface_default.xml',
                 'haarcascade_profileface.xml',
                 'haarcascade_upperbody.xml',
                 'haarcascade_fullbody.xml']
        _CASCADES = [(n, cv2.CascadeClassifier(base + n)) for n in names]
    return _CASCADES


def _load_rgb_and_alpha(image_path):
    im = Image.open(image_path)
    has_alpha = im.mode in ('RGBA', 'LA', 'PA') or 'transparency' in im.info
    rgb = np.array(im.convert('RGB'))
    return rgb, has_alpha


def detect_people(rgb):
    """Returns (faces, bodies) detection counts using Haar cascades."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    # work on a normalized size for stable detection
    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    g = cv2.resize(gray, (int(w * scale), int(h * scale))) if scale != 1.0 else gray
    g = cv2.equalizeHist(g)
    faces = bodies = 0
    minsz = max(24, int(min(g.shape) * 0.08))
    for name, cas in _load_cascades():
        if cas.empty():
            continue
        found = cas.detectMultiScale(g, 1.1, 5, minSize=(minsz, minsz))
        n = len(found)
        if 'face' in name:
            faces += n
        else:
            bodies += n
    return faces, bodies


def measure_tonality(rgb):
    """Returns dict of tonality signals."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    pixels = rgb.reshape(-1, 3)
    # unique colours after coarse quantization (ignore compression noise)
    quant = (pixels // 16 * 16)
    sample = quant if len(quant) <= 200000 else quant[
        np.random.RandomState(0).choice(len(quant), 200000, replace=False)]
    unique_colors = len(np.unique(sample, axis=0))
    # gradient presence: blur-vs-original mean diff
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    grad_diff = float(np.mean(cv2.absdiff(gray, blurred)))
    # edge sharpness: fraction of strong edges
    edges = cv2.Canny(gray, 80, 200)
    edge_frac = float((edges > 0).mean())
    # local variance (texture/noise)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # smooth-region fraction: low local std
    k = 7
    mean = cv2.boxFilter(gray.astype(np.float32), -1, (k, k))
    sq = cv2.boxFilter((gray.astype(np.float32)) ** 2, -1, (k, k))
    local_std = np.sqrt(np.maximum(sq - mean ** 2, 0))
    flat_frac = float((local_std < 4).mean())
    return {
        'unique_colors': unique_colors,
        'grad_diff': round(grad_diff, 3),
        'edge_frac': round(edge_frac, 4),
        'lap_var': round(lap_var, 1),
        'flat_frac': round(flat_frac, 3),
    }


def aspect_ratio_str(w, h):
    g = math.gcd(w, h)
    return f'{w // g}:{h // g}' if g else f'{w}:{h}'


def target_canvas(w, h, base=CANVAS_BASE):
    if w >= h:
        return {'width': base, 'height': max(1, round(base * h / w))}
    return {'width': max(1, round(base * w / h)), 'height': base}


def classify(image_path, override_type=None):
    rgb, has_alpha = _load_rgb_and_alpha(image_path)
    h, w = rgb.shape[:2]
    long_ar = max(w, h) / max(1, min(w, h))
    is_square = 0.8 <= (w / h) <= 1.25

    faces, bodies = detect_people(rgb)
    t = measure_tonality(rgb)

    # Tonality verdict: photo/paint-like if rich colour AND gradients AND not mostly flat.
    # Flat graphics (logos/icons) stay well below 700 colours, so they never trip this.
    is_tonal = (t['unique_colors'] > 700 and t['grad_diff'] > 1.5
                and t['flat_frac'] < 0.6)
    few_colors = t['unique_colors'] <= 600
    sharp_flat = t['flat_frac'] >= 0.55 and t['edge_frac'] < 0.12
    # Flat, few-colour graphics (logos/icons/line-art) must never be treated as
    # photos even if a Haar cascade false-fires on circular text or a mark.
    flat_graphic = t['unique_colors'] <= 80 and t['flat_frac'] >= 0.5
    person_detected = (faces >= 1 or bodies >= 1) and not flat_graphic

    if override_type:
        input_type = override_type
    elif person_detected:
        input_type = 'HUMAN_PHOTO'
    elif is_tonal:
        input_type = 'OBJECT_PHOTO'
    elif few_colors and sharp_flat:
        if is_square and has_alpha and max(w, h) <= 512:
            input_type = 'ICON'
        elif long_ar >= 3.0:
            input_type = 'TECHNICAL_GRAPHIC'
        elif long_ar >= 2.0:
            input_type = 'LOGO'
        elif is_square and has_alpha:
            input_type = 'ICON'
        else:
            input_type = 'LOGO'
    else:
        input_type = 'ILLUSTRATION'

    # Render mode
    if input_type in TONAL_SENSITIVE:
        render_mode = 'SKETCH_VECTOR' if is_tonal else 'STANDARD_VECTOR'
    else:
        render_mode = MODE_BY_CLASS.get(input_type, 'STANDARD_VECTOR')

    detail = DETAIL_BY_CLASS.get(input_type, 'HIGH')

    result = {
        'input_type': input_type,
        'render_mode': render_mode,
        'vector_detail_level': detail,
        'is_tonal': bool(is_tonal),
        'source_width': int(w),
        'source_height': int(h),
        'aspect_ratio': aspect_ratio_str(w, h),
        'target_canvas': target_canvas(w, h),
        'preserve_aspect_ratio': True,
        'signals': {'faces': int(faces), 'bodies': int(bodies),
                    'has_alpha': bool(has_alpha), **t},
    }

    # Sketch detail directives (TZ v3.2). Honoured by sketch_vectorize for
    # photo/portrait line extraction; recorded in the passport metadata.
    if result['render_mode'] == 'SKETCH_VECTOR':
        result.update({
            'line_quality': detail,
            'noise_reduction': 'MEDIUM',
            'min_line_width': 0.4,
            'max_line_width': 2.0,
            'keep_facial_details': input_type == 'HUMAN_PHOTO',
            'keep_hair_details': input_type == 'HUMAN_PHOTO',
            'keep_clothing_details': input_type == 'HUMAN_PHOTO',
            'remove_texture_noise': True,
        })
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    override = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(classify(sys.argv[1], override), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
