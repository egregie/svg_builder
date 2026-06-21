# Текущее состояние проекта

> Машиночитаемый источник истины (версия / движок / цветовая модель / пороги гейтов):
> [`00_governance/pipeline_config.json`](file:///c:/svg_builder/00_governance/pipeline_config.json) (SSOT, svg_cad T0).
> Значения ниже — производные от него; не дублировать пороги вручную.

- **Версия спецификации**: `3.5` (лайн: TZ v3.0→3.1→3.2 + CR v3.3→3.4→3.5 + svg_cad T0–T3 + Stage 4 compile_3mf).
- **Активный движок**: детерминированный VTracer-пайплайн — `hifi_vectorize.vectorize_monochrome` (STANDARD) + `sketch_vectorize.vectorize_sketch` (SKETCH). StarVector исключён.
- **Цветовая модель**: монохром `#000000` на прозрачном фоне — каноничный финальный вывод. Zero Black Policy + `design-tokens.json` — только для легаси `--color`.
- **Релиз-гейты**: SKETCH SSIM ≥ 0.75 (+ render_black ≤ 0.5), STANDARD SSIM ≥ 0.93 (из SSOT). Suitability-гейт: исходники без рёбер/детали (`edge_frac<0.005 ∧ lap_var<60`) отбраковываются (размытые мемы).
- **Ветки**: всё слито в `master` и `dev` (ветки `svg_cad`, `compile_3mf` влиты и удалены). Активная работа — на `dev`.
- **Рабочий корпус**: 122 объекта в графе. `05_output_svg/`: **120 released SVG**, 2 в карантине (размытые фото). Ранее обработанные — в `06_archive/`.
  - последний батч `input/phone/` (iPhone-скрины/фото/мемы): 102 → **100 released** (58 STANDARD, 42 SKETCH), 2 отбраковано suitability-гейтом.
- **Контракт артефакта**: каждый релизный SVG — standalone + встроенный `<metadata id="svgcad">` (схема [`svg_artifact_v1`](file:///c:/svg_builder/00_governance/schemas/svg_artifact_v1.schema.json)); зеркало в knowledge graph.
- **Статус QA**: 120/120 конформны контракту (`python ops/scripts/validate.py --artifacts`); пустых/блобов нет.
- **Stage 4 (compile_3mf)**: `ops/scripts/compile_3mf.py` собирает печатные `.3mf` из `3mf_eligible`-артефактов — для каждого ДВА варианта `_cutout` (трафарет) + `_raised` (рельеф). Прогон по 10 логотипам (di_ko/des): 20/20 watertight в `07_output_3mf/`. Конфиг — секция `three_mf` SSOT (cutout/raised, 500мм, 4мм, лимит принтера 550×450×450). STANDARD-логотипы из phone-батча ещё НЕ мешились (по запросу).
- **Тесты**: `ops/tests/test_svg_cad.py` 17/17, `ops/tests/test_compile_3mf.py` 14/14.
- **Препроцессинг входа**: `ops/scripts/` — `dedup_photos.py`, `rename_photos.py` (`--prefix`, сохранение расширения), `autocrop.py` (A00 de-chrome). HEIC конвертируется через `pillow-heif` (PIL/cv2 его не читают).
- **Что сломано / ограничено**: см. [known_problems.md](file:///c:/svg_builder/00_PROJECT_STATE/known_problems.md)
