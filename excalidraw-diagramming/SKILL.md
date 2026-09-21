---
name: excalidraw-diagramming
description: Guidelines for creating, reading, or editing Excalidraw whiteboard diagrams (.excalidraw JSON files). Use for flowcharts, research-design sketches, and system diagrams.
---

# Excalidraw Diagramming

Use Excalidraw when the user names it, attaches a `.excalidraw` file, or wants an editable whiteboard-style diagram. Prefer Mermaid for text-embeddable flowcharts (`mermaid-diagramming`) and native SVG for polished static graphics (`svg-diagram`); `.excalidraw` files are standalone workspace artifacts and cannot be embedded in Markdown documents.

## Working with Excalidraw Files

An `.excalidraw` file is a standard JSON file containing an `elements` array. Since it is just JSON, you can read and modify it directly using standard file tools or simple scripts.

**Important Warning:** The JSON structure can be verbose. When modifying existing diagrams, be careful to preserve element `id`s, `seed`s, and `version`s to avoid breaking the diagram state. 

### Workflow

1. **Read:** Parse the `.excalidraw` JSON file. Review the `elements` array to understand the current shapes, their `id`s, `type`s, and coordinates (`x`, `y`).
2. **Edit:** Modify the JSON. You can write a short Python or Node.js script to safely mutate the JSON (e.g., adding new elements, moving elements, changing text) or use careful text replacement.
3. **Validate:** Ensure the resulting file is valid JSON before saving.

## Designing the diagram

- Plan on a grid: flow left-to-right (columns ≈ 300px apart) or top-down (rows ≈ 180px apart); give branch points room to fan out.
- Shape semantics (`type` field): `rectangle` = process or step, `ellipse` = start/end/trigger, `diamond` = decision or condition, `text` = free-floating annotation, `arrow` = directed relationship.
- Keep labels short (≤ 4 words where possible); use `\n` for two-line labels.
- Color semantically: use consistent `backgroundColor` and `strokeColor` per role (e.g. data `#a5d8ff`/`#1971c2`, decision `#ffec99`/`#e67700`, terminal `#d3f9d8`/`#2f9e44`).

## Editing rules

- **Updating elements:** You can reposition elements by changing `x` and `y`. For text elements, update the `text` and `originalText` fields.
- **Arrows and Connections:** Arrows reference the shapes they connect to via the `startBinding` / `endBinding` fields on the arrow itself. 
- **Deleting elements:** If you delete a shape, make sure to also delete any arrows that were bound to it, or remove their bindings to prevent corrupted references.
