---
name: mermaid-diagramming
description: Create or edit Mermaid flowcharts.
---

# Mermaid Diagramming

Mermaid is an excellent diagram format for Markdown: use it for diagrams embedded in Markdown documents and quick conceptual flowcharts. Switch to SVG (`svg-diagram`) only when the deliverable needs pixel-level polish or a layout Mermaid cannot express, and to Excalidraw (`excalidraw-diagramming`) only when the user wants an editable whiteboard-style diagram.

## Authoring rules

- Prefer `flowchart TD` or `flowchart LR` over the legacy `graph` spelling.
- Use short ASCII node IDs such as `A`, `claim_db`, or `review_1`.
- **Every human-readable node label MUST be double-quoted inside its shape delimiters. Never emit `A[Label]` or `B{Decision}`.** Write `A["Label"]`, `B{"Decision"}`, and `C(["Terminal label"])`.
- Parentheses, colons, percentages, ampersands, slashes, commas, periods, hyphens, and non-ASCII characters belong only inside those quoted labels.
- Keep syntax outside labels ASCII. Unicode is fine inside quoted labels.
- Use one statement per line. Semicolons are unnecessary.
- Prefer several concise nodes over one node containing a paragraph.

## Styling Best Practices

- Produce clean, informative Mermaid diagrams with moderate styling that improves readability.
- Use Mermaid-native styling where supported: `classDef`, `class`, `style`, `linkStyle`, and clear subgraph/section titles.
- Prefer restrained emphasis: highlight only key nodes/steps, not every element.
- Keep high contrast and legible labels; avoid excessive decoration.
- **HTML Usage:** Use simple HTML tags in labels/text ONLY when safely supported by the chosen diagram type (e.g., most flowcharts). 
  - For strict-syntax diagram types (such as `gantt`, `journey`, `requirementDiagram`, `timeline`, and `pie`), keep labels **plain text and avoid HTML tags entirely**.
  - **Never** use script/style tags, inline event handlers, iframes, or external resources.

## Specific Diagram Type Rules

- **Requirement Diagram (`requirementDiagram`):** The `verifymethod` field MUST be one of: `analysis`, `demonstration`, `inspection`, or `test`. Do NOT use any other value for `verifymethod`.

## Validation and Output

1. Be extremely careful with syntax, as broken Mermaid diagrams will fail to render in standard Markdown previewers. Adhere strictly to the double-quoting rule above to avoid the vast majority of parsing errors.
2. When embedding in Markdown, wrap the raw source in exactly one ```mermaid code fence. 
3. For a standalone `.mmd` or `.mermaid` file, write the raw source without fences.
