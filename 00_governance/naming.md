# Стандарты именования файлов проекта

1. **Паспорта объектов**: `04_passports/COMP-NNN.md` (где NNN — от 3 до 6 цифр).
2. **База знаний / Граф**: `03_knowledge_graph/COMP-NNN.json`.
3. **Результаты деконструкции**: `02_processing/{source_base}_raw.json`.
4. **Оригинальные растры**: `01_input_raster/{category}/{source_filename}`.
5. **Выходные SVG**:
   - Финальный релиз: `05_output_svg/svg_{source_base}.svg` (с суффиксом коллизии `_NN` при необходимости, например `svg_cat_2_01.svg`).
   - Буфер сборки: `05_output_svg/staging/{stem}_compiled.svg`.
   - Карантин: `05_output_svg/quarantine/{output_filename}`.
6. **Архивные копии**: `06_archive/{original_folder_name}_arh/` (например, `06_archive/04_passports_arh/COMP-001.md`).
