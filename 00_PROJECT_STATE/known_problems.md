# Известные проблемы и ограничения

- `[CLOSED]` — Пустые/залитые сплошным фоном SVG (решено добавлением фильтрации фоновых путей по токенам).
- `[CLOSED]` — viewBox-мисматч в COMP-001 (решено корректным масштабированием и трансляцией координат в compile_svg.py).
- `[CLOSED]` — CPU-only torch при работе с INT4 моделями.
- `[OPEN]` — Падение StarVector на Windows при отсутствии библиотеки `fairscale` (R-01). StarVector исключён из критического пути (детерминированный VTracer-пайплайн), поэтому в активном рендере не воспроизводится.
- `[MITIGATED]` — Слишком агрессивная фильтрация при малом числе foreground-paths (R-03). svg_cad T3: в `hifi_vectorize.vectorize_monochrome` введён инвариант — single-linkage merge не может поглотить ВСЕ кластеры (сохраняется самый дальний от фон-seed → ≥1 foreground-путь); пустой foreground (`n_paths==0`) больше не отдаётся тихо как «успех», а помечается `invariant_violation` и уходит в quarantine с диагностикой. Регрессионный кейс: `ops/tests/test_svg_cad.py` (градиент). Полный геометрический валидатор — вне области (ТЗ `compile_3mf.py`).
- `[CLOSED]` — Дрейф версии/движка/цветовой модели (E-4/E-5). svg_cad T0: единый SSOT `00_governance/pipeline_config.json`; код читает пороги оттуда.
- `[CLOSED]` — Отсутствие контракта выходного SVG (E-3 / ND-04). svg_cad T1: схема `svg_artifact_v1` + встроенные метаданные + аудит `validate.py --artifacts`.
- `[CLOSED]` — Смешение визуального и топологического качества (E-1). svg_cad T2 развёл оси + `3mf_eligible`; compile_3mf T3 добавил полный манифолд-валидатор (watertight/winding/volume/габариты принтера) перед экспортом 3MF.
- `[CLOSED]` — px→мм не определён (R-06). compile_3mf T0: `px_to_mm = target_long_side_mm / max(viewBoxW,viewBoxH)` в SSOT (`three_mf`), иерархия CLI > COMP-override > config.
- `[MITIGATED]` — Векторный парсинг SVG даёт extrusion-hostile геометрию на сложных лого (валидные по `is_valid`, но `extrude_polygon` оставляет открытые рёбра при многих дырах). compile_3mf T1: vector-first с авто-fallback на растровый контур (cv2 RETR_CCOMP); полигон-с-дырами собирается как exterior-solid минус hole-призмы (boolean). Урок: для меша надёжнее простые замкнутые контуры, чем точные, но «грязные» векторы.
