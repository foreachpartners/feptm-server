# Просмотр диаграмм моделей данных в VSCode

В этой директории находятся диаграммы моделей данных проекта в различных форматах. Ниже приведены инструкции по их просмотру в VSCode.

## Доступные форматы

1. **Mermaid** (`.mmd`) - простой в использовании формат диаграмм
2. **PlantUML** (`.plantuml`) - мощный и гибкий инструмент для UML-диаграмм
3. **GraphViz/DOT** (`.dot`) - язык описания графов для сложных взаимосвязей

## Просмотр диаграмм в VSCode

### Для Mermaid-диаграмм (data_model.mmd)

1. Установите расширение:
   ```
   code --install-extension bierner.markdown-mermaid
   ```
   или найдите "Markdown Preview Mermaid Support" в маркетплейсе VS Code

2. Затем можно просматривать файлы `.mmd` непосредственно, или интегрированные в Markdown файлы с использованием стандартного просмотрщика Markdown (Ctrl+Shift+V или кнопка в верхнем правом углу редактора)

### Для PlantUML-диаграмм (data_model.plantuml)

1. Установите расширение:
   ```
   code --install-extension jebbs.plantuml
   ```
   или найдите "PlantUML" в маркетплейсе VS Code

2. Установите зависимости:
   - Java (требуется для PlantUML)
   - GraphViz (необходим для рендеринга диаграмм)

3. Откройте файл `.plantuml` и нажмите Alt+D для предварительного просмотра, или используйте правый клик и выберите "Preview Current Diagram"

### Для GraphViz/DOT-диаграмм (data_model.dot)

1. Установите расширение:
   ```
   code --install-extension joaompinto.vscode-graphviz
   ```
   или найдите "Graphviz Preview" в маркетплейсе VS Code

2. Откройте файл `.dot` и нажмите Ctrl+Shift+V для предварительного просмотра или используйте правый клик и выберите "Show Graphviz Preview"

## Экспорт диаграмм в графические форматы

### Mermaid

```bash
# Установка CLI для Mermaid
npm install -g @mermaid-js/mermaid-cli

# Экспорт в PNG
mmdc -i docs/data_model.mmd -o docs/data_model_mermaid.png

# Экспорт в SVG
mmdc -i docs/data_model.mmd -o docs/data_model_mermaid.svg

# Экспорт в PDF
mmdc -i docs/data_model.mmd -o docs/data_model_mermaid.pdf -C
```

### PlantUML

```bash
# Требуется Java и PlantUML JAR
# Скачайте PlantUML JAR с http://plantuml.com/download

# Экспорт в PNG
java -jar plantuml.jar docs/data_model.plantuml

# Экспорт в SVG
java -jar plantuml.jar -tsvg docs/data_model.plantuml

# Экспорт в PDF
java -jar plantuml.jar -tpdf docs/data_model.plantuml
```

### GraphViz/DOT

```bash
# Установка GraphViz
# Linux: sudo apt-get install graphviz
# macOS: brew install graphviz
# Windows: скачайте с https://graphviz.org/download/

# Экспорт в PNG
dot -Tpng -o docs/data_model_dot.png docs/data_model.dot

# Экспорт в SVG
dot -Tsvg -o docs/data_model_dot.svg docs/data_model.dot

# Экспорт в PDF
dot -Tpdf -o docs/data_model_dot.pdf docs/data_model.dot
```

## Онлайн-редакторы

Также можно использовать онлайн-редакторы для визуализации и редактирования диаграмм:

- **Mermaid Live Editor**: https://mermaid.live/
- **PlantUML Online Server**: http://www.plantuml.com/plantuml/uml/
- **GraphvizOnline**: https://dreampuf.github.io/GraphvizOnline/

## Описание моделей данных

Подробное описание моделей данных и их взаимосвязей можно найти в файлах:
- `data_model_diagram.md` (Mermaid)
- `data_model_plantuml.md` (PlantUML)
- `data_model_graphviz.md` (GraphViz/DOT) 