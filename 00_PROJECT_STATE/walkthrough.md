# Walkthrough: Antigravity Vectorizer Pipeline (Phase 2, Phase 3 & Section 24 Fix)

Successfully implemented Phase 2, Phase 3, and resolved Section 24 (Diagnosing and Fixing Solid-Color/Empty SVGs) of the Antigravity Vectorizer pipeline.

## Changes Made

### 1. Ingestion Restructuring (Phase 3)
- **Unified Entry Point (`input/`):** Created the `input/` directory to serve as the single entry point for all raw user images.
- **Naming Guidelines & Requirements:** Created [input/README.md](file:///c:/svg_builder/input/README.md) specifying naming conventions, supported formats, and execution instructions.
- **Automatic Routing in Deconstructor (A01):** Modified [deconstruct.py](file:///c:/svg_builder/ops/scripts/deconstruct.py) to scan `input/` and route raster copies to the appropriate subfolder in `01_input_raster/`.

### 2. SVG Compilation & Color Filtering (Phase 2 & Section 24 Fix)
- **vtracer_bridge.py (A03):** Performs iterative VTracer scaling based on anchor point thresholds.
- **starvector_inference.py (A04):** Executes HuggingFace StarVector 1B with a high-fidelity VTracer-fallback on Windows.
- **compile_svg.py (A05 & Compiler):** 
  - Added hex color parsing (`parse_hex_to_rgb`) and distance-based color token resolution (`get_closest_color_token`).
  - Added original fill extraction (`get_element_fill`) to read colors from `fill` or `style` attributes.
  - Modified `extract_layer_shapes` to filter paths: it maps each shape to its closest design token and discards elements that do not match the layer's target color token (filtering out background paths from foreground layers).
  - Groups shapes in `<g>` tags and styles them via CSS design tokens injected into the `:root` block, maintaining Zero Black Policy.

---

## Verification Results

### 1. Pipeline execution logs (Section 24 Run)
Ran the complete compilation pipeline on all 5 images:
```bash
python ops/scripts/compile_svg.py
```
- **Filter Action:** Correctly identified and discarded background elements:
  - `COMP-001`: Discarded 4 paths mapped to `--dark` (target: `--bg-alt`).
  - `COMP-002`: Discarded 6 paths mapped to `--white`/`--bg` (target: `--dark`).
  - `COMP-003`: Discarded 14 paths mapped to `--white`/`--bg`/`--bg-alt` (target: `--dark`).
  - `COMP-004`: Discarded 11 paths mapped to `--white`/`--bg`/`--bg-alt` (target: `--dark`).
  - `COMP-005`: Discarded 4 paths mapped to `--white` (target: `--dark`).
- **QA Verification:** All 5 compiled SVGs passed the QA validation gate (0 failures).

### 2. Path Count Comparison (Before vs. After Filtering)

| SVG File | Paths Before Fix | Paths After Fix (Foreground Only) | Status |
|----------|------------------|-----------------------------------|--------|
| `COMP-001.svg` | 5 | 1 | Passed |
| `COMP-002.svg` | 15 | 9 | Passed |
| `COMP-003.svg` | 44 | 30 | Passed |
| `COMP-004.svg` | 30 | 19 | Passed |
| `COMP-005.svg` | 5 | 1 | Passed |

- **Visual Consistency:** Checked that the foreground shapes are isolated and correctly colored against their corresponding background rectangle.
- **Release:** Merged changes successfully from `dev` to `master` with a merge commit.

---

## Sprint 2026-06-19: Rebuilding remaining/new SVGs from clean input/

Successfully processed the remaining and new images after directory archiving:
- `cat_1.png` -> `svg_cat_1.svg`
- `cat_2.png` -> `svg_cat_2.svg`
- `cat_3.jpg` -> `svg_cat_3.svg`
- `cat_4.jpg` -> `svg_cat_4.svg`
- `cat_5.jpg` -> `svg_cat_5.svg`
- `logo_pee.png` -> `svg_logo_pee.svg`
- `svg_full_name_ym_proskin.png` -> `svg_full_name_ym_proskin.svg`

### Verification Results
All 7 compiled SVGs successfully passed QA validation (0 failures) and are available in [05_output_svg/](file:///c:/svg_builder/05_output_svg/).

---

## svg_cad 2026-06-19: blockers T0–T3 before `compile_3mf.py` (spec 3.5)

**Status:** COMPLETED on branch `svg_cad` (not merged to `master`).

**Changes**
- **T0 — SSOT:** `00_governance/pipeline_config.json` (spec version, engine, colour model, gate thresholds) + loader `ops/scripts/pipeline_config.py`. `sketch_vectorize.SSIM_GATE` (0.75) and `hifi_vectorize.SSIM_RELEASE_GATE` (0.93) now read from it. Resolved drift: version `3.5`, deterministic VTracer engine (StarVector excluded), colour model **monochrome** (owner decision — Zero Black scoped to the legacy `--color` path).
- **T1 — artifact contract (ND-04 keystone):** schema `00_governance/schemas/svg_artifact_v1.schema.json` + module `ops/scripts/svg_contract.py`. Canonical output = standalone `<svg>` carrying `<metadata id="svgcad">` (provenance, gate_results per axis, `3mf_eligible`, viewbox/units, px→mm reservation), mirrored into the knowledge graph. Audit: `validate.py --artifacts`.
- **T2 — quality axes:** orthogonal visual (SSIM, governs 2D release) / colour (monochrome) / topological (closed paths, no raster/gradient). `3mf_eligible = mono ∧ closed ∧ STANDARD_VECTOR`; `SKETCH_VECTOR → false` always. Gate 0.75 untouched. CR v3.5 mode-recovery fallback folded into the active path.
- **T3 — filtration invariant (R-03):** `vectorize_monochrome` never merges all clusters into the background (keeps the farthest → ≥1 path); an empty foreground is flagged (`invariant_violation`) and quarantined, not silently released.
- **Regression suite:** `ops/tests/test_svg_cad.py` — 15 assertions across T0–T3.

**Verification**
- `python ops/tests/test_svg_cad.py` → 15/15 PASS.
- `python ops/scripts/compile_svg.py` (7-object corpus) → 7/7 released, 0 fail.
- `python ops/scripts/validate.py --artifacts` → 7/7 contract-conformant, 0 violations.
- Valid example: `svg_cat_3.svg` (embedded metadata passes schema). Invalid example: metadata without `viewbox` → `validate_artifact` returns an error (T1 test).

| output | render_mode | SSIM | 3mf_eligible | result |
|--------|-------------|------|--------------|--------|
| svg_cat_1.svg | SKETCH_VECTOR | 0.8881 | false | release |
| svg_cat_2.svg | SKETCH_VECTOR | 0.8589 | false | release (fallback STANDARD→SKETCH) |
| svg_cat_3.svg | STANDARD_VECTOR | 0.9540 | true | release |
| svg_cat_4.svg | SKETCH_VECTOR | 0.9436 | false | release |
| svg_cat_5.svg | SKETCH_VECTOR | 0.9447 | false | release |
| svg_logo_pee.svg | STANDARD_VECTOR | 0.9905 | true | release |
| svg_full_name_ym_proskin.svg | STANDARD_VECTOR | 0.9869 | true | release |

**Open questions**
- Full manifold/geometry validator → next TZ (`compile_3mf.py`); here only the `3mf_eligible` flag.
- ND-06 (passport versioning on re-deconstruction) — out of scope.
- `svg_full_name_ym_proskin.svg` triple-prefix is a cosmetic naming artifact from the source filename, not a blocker.

---

## compile_3mf 2026-06-19: Stage 4 — 2D SVG artifact -> printable 3MF mesh

**Status:** COMPLETED on branch `compile_3mf` (from `svg_cad`, not merged).

**Changes**
- **T0:** Variant A deps (`trimesh`, `mapbox_earcut`, `manifold3d`). SSOT `three_mf` section (cutout, 500mm long side, 4mm, printer bounds 550x450x450) + `pipeline_config.three_mf_config()` override hierarchy (CLI > COMP `three_mf_override` > config). `px_to_mm = target_long_side_mm / max(viewBoxW, viewBoxH)` (closes R-06).
- **T1:** `compile_3mf.py` parses SVG (group scale + path translate -> viewBox coords), flattens Beziers (svgpathtools), builds shapely polygons-with-holes. Vector-first; auto-fallback to raster contours (resvg render -> cv2 RETR_CCOMP) when the vector mesh is not a clean manifold. min_feature_mm cleanup; empty geometry -> quarantine.
- **T2:** scale px->mm + Y-flip; polarity **cutout** = solid plate minus shapes poking through both faces (3D boolean, manifold3d); **raised** = extrude (+ base plate union if set). Polygon-with-many-holes built as exterior-solid minus hole-prisms (earcut caps fail otherwise).
- **T3:** manifold validator — watertight, winding-consistent, volume>0, within printer bounds. Failure -> `07_output_3mf/quarantine/` with diagnostics.
- **T4:** `.3mf` export (unit=millimeter injected into the OPC model XML) + `mesh_artifact_v1` sidecar + graph mirror (raster->SVG->3MF provenance).
- **T5:** CLI (`--only`, `--profile`, `--no-clean`), A09 trace logging, regression suite `ops/tests/test_compile_3mf.py`.

**Verification**
- `python ops/tests/test_compile_3mf.py` -> 14/14 PASS.
- `python ops/scripts/compile_3mf.py` -> 3 released, 0 quarantined, 4 skipped (SKETCH).
- Independent reimport via trimesh -> all 3 `is_watertight==True`, `unit=millimeter` present; sidecars schema-conformant.

| comp_id | output | source | bbox_mm | volume_mm3 | watertight | result |
|---------|--------|--------|---------|------------|------------|--------|
| COMP-022 | svg_cat_3.3mf | raster | [500, 331.95, 4] | 173508 | true | release |
| COMP-028 | svg_logo_pee.3mf | vector | [500, 193.75, 4] | 284217 | true | release |
| COMP-143 | svg_full_name_ym_proskin.3mf | raster | [500, 198.16, 4] | 358518 | true | release |
| COMP-020/023/024/140 | (cat_1/4/5/2) | — | — | — | — | skip (SKETCH, not 3mf_eligible) |

**Open questions**
- SKETCH (line-art) -> 3D (tube/engrave) remains a future mode.
- Vector parsing is precise but fragile on complex logos; raster fallback is the reliable backstop (lesson logged).

---

## input/phone batch 2026-06-20: 102 iPhone screenshots/photos/memes -> SVG

**Status:** COMPLETED on `dev` (svg_cad/compile_3mf already merged into master+dev).

**Pipeline**
- **Format fix:** installed `pillow-heif`; converted 20 `.HEIC` -> `.jpg` (PIL/cv2 + the deconstruct extension filter can't read HEIC). WEBP read natively by PIL — kept.
- **Dedup:** 1 near-duplicate removed (perceptual hash) -> 102 survivors.
- **Rename:** `phone_001..phone_102`, ORIGINAL extension preserved (69 jpg / 30 png / 3 webp). `rename_photos.py` generalized with `--prefix` + ext preservation + natural sort.
- **De-chrome (A00):** 18 art-on-white screenshots cropped (UI bands trimmed, originals backed up to `input/phone/_precrop_originals/`), 83 clean, 1 skip.
- **Pipeline:** deconstruct (recursive) -> validate -> compile.

**Verification**
- 118 classified, 0 failures. Phone classes: 56 LOGO, 28 HUMAN_PHOTO, 11 ILLUSTRATION, 7 OBJECT_PHOTO.
- Compile: 122 objects -> **120 released, 2 quarantined**. The 2 are blurry phone photos (`edge_frac≈0.004`) correctly rejected by the suitability gate.
- Phone: **100/102 released** (58 STANDARD, 42 SKETCH).
- `validate.py --artifacts` -> 120/120 contract-conformant; no empty SVGs.

**Open questions**
- Phone STANDARD logos not yet meshed to 3MF (only requested SVG render).


