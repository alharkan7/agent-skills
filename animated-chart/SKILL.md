---
name: animated-chart
description: Takes an input of a chart image and turns it into an animated chart via Chart.js, outputting an HTML file for preview.
---

# Animated Chart.js Skill

This skill provides instructions for transforming a static chart image into an interactive, animated chart using the Chart.js library within a standalone HTML file.

## 1. Image Analysis
*   Carefully analyze the provided chart image.
*   Identify the chart type (e.g., line, bar, pie, doughnut, radar).
*   Extract the data points, axes labels, and legends. Estimate values as accurately as possible if exact numbers are not present.
*   Extract the color palette used in the image (line colors, fill colors, background colors).

## 2. HTML and Chart.js Setup
*   Create a standalone HTML file.
*   Include the Chart.js library via CDN (e.g., `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>`).
*   Set up a `<canvas>` element for the chart with appropriate dimensions.
*   Add basic CSS to ensure the chart is displayed correctly and beautifully (centered, proper padding, matching the image's background if any).

## 3. Design & Aesthetics (Academic / Editorial Style)
NEVER copy default Excel or generic bright styles (e.g., pure green or pure orange on plain layouts) unless explicitly instructed. ALWAYS elevate the chart to an Academic or "New York Times" editorial style:
*   **Typography**: Use a professional serif font (e.g., `Georgia, serif`) for chart titles to give an editorial feel. Use clean sans-serif (e.g., `'Helvetica Neue', Arial`) for axes, tooltips, and legends.
*   **Color Palette**: Use muted, professional colors. E.g., deep editorial red (`#b22222`), navy blue (`#1f4e79`), and muted greys for historical or secondary data. Consider using dashed lines for older data to distinguish it from the current/primary dataset.
*   **Layout & Axes**:
    *   Move the Y-axis to the `right` side (common in professional journalism).
    *   Remove the solid Y-axis border (`border: { display: false }`).
    *   Keep horizontal grid lines very faint (`#ededed`) and remove vertical grid lines.
    *   Give the X-axis a strong, solid baseline (`border: { color: '#111', width: 1.5 }`).
*   **Tooltips & Legends**: Align legends to the top-left (`align: 'start'`) using `usePointStyle: true`. Style tooltips to be clean with a white/light background and dark text, adding a subtle border.

## 4. Chart Configuration & Animation
*   Initialize the Chart.js instance with the extracted data, strictly applying the **Design & Aesthetics** rules above.
*   **Line & Area Charts (Crucial Animation Rule)**: 
    *   To achieve a perfectly smooth left-to-right reveal (avoiding a staggered or blocky progressive draw), use a custom clipping plugin and disable default animations.
    *   Implement a `beforeDatasetsDraw` hook that clips the `chartArea` width based on a time-based easing function (e.g. `easeOutQuart`), then calls `requestAnimationFrame(() => chart.update('none'))`.
    *   Restore the context in `afterDatasetsDraw`.
    *   Set `options.animation = false` to prevent native animations from conflicting.
    *   For area charts, use `fill: true` and a smooth curve (`tension: 0.4`) with a semi-transparent background color matching the border line.
*   **Bar Charts**:
    *   Use the native Chart.js animation which works perfectly for a bottom-up growth effect.
    *   Configure `options.animation: { duration: 2000, easing: 'easeOutQuart' }`.
    *   Add a subtle `borderRadius: 2` or `3` to the bars to soften the edges.
*   **Doughnut & Pie Charts**:
    *   Only use rotational animations (`animateRotate: true`) and explicitly disable scaling animations (`animateScale: false`) so the chart doesn't awkwardly inflate from the center.
    *   Ensure legends for circular charts are placed elegantly (e.g., `position: 'right'` or `position: 'bottom'`).
*   **Scatter & Bubble Charts**:
    *   Use default animations (points expand and fade in).
    *   Use semi-transparent background colors (e.g., `rgba(..., 0.6)`) to ensure overlapping points remain visible.
*   **Radar Charts**:
    *   To make the chart "take shape", disable native animations and implement a custom angular wipe plugin.
    *   In the `beforeDatasetsDraw` hook, use `ctx.arc(centerX, centerY, radius, -Math.PI / 2, sweepAngle)` to progressively clip the radar web clockwise over time.
    *   Ensure the radial scale has a transparent backdrop for ticks to maintain a clean look (`scales: { r: { ticks: { backdropColor: 'transparent' } } }`).
*   **Bubble Charts**:
    *   To make each bubble strictly grow in place independently, disable global animations (`animation: false`) to stop axes and groups from moving.
    *   Implement a custom `bubbleRevealPlugin` that loops through the dataset metadata during `beforeDatasetsDraw`, calculates `point.options.radius = targetRadius * progress`, and updates the chart.
*   **Stacked & Mixed Charts**:
    *   For stacked bars, apply `stacked: true` to both `x` and `y` scale configurations.
    *   For mixed charts (e.g., Bar with an overlaid Line), use the dataset-specific line wipe plugin on the line dataset, and leave the bar dataset to animate natively.
*   **Crucial Lifecycle Rule for Tabs/Hidden Containers**: 
    *   If a chart is inside a hidden container (e.g., `display: none` in a tabbed UI), do **not** initialize it on page load. 
    *   Initializing a Chart.js canvas while hidden forces it to a 0x0 size. When later displayed, it animates the *resize* from the top-left corner instead of rendering the data animation.
    *   **Solution**: Lazily instantiate the chart *only* after its container is set to `display: block`.

## 5. Output
*   The final output should be a complete HTML file that can be opened in a browser to view the animated chart.
