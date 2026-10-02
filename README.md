# AI Agent Skills

This public repository contains AI agent skills in the [agentskills.io](https://agentskills.io) `SKILL.md` format. Compatible agents can load them to extend their capabilities. Check each skill's license before reuse; included third-party packages may have their own terms.

## Available Skills

* **2d-motion-graphics**: Create motion graphics HTML sequences with CSS or Web Animations API, covering timing, responsiveness, and motion patterns.
* **3d-motion-graphics**: Create Three.js motion graphics with guidance for scenes, animation, lighting, and video export.
* **svg-diagram**: Generates highly aesthetic, modern, soft-styled SVG diagrams natively without relying on Mermaid.
* **posterly**: Build academic conference posters (ICML/NeurIPS/ICLR/CVPR) as a single HTML/CSS file, rendered to print-ready PDF via headless Chromium. A deterministic Python gate suite measures real browser geometry so columns align, content fits the canvas, and styling stays on-palette before printing. Upstream: [Chenruishuo/posterly](https://github.com/Chenruishuo/posterly) (AGPL-3.0).
* **animated-chart**: Takes an input of a chart image and turns it into an animated chart via Chart.js, outputting an HTML file for preview.
* **bibliometric-analysis**: End-to-end bibliometric analysis (science mapping) of a research field — collect scholarly metadata from OpenAlex, screen it into a coding sheet, compute structured indicators, generate an academic chart suite (trends, themes, keyword co-occurrence, co-citation, collaboration networks), and write insight-driven reports. Language-agnostic workflow with a runnable Python reference implementation.
* **engineering-practice**: Agent software engineering behavior and architectural principles.
* **excalidraw-diagramming**: Create, read, and edit Excalidraw diagrams for flowcharts, research sketches, and system diagrams.
* **interactive-textbook**: Creates interactive textbook React components from source text, featuring nested tooltips for prerequisites and interactive widgets for gears-level models.
* **mermaid-diagramming**: Create and edit Mermaid flowcharts for Markdown documents.
* **science-scrollytelling**: Turns a scientific research paper, dataset, or text document into a stunning, interactive "Scrollytelling" web application.

## More Skills in Beeblio

I also develop skills in the open-source [Beeblio repository](https://github.com/alharkan7/beeblio-oss/tree/main/agent/skills). Its collection includes research, document, presentation, spreadsheet, and visualization workflows. Some skills appear in both repositories; the collections overlap and can complement each other. Browse the [Beeblio source](https://github.com/alharkan7/beeblio-oss) alongside this [public skills repository](https://github.com/alharkan7/skills).

## Usage

[![skills.sh](https://skills.sh/b/alharkan7/skills)](https://skills.sh/alharkan7/skills)

Install a top-level skill from this repository by replacing `{skill-path}` with its folder name from the list above:

```bash
npx skills add alharkan7/skills/{skill-name}
```

Install an individual Beeblio skill that has `SKILL.md` frontmatter into your current project's `.agents/skills/` directory by replacing `{skill-name}` with its filename (without `.md`):

```bash
mkdir -p .agents/skills/{skill-name} && curl -fsSL https://raw.githubusercontent.com/alharkan7/beeblio-oss/main/agent/skills/{skill-name}.md -o .agents/skills/{skill-name}/SKILL.md
```

Beeblio's `beeblio-docx`, `beeblio-pptx`, and `beeblio-xlsx` guides are app-specific Markdown files without skill frontmatter.

Each top-level skill in this repository contains a `SKILL.md` with its instructions.
