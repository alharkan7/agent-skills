## Tools

```
tools/
├── poster_check.py        ← CLI: measure / pack / fit-logos / preflight / polish / verify-final
├── render_preview.py      ← CLI: print-emulated PDF + thumbnail PNG
├── run_gates.py           ← orchestrator: preflight→style→asset→measure→polish → GATE_REPORT.json   (vendored, ARIS)
├── style_check.py         ← HARD style gate: token-only colors, no inline style, font/size scale     (vendored, ARIS)
├── asset_check.py         ← real-figure provenance gate (data-source + FIGURE_MANIFEST)               (vendored, ARIS)
├── extract_pdf_figures.py ← pull real figures from a paper PDF (contact-sheet / auto / crop)          (vendored, ARIS)
├── preprocess_figures.py  ← autocrop / resolution-check crops, keep the manifest honest               (vendored, ARIS)
└── _posterly/             ← internal modules (canvas parser, Playwright + settle, etc.)
```

The five `(vendored, ARIS)` tools are documented in `ENHANCED-GATES.md` (license/attribution in `NOTICE.md`); they reuse posterly's own `_posterly` engine. The **minimal fallback** uses only `poster_check.py` + `render_preview.py`:

- `poster_check.py`:
  - `measure` — **hard** geometry gate (column-bottom spread < 5 px, gap-to-footer in [30, 50] px, intercard gap in [12, 50] px inside each column, canvas-fill ∈ [95 %, 101 %] as a coarse diagnostic, poster bbox aligns to the page within ±2 px — the bbox-alignment check is the authoritative full-canvas requirement — poster *content* stays within the canvas box, catching a right/bottom strip sliced off when content overflows a mis-configured `.poster` grid, and content that escapes a card does not collide with a neighbouring card/banner/header beyond `--max-collision-px` (default 3 px)). On failure prints the shared passing band + per-column safe deltas and the edit-targets block; carries the consecutive-failure circuit breaker (exit 3 at the budget cap). `--with-polish` folds the polish measurement onto the same rendered page (advisory report; measure's exit code untouched) — one browser launch when a round wants both readings.
  - `pack` — **advisory** column-feasibility pre-check (run once before the loop): probes card figures at their Gate A band endpoints in-browser and reports columns unreachable by figure sizing alone.
  - `fit-logos` — **advisory, read-only** logo-zone packer (ported from ResearchStudio's paper2poster, reshaped for the human-in-the-loop idiom: it never edits the file). Measures the header logo zone (an explicit `--zone` selector overrides everything and never falls back; else `[data-logo-zone]`; else the *union* of `data-lf-h0`-stamped zones, `.logo-row`s, and standalone `.logo-slot`s, with nested candidates resolved stamp > row > slot and outer winning ties — rows/slots *inside* an applied `logo-pack` are never auto-discovered, so a re-run returns to the original zone, and a poster with one applied and one untouched zone keeps both), searches row partitions for the arrangement that maximises the ONE uniform height every institution mark shares, and prints the proposal — rows, per-mark widths, opaque-pixel fill, a paste-ready snippet — plus a note when that height would trip Gate E's QR match. **Use it critically**: the packer equalizes *bounding boxes* only; optical weight (a dense lockup beside a clean wordmark, §Gate E) is an authoring judgment it cannot make. Apply the snippet by hand only if it reads right in the preview, adapt it (e.g. swap to size classes or a width-normalized `logo-stack`), or ignore it and place the logos yourself — then re-run the gates either way. Most useful at ≥3 marks of mixed AR; for one or two logos the size classes are already the answer. **Re-run idempotency:** when you apply a proposal into a content-sized zone, also stamp the zone's pre-application height as `data-lf-h0="<px>"` (the CLI prints the exact stamp line) — an applied pack collapses the zone to its packed height, so an unstamped re-run measures only the shrunken strip and can only propose smaller; the advisor reads the stamp back (`max(stamp, live box)`, so a template-grown zone still wins) and warns when it finds an applied pack without one.
  - `preflight` — static HTML lint (LaTeX residue, math `<`, missing images, role validation, `.figure` blocks missing their one-line `.caption`).
  - `polish` — **soft** visual gate (figure sizing by AR, broken images, typography orphans, space-between fill, card trailing / mid-card voids, `<br>`-in-flex collapse, header logos: broken / oversized / QR mismatch / title squeeze). Warns by default; `--strict` to fail. Hard-fails if the poster has no `[data-measure-role]` markup at all (silent PASS would be a worse bug). Its measurement half also rides `measure --with-polish` (same rendered page, advisory there); this standalone run remains the loop's final soft gate.
  - `verify-final` — `pdfinfo`-based PDF sanity (page count, dimensions, file size).
- `render_preview.py` — Playwright print-emulated PDF + scaled PNG thumbnail.

All scripts read `@page { size: W H }` from the input HTML so the same code handles ICML 60×36 landscape, ICLR 24×36 portrait, CVPR A0, etc. without flags.

Every gate render also serves MathJax from the skill's **bundled copy** (`assets/mathjax/tex-svg.js`, MathJax 3.2.2 — the renderer intercepts the templates' CDN request), so math typesetting during measurement is deterministic and offline-safe; a hand-opened `poster.html` still loads from the CDN as before.
