---
name: bibliometric-analysis
description: End-to-end bibliometric analysis (science mapping) of a research field — collect scholarly metadata from OpenAlex, screen it into a coding sheet, compute structured indicators, generate an academic chart suite (trends, themes, keyword co-occurrence, co-citation, collaboration networks), and write insight-driven reports. Use whenever the user wants to map a body of academic literature, run a quantitative or systematic literature review, analyze citations, keywords, journals, authors, or countries, build co-citation / keyword / collaboration networks, find research gaps, or says things like "bibliometric analysis", "science mapping", "lembar koding bibliometrika", or "what does the literature say about X, quantitatively".
---

# Bibliometric Analysis

Turn a research topic into a defensible map of its scholarly literature: a screened
corpus dataset, a structured metrics file, a full chart suite, and a written report
with research-gap implications.

The reference implementation (in `scripts/` of this directory) is Python, but the
workflow is **language-agnostic**: every stage is defined by its inputs, outputs, and
rules — implement each stage in whatever stack the user prefers (Python, R,
JavaScript/TypeScript, Julia, shell + jq, …). Treat `scripts/*.py` and `run_pipeline.sh`
as an *executable specification*, not a requirement.

## Ground rules

1. **Stages communicate only through files** — a coding-sheet CSV and an insights JSON.
   Keep the schemas below byte-compatible and any stage can be rewritten or replaced
   in another language without touching the others.
2. **One self-contained output directory per run**: `reports/<YYYYMMDD_HHMM>_<topic-slug>/`
   holding the coding sheet, insights JSON, and all charts. Never scatter run artifacts
   across shared folders.
3. **Fail fast**: run stages in order; if a stage errors, stop and report rather than
   continuing with partial data.
4. **Coding-sheet language**: column names and category labels below are the canonical
   contract (in Indonesian, inherited from the reference corpus — e.g. *lembar koding* =
   coding sheet). Chart titles/axes may be in the user's report language; do not rename
   the CSV columns without migrating every downstream stage.

## Stage 0 — Scope the study

Before any code, pin down and write into the run directory as `study_design.md`:

- **Topic and angle** (e.g. "digital activism", "ESG perception", "hoax detection").
- **Time window** and document filter (reference default: articles from 2010 onward,
  abstract required).
- **Geographic/contextual focus**, if any (reference: Indonesia).
- **Query set**: 5–10 search queries covering synonyms, adjacent framings, and — if the
  field publishes in one — the local language. Reference example:
  - `"digital activism" AND ("Indonesia" OR "Indonesian")`
  - `"hashtag activism" AND ("Indonesia" OR "Indonesian")`
  - `"aktivisme digital" AND "Indonesia"` (local-language variant)
- **Domain adaptation rules** to swap in (see checklist at the end): relevance signals,
  platform list, theme/theory keyword rules, stop-keywords.

## Stage 1 — Collect (OpenAlex API)

**Output**: `lembar_koding_bibliometrika.csv` — the canonical coding sheet.

### API contract

- Endpoint: `GET https://api.openalex.org/works`
- Parameters:
  - `search=<query>` (one request series per query in the query set)
  - `filter=from_publication_date:<YYYY>-01-01,type:article,has_abstract:true`
  - `per-page=100`, `page=1..N`
  - `select=id,doi,title,authorships,publication_year,primary_location,biblio,cited_by_count,keywords,concepts,language,abstract_inverted_index,referenced_works`
- **Politeness**: send a `User-Agent` identifying the project with a `mailto:` address
  (OpenAlex "polite pool") — the reference fetcher takes `--email` (or the
  `OPENALEX_EMAIL` env var via `run_pipeline.sh`) — and sleep ~0.25 s between
  paged requests.
- **Retry**: on HTTP 429 retry up to 4 times with exponential backoff
  (wait `2^attempt + 2` seconds). On other errors, abandon that page and move on.
- Stop paginating a query when a page returns fewer results than `per-page`.
- Caps (defaults; size to the field): 10 pages per query, 500 final rows (`MAX_ROWS`).

### Batch metadata resolution (used again in Stage 4)

To label referenced works (co-citation network, reference genealogy):
`GET https://api.openalex.org/works?filter=openalex:W1|W2|W3&select=id,title,authorships,publication_year`
(pipe-separated OR of OpenAlex work IDs, ≤50 per call). Label format: `LastName (Year)`.

### Record processing rules

- **Deduplicate** across queries by OpenAlex work ID.
- **Sort** by citation count descending, then publication year descending; keep the
  top `MAX_ROWS`.
- **Reconstruct abstracts** from `abstract_inverted_index`: it maps each word to its
  positions — flatten to `(position, word)` pairs, sort by position, join with spaces.
- **Authors**: `Last, First` format, first 4 authors, then `et al.`; `;`-separated.
- **Collaboration type** from authorships' institution country codes:
  1 author → `Tunggal`; >1 country → `Multi-negara`; 1 country → `Satu-negara`;
  no country data → `Multi-penulis (afiliasi tidak diketahui)`.
- **Citations per year** = `cited_by_count / max(current_year − publication_year, 1)`.
- **Platform studied** — keyword match on title (first match group per platform):
  `twitter|tweet|x.com` → Twitter/X; `facebook`; `instagram`; `youtube`; `tiktok`;
  `whatsapp|telegram|line` → WhatsApp/Telegram/Line; `reddit|discord` → Reddit/Discord.
  No match → `Tidak spesifik / multi-platform`.
- **Theme / theory inference** from the OpenAlex concept hierarchy. Note: OpenAlex is
  deprecating `concepts` in favor of `topics` (field → subfield → topic) — if
  `concepts` is absent, anchor inference on `topics` levels instead. Any equivalent
  leveled taxonomy works:
  - `Tema_Utama` = first level-2 concept; fallback first level-1.
  - `Subfield` = first level-1 concept.
  - `Teori_Kerangka` = first level-3 concept, else "unspecified".
  - `Metode_Penelitian` = up to 2 concepts whose names match method-ish keywords
    (analysis, method, model, algorithm, technique, approach, framework, survey,
    experiment, study, evaluation, review, mapping, mining, network, simulation).

### Canonical coding-sheet schema

Write UTF-8 with BOM so Excel opens it cleanly (Python calls this encoding
`utf-8-sig`; in R, `readr::write_excel_csv()`).

| Column | Content |
|---|---|
| `Kode_Dokumen` | Sequential ID `D001, D002, …` |
| `Judul` | Title |
| `Penulis` | `Last, First; …; et al.` |
| `Tahun_Terbit` | Publication year |
| `Nama_Jurnal_Prosiding` | Journal / proceedings name |
| `Volume_Halaman` | `vol(issue), first–last` |
| `DOI` | Bare DOI (no `https://doi.org/` prefix) |
| `Bahasa` | Language label (reference: Indonesia/Inggris) |
| `Basis_Data_Sumber` | Source database (OpenAlex) |
| `Afiliasi_Penulis_Pertama` | First author's institution |
| `Negara_Afiliasi` | First affiliation country code (ISO-2) |
| `Semua_Negara_Afiliasi` | All distinct country codes, `;`-joined |
| `Asal_Peneliti` | Researcher origin (country code, else unknown) |
| `Kolaborasi` | Collaboration type (taxonomy above) |
| `Total_Sitasi` | Citation count |
| `Cite_per_Year` | Citations per year |
| `Author_Keywords` | Author keywords, `;`-joined (top 6) |
| `Index_Keywords` | Index keywords from level-1/2 concepts |
| `Tema_Utama` | Main theme (inferred) |
| `Subfield` | Subfield (inferred) |
| `Teori_Kerangka` | Theory/framework (inferred) |
| `Metode_Penelitian` | Method (inferred) |
| `Platform_yang_Dikaji` | Platform studied (inferred) |
| `Kriteria_Inklusi` | `Dimasukkan` / `Dieksklusi` (set in Stage 2) |
| `Alasan_Eksklusi` | Exclusion reason (set in Stage 2) |
| `Referenced_Works` | Cited OpenAlex work IDs, `;`-joined |
| `Abstrak` | Reconstructed abstract |

## Stage 2 — Screen (automated inclusion/exclusion)

**Input/output**: the coding sheet — update `Kriteria_Inklusi` / `Alasan_Eksklusi`
in place (default every row to `Dimasukkan`).

Apply, in order:

1. **Duplicates**: normalize titles to lowercase alphanumerics only; second and later
   occurrences → exclude, reason `Duplikasi`.
2. **Abstract adequacy**: fewer than 30 words → exclude (incomplete records,
   editorials, non-research items).
3. **Topical relevance** (only when the study has a geographic/contextual focus):
   require signals of the focus context in title/abstract (reference used tokens like
   `jakarta`, `jokowi`, `kpk`). Also drop papers where the context is only a marginal
   data point — operational test: no context signal in the title AND the context
   country absent from author affiliations AND the abstract name-drops it alongside
   several other countries (cross-national survey with a one-line Indonesia result).

Print a screening summary: totals included/excluded and a breakdown by exclusion
reason. Keep excluded rows in the file (audit trail), never delete them.

## Stage 3 — Extract insights (JSON)

**Input**: only rows with `Kriteria_Inklusi == Dimasukkan`.
**Output**: `insights_data.json` — one key per indicator, each a ranked
`{label: count}` map or per-year structure. This file is the numeric backbone the
report quotes verbatim; every number in the report must be traceable to it.

Indicators (reference keys):

- `tren_publikasi` — articles per year.
- `distribusi_tema` / `distribusi_tema_detail` — theme counts (raw / after breaking
  generic buckets apart).
- `asal_peneliti`, `kolaborasi`, `top_institusi`, `top_jurnal`, `top_negara`.
- `top_keywords` — from author + index keywords: split on `;`/`,`, lowercase,
  collapse whitespace, drop tokens <3 or ≥50 chars, drop stop-keywords (domain-generic
  terms like *indonesia, social media, digital, study, analysis, based, network* —
  anything that would top every chart without informing), dedupe per article, count.
- `kolaborasi_negara` — for each multi-country article, count all sorted country pairs.
- `sitasi` — per year: `{total_articles, total_citations, avg_citations}`.
- `distribusi_teori`, `distribusi_teori_detail`, `evolusi_teori` (theory counts per
  year, keep theories with ≥5 articles).
- `teori_vs_metode` and `tema_vs_metode` — sparse `{"Theme | Method": count}` pairs.
- `dampak_sitasi_per_tema` / `_kolaborasi` / `_bahasa` / `_penerbit` — avg, n, total
  citations per group (require n ≥ 2).
- `distribusi_penerbit` — publisher tier by DOI prefix. Reference prefix map:
  `10.1080` Taylor & Francis, `10.3390` MDPI, `10.1177` SAGE, `10.1007` Springer,
  `10.1017` Cambridge UP, `10.1093` Oxford UP, `10.1016` Elsevier, `10.1002`/`10.1111`
  Wiley, `10.1186` BMC, `10.3389` Frontiers, `10.1145` ACM, `10.1109` IEEE,
  `10.2991` Atlantis Press (→ proceedings). Other `10.x` → other journal;
  no DOI → `Tanpa DOI`. Extend with the local publishers your field actually uses.

## Stage 4 — Visualize

**Input**: screened coding sheet (+ live OpenAlex metadata calls for co-citation
labels). **Output**: PNG charts (reference: 150 dpi, ~11–16 in wide) in the run
directory. Every chart states its n and thresholds in the title or caption.

### Chart catalog

| # | Output (reference name) | Chart | Content & parameters |
|---|---|---|---|
| 1 | `trend_publikasi` | bar + line | Articles per year; annotate bar values |
| 2 | `distribusi_tema` | horizontal bar | Top 12 themes |
| 3 | `distribusi_tema_detail` | horizontal bar | Themes after generic-bucket breakdown; color-code inferred sub-themes vs original |
| 4 | `tipe_kolaborasi` | horizontal bar | Collaboration-type counts |
| 5 | `top_institusi` | horizontal bar | Top 15 institutions by first-author affiliation |
| 6 | `top_jurnal` | horizontal bar | Top 15 journals |
| 7 | `top_negara` | vertical bar | Top 12 countries (map ISO codes to names) |
| 8 | `keyword_cooccurrence` | network | Keyword co-occurrence; keep keywords with freq ≥2, cap ~40 nodes, edge if co-occur ≥2, drop isolates; node size ∝ frequency, edge width ∝ weight, color by degree; label nodes with freq ≥3 |
| 9 | `kolaborasi_negara` | network | Countries as nodes, pair counts as weighted edges |
| 10 | `sitasi_per_tahun` | 2 panels | Avg citations/year (line + fill) over total citations (bars) + article count (line, secondary axis) |
| 11 | `evolusi_tema` | multi-line | Top 7 themes per year, full year index (zero-filled) |
| 12 | `jaringan_kositasi` | network | Co-citation of `Referenced_Works`; top ~35 most-cited refs, edge ≥2 co-citations; labels `Author (Year)` from batch metadata API |
| 13 | `top_penulis` | horizontal bar | Authors ranked by corpus-wide summed citations. Caveat: the schema truncates `Penulis` at 4 + `et al.`, so 5th+ authors are undercounted — state this limitation under the chart |
| 14 | `top_teori` | horizontal bar | Top ~14 theories; color-code inferred vs explicit |
| 15 | `teori_vs_metode` | heatmap | Theory × method counts (keep theories ≥5, methods ≥3) |
| 16 | `evolusi_teori` | stacked area | Top 8 theories over time |
| 17 | `genealogi_referensi` | timeline scatter | Top ~20 most-cited references at their publication year; bubble size ∝ corpus citations; skip entries with unresolved metadata |
| 18 | `dampak_sitasi_per_tema` | horizontal bar | Avg citations per theme, label `(n=…)` |
| 19 | `dampak_sitasi_kolaborasi` | vertical bar | Avg citations per collaboration type |
| 20 | `evolusi_platform` | multi-line | Platform-specific articles per year |
| 21 | `distribusi_penerbit` | pie + bar | Publisher-tier share + avg citations per tier |
| 22 | `tema_vs_metode` | heatmap | Theme × method counts (≥2 each side) |

### Visual style (academic, print-safe)

- Serif font family (STIX / Times / DejaVu Serif), base size 11, bold titles.
- No top/right spines; dashed light-gray grid behind data; white background.
- Muted palette, e.g. navy `#2B4C7E`, sage `#5B8C5A`, brick `#A45A52`,
  steel `#6B7AA1`, tan `#C49A6C`, warm gray `#7A6C5D` (warm tones for *inferred*
  categories, cool for *original* — legend explains the distinction).
- Always label values on bars; wrap long category labels onto 2–3 lines.
- Networks: force-directed layout with a fixed random seed (reproducibility),
  remove isolated nodes, white node outlines.

### Network construction recipe (any language)

Count pair co-occurrences with the sorted-pairs trick: for each article take its
deduplicated item set, generate all 2-combinations of the sorted set, increment pair
counters. Filter by frequency/co-occurrence thresholds, cap node count, lay out with
a force-directed algorithm (e.g. Fruchterman–Reingold / spring layout).

## Stage 5 — Report

**Inputs**: insights JSON + charts + (if provided) the user's research proposal.
**Outputs**: an analytic-memos document (`visualizations_insights.md`) and/or a
findings chapter. Write the report in the user's working language even though the
coding-sheet labels are Indonesian — quote labels as-is when citing the data.

Rules learned the hard way — follow them:

1. **Never let a generic category dominate.** If one bucket like "Digital activism
   (umum)" or "unspecified theory" tops a distribution, break it down with keyword
   rules over title/keywords/abstract before charting and reporting (the reference
   corpus resolved 93% of its generic bucket this way). Same for "local researchers" —
   resolve to institutions.
2. **One analytic memo per chart**: *Key insight* → interpretation → historical /
   contextual explanation (e.g. a 2019 publication spike tied to real-world protest
   waves). Numbers must come from the insights JSON, not eyeballed from charts.
3. **Separate diagnostic charts from report charts.** Citation-impact-by-collaboration,
   publisher distribution, platform evolution, and the theme×/theory×method matrices
   are exploratory; exclude them from formal reports unless they answer a stated
   research question.
4. **Align with the research paradigm** stated in the proposal (epistemology,
   methodological framing) — findings chapters must speak its language, at the
   qualification level the user is working at.
5. **End with research gaps**: sparse themes, missing platforms, absent regions or
   collaboration patterns are the deliverable — they justify the next study.

## Orchestration

Run order: **collect → screen → insights → visualize → report**, each stage reading
the previous stage's files from the shared run directory. Reference runner:
`run_pipeline.sh [keywords…]` — builds the timestamped run directory (under the
directory you invoke it from), chains the stages, stops on first failure. Re-running
a single stage against an existing run directory must work (all stages take the run
directory as their target).

## Choosing a stack

Any combination providing: an HTTP client, CSV + JSON I/O, a plotting library, and a
force-directed graph layout. Suggested equivalents per stage:

| Stage | Python (reference) | R | JS/TS | Shell |
|---|---|---|---|---|
| Collect | `urllib`/`requests` | `httr2` | `fetch` | `curl` + `jq` |
| Screen/Insights | `csv` + `collections` | `dplyr` | `d3-array`/`lodash` | `jq`, `mlr` |
| Charts | `matplotlib` | `ggplot2` | D3 / Observable Plot | — |
| Networks | `networkx` | `igraph`/`ggraph` | `d3-force`/Cytoscape.js | — |

Prefer the ecosystem the user's repo already uses; when unsure, default to the
reference Python stack so `scripts/` can be reused as-is (third-party deps are
listed in `scripts/requirements.txt`; fetch/screen/insights are stdlib-only).

## Domain adaptation checklist

When applying this to a field other than the reference (digital activism in
Indonesia), replace:

- [ ] Query set (synonyms + local-language variant)
- [ ] Relevance signals for the contextual focus (Stage 2, rule 3)
- [ ] Platform list (Stage 1 inference) — e.g. finance apps, health platforms, LLM tools
- [ ] Theme/theory keyword rules for generic-bucket breakdown (Stage 5, rule 1)
- [ ] Stop-keyword list (terms that are generic *within this field*)
- [ ] Country-code focus and publisher prefix map, if the field publishes elsewhere
- [ ] Time window start (2010 fits social-media topics; older fields need more)
