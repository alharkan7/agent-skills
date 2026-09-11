# AI Agent Skills

This repository contains a collection of AI agent skills following the standard [agentskills.io](https://agentskills.io) specification. These skills can be loaded by compatible AI agents to extend their capabilities.

## Available Skills

*   **2d-motion-graphics**: Create new motion graphics animation HTML sequences for the Mograph Player application. Covers best practices for CSS animation timing, responsiveness, design aesthetics, specific motion patterns, and the Mograph export contract.
*   **3d-motion-graphics**: Create new 3D motion graphics animations using Three.js for the ThreeJS Player application. Covers best practices for Three.js scene setup, animation loops, lighting, composite video export rules, and manifest registration.
*   **svg-diagram**: Generates highly aesthetic, modern, soft-styled SVG diagrams natively without relying on Mermaid.
*   **posterly**: Build academic conference posters (ICML/NeurIPS/ICLR/CVPR) as a single HTML/CSS file, rendered to print-ready PDF via headless Chromium. A deterministic Python gate suite measures real browser geometry so columns align, content fits the canvas, and styling stays on-palette before printing. Upstream: [Chenruishuo/posterly](https://github.com/Chenruishuo/posterly) (AGPL-3.0).
*   **animated-chart**: Takes an input of a chart image and turns it into an animated chart via Chart.js, outputting an HTML file for preview.
*   **bibliometric-analysis**: End-to-end bibliometric analysis (science mapping) of a research field — collect scholarly metadata from OpenAlex, screen it into a coding sheet, compute structured indicators, generate an academic chart suite (trends, themes, keyword co-occurrence, co-citation, collaboration networks), and write insight-driven reports. Language-agnostic workflow with a runnable Python reference implementation.
*   **engineering-practice**: Agent software engineering behavior and architectural principles.
*   **interactive-textbook**: Creates interactive textbook React components from source text, featuring nested tooltips for prerequisites and interactive widgets for gears-level models.
*   **science-scrollytelling**: Turns a scientific research paper, dataset, or text document into a stunning, interactive "Scrollytelling" web application.

## Usage

[![skills.sh](https://skills.sh/b/alharkan7/skills)](https://skills.sh/alharkan7/skills)

Because this repository follows the open standard, you can install these skills directly into your agent environment using the open-source `skills` CLI:

```bash
npx skills add alharkan7/skills/2d-motion-graphics
npx skills add alharkan7/skills/3d-motion-graphics
npx skills add alharkan7/skills/svg-diagram
npx skills add alharkan7/skills/animated-chart
npx skills add alharkan7/skills/bibliometric-analysis
npx skills add alharkan7/skills/engineering-practice
npx skills add alharkan7/skills/interactive-textbook
npx skills add alharkan7/skills/science-scrollytelling
```

Agents that support the `agentskills` format can dynamically load and execute these skills when required to complete a task. Each skill folder contains a `SKILL.md` detailing exactly how the skill should be executed.
