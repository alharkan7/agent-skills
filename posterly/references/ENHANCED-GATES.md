## Enhanced gates & fix discipline (vendored from ARIS)

These tools and the fix discipline below are vendored from ARIS's `paper-poster-html` (MIT © 2026 wanshuiyin — see `NOTICE.md`). They layer on top of the Step 4 / Step 6 gates and reuse posterly's own `_posterly` engine. For a poster scaffolded from posterly's own templates they are the **default loop, not extras**: `run_gates.py` is the Step 4 driver and `style` is a hard gate every iteration (`asset` stays opt-in via `--manifest`). The bare `poster_check.py` core (preflight / measure / polish / verify-final) is the **fallback** only for a non-tokenized or imported template that can't pass `style` — it is *not* a license to skip `style` on a poster built from these templates.

### One-shot gate runner — `run_gates.py`

Instead of calling `measure` / `preflight` / `polish` by hand each iteration, run all gates in their load-bearing order and get the whole fix surface in one report:

```bash
# core gates (preflight + style + measure + polish); --tokens carries the
# Step 2.5 pack (design_tokens.json, always written at lock time):
python tools/run_gates.py poster.html --tokens design_tokens.json --report GATE_REPORT.json
# add --manifest to also run the real-figure asset gate (see below):
python tools/run_gates.py poster.html --tokens design_tokens.json --manifest FIGURE_MANIFEST.json --report GATE_REPORT.json
```

Order is fixed: `preflight → style → asset → measure → polish`. The cheap static gates (preflight/style/asset) run before the expensive renders (measure/polish), so a structural or style bug fails fast instead of burning a render. `GATE_REPORT.json` holds every gate's pass/fail + findings — one read tells you the whole fix surface. Child processes run with `sys.executable`, so it uses the same interpreter/venv as posterly. By default `run_gates.py` forwards `--style-disable 4,5` to the style gate (posterly's default — see **§Style HARD gate** below for what that drops and how to re-enable). Plain `poster_check.py measure` still works if you don't adopt the style/asset gates.

Without `--manifest`, the asset gate is **opt-in** — it is reported `NOT_RUN` and excluded from `overall` (real figures not verified), so a green `overall` means *the gates that ran* passed, not that figures were checked. (This is a posterly fix to the vendored orchestrator — see `NOTICE.md`; upstream silently counted the missing-manifest asset gate as a pass.)

### Style HARD gate — `style_check.py`

The Step 6 `polish` gate is *soft* (aesthetics). `style_check.py` is a **hard** gate for the design-system discipline the templates assume:

```bash
python tools/style_check.py poster.html --disable 4,5 --tokens design_tokens.json   # posterly default; the pack is always written at lock time (Step 2.5)
```

14 rules: colors only via `var(--…)` from the `:root` token block (no stray hex), no inline `style=`, no gradients, font-family against a whitelist, font-size only from the `--fs-*` scale, bounded token count, the `data-*` / inline-SVG contracts, (rule 13) every `block--modifier` variant class used in the markup must have a matching CSS rule, and (rule 14) every numeric utility class used (`w-65`, `mt-2`, `sr-46`) must have one too — an undefined width utility lets the figure render at natural size and balloon its column (three wave-2 posters hit exactly this) — a dropped rule leaves the class inert and the layout silently wrong (e.g. a `keybox--4` with no `.keybox.keybox--4` rule falls back to the 3-col base grid, orphaning a 4th tile into an empty second row). Pure static analysis plus a small Playwright render gate for computed-style rules, so it's cheap — run it right after the Step 3 scaffold and on every layout change.

**posterly default — rules 4 and 5 are disabled** (`run_gates.py` forwards `--style-disable 4,5`): rule 4 (≤2 non-neutral hue families) and rule 5 (no gradients) are *design-opinion* rules, so palette breadth and gradients are left to you. The other 12 — the *operational* discipline: token-only colors, no inline `style=`, the font/size scale, the data-attribute and variant-class contracts — stay enforced. A disabled rule still runs and shows in the report as `SKIPPED`; it just no longer drives pass/fail. Calling `style_check.py` directly enforces all 14 unless you pass `--disable 4,5`; re-enable everything with `--style-disable ''` on `run_gates.py`.

> **Note.** `style_check` assumes a *tokenized* template — a `/* ===== DESIGN TOKENS ===== */ … /* ===== END DESIGN TOKENS ===== */` block, colors via `var(--…)`, sizes via `--fs-*`, no inline `style=` / gradients. posterly's `*_neutral.html` templates **are** tokenized (vendored from ARIS — see `NOTICE.md`), so a poster scaffolded from them passes `style` out of the box. A hand-written or imported non-tokenized template will FAIL `style` until you tokenize it; the other gates (`preflight` / `measure` / `polish`) don't require tokenization.

> **Reconciling with the older layout examples.** Some examples in *Step 6 / Visual polish gates* below set figure widths with inline `style="width: …"`. `style_check` (rule 2) forbids inline `style=` **except** `style="width: NN%"` on an `img[data-source="paper"]` and anything inside a `data-color-exempt="logo"` element. So if you adopt `style_check`, express figure widths via the `w-95` / `w-100` utility classes (see `templates/COMPONENTS.md`) or a tokenized component rule rather than taking the bare inline-`style=` snippets literally — and size logos by their size class or a tokenized variant (Gate E), never a bare inline height on the slot.

### Real-figure provenance gate (optional) — `asset_check.py` + figure tools

Step 1–2 sets a ≥2× resolution *target*; this gate enforces a hard **1.5× floor** (a 2× source clears it comfortably) for the workflow where you want a guarantee that every paper figure is genuinely from the paper (not AI-fabricated, not a tiny decorative thumbnail). **Needs the `figures` extra**: `pip install -e ".[figures]"` (PyMuPDF + Pillow).

1. `python tools/extract_pdf_figures.py paper.pdf --out fig_work/ contact-sheet` → a labelled page grid to read crop bboxes off; then the `auto` (candidate regions) and/or `crop` subcommands at 300–450 DPI (the top-level `--out` goes **before** the subcommand). **A human confirms crop choices** (🚦).
2. `python tools/preprocess_figures.py fig_work/fig.png --autocrop --manifest FIGURE_MANIFEST.json` → trims white margins, checks resolution, and (with `--manifest`) re-syncs each crop's `natural_px` / `sha256` so the manifest stays honest. Without `--manifest` it autocrops but leaves stale hashes that `asset_check` will then reject.
3. Embed as `<img data-source="paper" data-asset-id="fig1">`; record each in `FIGURE_MANIFEST.json` (page, bbox, dpi, sha256, natural_px, `from_paper: true`).
4. `python tools/asset_check.py poster.html --manifest FIGURE_MANIFEST.json` → fails unless ≥2 paper figures resolve to manifest entries with matching sha256 and a rendered area **inside a band** — per-figure `≥1.5%` of the poster (floor) to `≤13%` of the body (cap), total `12–28%` of the body (warn above 24%; target ~14–22%; `--hero` raises the per-figure cap to 42% for a hero centerpiece). So a too-small figure *and* an oversized one both hard-fail — worth knowing if you enlarge figures for a Light-density poster. Theory-only papers waive the total-area rule at a human checkpoint (`--waive-total-area`), never silently.

If you don't adopt this contract, skip it — the other gates don't require `data-source` / manifest markup.

### Fix discipline — softened closed-set fix vocabulary

The failure mode of any "render → review → fix → re-render" loop is the **patch loop**: the agent fixes one nit by adding an inline style / a new hex / a one-off SVG, the next gate flags *that*, and it never converges. The discipline below keeps the Step 6 loop bounded. It is the **softened** form of ARIS's closed set — half-closed, with a smooth escape hatch — suited to posterly's human-in-the-loop use:

- **Prefer the named knobs.** Every fix inside the loop should be one of the 7 operations catalogued in `templates/COMPONENTS.md` (edit a `:root` token; swap/add/remove a catalogued component; rebalance paper-sourced content; reselect template/canvas; edit a component's token-only CSS; toggle a predefined variant; fix an asset). These are *named, reusable* knobs, not one-off hacks.
- **No one-off hacks.** No new inline `style=`, no new hex anywhere (colors come from tokens), no bespoke decorative SVG, no single-element font-size override — `style_check.py` enforces these as hard rules.
- **Escape hatch (the softening).** If a fix genuinely needs something outside the catalog — a new token, variant, or component — the agent may **propose** it explicitly, flagged as a *system extension* for your review, rather than being hard-blocked. On approval, add it to `COMPONENTS.md` / the token block and re-run from Step 3 so it passes `style` from a clean state. Don't splice a new element into a mid-loop poster silently.
- **Round caps are a guide, not a wall.** Default: ≤3 issues per round, and after ~3 rounds without reaching your visual bar, stop patching and escalate (reselect template/content, or a human call) rather than endless cosmetic micro-tuning. Adjust the caps deliberately — you're in the loop.

### Cross-model final review (strengthens Step 6.5)

Step 6.5 becomes a true **final gate** when run after `run_gates.py` is all-green and polish warnings are zero-or-waived: open a **fresh, cross-model** thread (a different model family than drafted the poster — e.g. Codex `gpt-5.6-sol`, `xhigh`) on the *final artifacts only* — `poster.html`, the rendered PDF/PNG, the paper source, and `GATE_REPORT.json` — passed as **paths, no executor framing**. It re-checks fidelity/overclaims on the *polished* text (polish introduces new claims), residue (`\ref{`, `TODO`, raw `<` in math, missing images, remote URLs), visual rhetoric (headline numbers prominent, banner readable at 2 m), copy voice (AI-flavor clusters per `templates/WRITING.md`, respecting its genre carve-out), design coherence (the sheet delivers its own `DESIGN DIRECTION` block — concept, single hero moment, component-native figure mounts, poster-voiced microcopy and earned emphasis; Step 6.5 item 4's restraint applies), and gate-log coherence. The reviewer *recommends*; it does not edit. Any fix loops back through Step 4/6 — never straight to re-review.
