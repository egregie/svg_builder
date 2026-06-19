# -*- coding: utf-8 -*-
"""SSOT loader (svg_cad T0).

Single accessor for the machine-readable pipeline config in
00_governance/pipeline_config.json. Gate thresholds, the active colour model and
the spec version live there; code reads them here instead of hard-coding, so
there is one source of truth (no version/threshold drift — audit E-4/E-5).

Literal fallbacks mirror the JSON only so the pipeline still runs if the file is
missing; the JSON is authoritative when present.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), '..', '..',
                     '00_governance', 'pipeline_config.json')

_FALLBACK = {
    'spec_version': '3.5',
    'color_model': {'active': 'monochrome'},
    'gates': {
        'SKETCH_VECTOR': {'ssim_min': 0.75, 'render_black_frac_max': 0.5},
        'STANDARD_VECTOR': {'ssim_min': 0.93},
        'COLOR_LEGACY': {'ssim_min': 0.93},
    },
}

_CACHE = None


def get_config():
    global _CACHE
    if _CACHE is None:
        try:
            with open(_PATH, 'r', encoding='utf-8') as f:
                _CACHE = json.load(f)
        except Exception:
            _CACHE = _FALLBACK
    return _CACHE


def gate(render_mode, key='ssim_min', default=None):
    """Return a gate value for a render_mode, e.g. gate('SKETCH_VECTOR')."""
    g = get_config().get('gates', {}).get(render_mode, {})
    if key in g:
        return g[key]
    fb = _FALLBACK['gates'].get(render_mode, {})
    return fb.get(key, default)


def spec_version():
    return get_config().get('spec_version', _FALLBACK['spec_version'])


def active_color_model():
    return get_config().get('color_model', {}).get('active', 'monochrome')
