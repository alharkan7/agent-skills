# AI Agent Skills

This repository contains a collection of AI agent skills following the standard [agentskills.io](https://agentskills.io) specification. These skills can be loaded by compatible AI agents to extend their capabilities.

## Available Skills

*   **2d-motion-graphics**: Create new motion graphics animation HTML sequences for the Mograph Player application. Covers best practices for CSS animation timing, responsiveness, design aesthetics, specific motion patterns, and the Mograph export contract.
*   **3d-motion-graphics**: Create new 3D motion graphics animations using Three.js for the ThreeJS Player application. Covers best practices for Three.js scene setup, animation loops, lighting, composite video export rules, and manifest registration.
*   **svg-diagram**: Generates highly aesthetic, modern, soft-styled SVG diagrams natively without relying on Mermaid.
*   **posterly**: Build academic conference posters (ICML/NeurIPS/ICLR/CVPR) as a single HTML/CSS file, rendered to print-ready PDF via headless Chromium. A deterministic Python gate suite measures real browser geometry so columns align, content fits the canvas, and styling stays on-palette before printing. Upstream: [Chenruishuo/posterly](https://github.com/Chenruishuo/posterly) (AGPL-3.0).

## Usage

[![skills.sh](https://skills.sh/b/alharkan7/skills)](https://skills.sh/alharkan7/skills)

Because this repository follows the open standard, you can install these skills directly into your agent environment using the open-source `skills` CLI:

```bash
npx skills add alharkan7/skills/2d-motion-graphics
npx skills add alharkan7/skills/3d-motion-graphics
npx skills add alharkan7/skills/svg-diagram
```

Agents that support the `agentskills` format can dynamically load and execute these skills when required to complete a task. Each skill folder contains a `SKILL.md` detailing exactly how the skill should be executed.
