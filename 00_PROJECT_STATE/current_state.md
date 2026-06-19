# Текущее состояние проекта

> Машиночитаемый источник истины (версия / движок / цветовая модель / пороги гейтов):
> [`00_governance/pipeline_config.json`](file:///c:/svg_builder/00_governance/pipeline_config.json) (SSOT, svg_cad T0).
> Значения ниже — производные от него; не дублировать пороги вручную.

- **Версия спецификации**: `3.5` (лайн: TZ v3.0→3.1→3.2 + CR v3.3→3.4→3.5). Прежнее `TZ_v2.9` в этом файле было устаревшим.
- **Активный движок**: детерминированный VTracer-пайплайн — `hifi_vectorize.vectorize_monochrome` (STANDARD) + `sketch_vectorize.vectorize_sketch` (SKETCH). StarVector исключён из критического пути (галлюцинации); вопрос «8B/1B» неактуален.
- **Цветовая модель**: монохром `#000000` на прозрачном фоне — каноничный финальный вывод (решение владельца 2026-06-19). Zero Black Policy + `design-tokens.json` действуют только для легаси-пути `--color`.
- **Последний релиз-гейт**: SKETCH SSIM ≥ 0.75 (+ render_black ≤ 0.5), STANDARD SSIM ≥ 0.93 — из SSOT.
- **Текущая ветка**: `svg_cad` (закрытие блокеров T0–T3 перед `compile_3mf.py`); не влита в `master`.
- **Рабочий корпус**: 7 объектов в `05_output_svg/` (cat_1–5, logo_pee, full-name). Ранее обработанные 66 — в `06_archive/`.
- **Контракт артефакта**: каждый релизный SVG — standalone + встроенный `<metadata id="svgcad">` (схема [`svg_artifact_v1`](file:///c:/svg_builder/00_governance/schemas/svg_artifact_v1.schema.json)); зеркалится в knowledge graph.
- **Статус QA**: 7/7 прошли релиз-гейт; 7/7 конформны контракту артефакта (`python ops/scripts/validate.py --artifacts`).
- **Stage 4 (compile_3mf)**: ветка `compile_3mf` (от `svg_cad`, не влита). `ops/scripts/compile_3mf.py` собирает печатные `.3mf` из `3mf_eligible`-артефактов. Прогон: 3/3 eligible (cat_3, logo_pee, full_name) → watertight-меши в `07_output_3mf/` (мм, `unit="millimeter"`), 4 SKETCH пропущены. Конфиг в SSOT секция `three_mf` (cutout, 500мм, 4мм). Тесты `ops/tests/test_compile_3mf.py` 14/14.
- **Что сломано / ограничено**: см. [known_problems.md](file:///c:/svg_builder/00_PROJECT_STATE/known_problems.md)
