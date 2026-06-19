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


_THREE_MF_FALLBACK = {
    'target_long_side_mm': 500.0, 'extrusion_height_mm': 4.0,
    'base_plate': False, 'base_plate_mm': 0.6, 'polarity': 'cutout',
    'min_feature_mm': 0.8, 'max_printer_bounds_mm': [550.0, 450.0, 450.0],
    'output_units': 'millimeter',
}


def three_mf_config(comp_override=None, cli_override=None):
    """Resolve the Stage-4 config per the hierarchy of truth (compile_3mf T0):
    CLI args > COMP-*.json 'three_mf_override' > pipeline_config.json 'three_mf'
    > built-in fallback. Each later source only overrides provided keys."""
    cfg = dict(_THREE_MF_FALLBACK)
    cfg.update({k: v for k, v in get_config().get('three_mf', {}).items()
                if not k.startswith('$')})
    if comp_override:
        cfg.update(comp_override)
    if cli_override:
        cfg.update(cli_override)
    return cfg
