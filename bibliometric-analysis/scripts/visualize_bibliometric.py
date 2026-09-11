#!/usr/bin/env python3
"""
visualize_bibliometric.py
--------------------------
Generate bibliometric visualizations from lembar_koding_bibliometrika.csv

Outputs (saved to ../visualizations/):
  1.  trend_publikasi.png          — Annual publication trend
  2.  distribusi_tema.png          — Theme/subfield distribution (horizontal bar)
  2b. distribusi_tema_detail.png   — Detailed theme distribution ("umum" broken down)
  3.  asal_peneliti.png            — Local vs International researcher pie
  3b. top_institusi.png            — Top 15 institutions by article count
  4.  top_jurnal.png               — Top 15 journals by article count
  5.  top_negara.png               — Top countries by article count
  6.  keyword_cooccurrence.png     — Keyword co-occurrence network (main output)
  7.  kolaborasi_negara.png        — Country collaboration network
  8.  sitasi_per_tahun.png         — Average citations per year (line + scatter)
  9.  evolusi_tema.png             — Theme evolution (with reclassified sub-themes)
  10. jaringan_kositasi.png        — Co-citation network
  11. top_penulis.png              — Top authors by citation count
  12. top_teori.png                — Theories/frameworks (with inferred sub-categories)
  12b.teori_vs_metode.png          — Theory-vs-Method heatmap

Usage:
  python3 visualize_bibliometric.py
"""

import csv
import os
import re
import math
import json
import urllib.request
from collections import Counter, defaultdict
from itertools import combinations
import numpy as np
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import pandas as pd

# ─── Config ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Generate bibliometric visualizations.")
parser.add_argument("--out-dir", default=None, help="Output directory.")
args = parser.parse_args()

if args.out_dir:
    CSV_PATH = os.path.join(args.out_dir, "lembar_koding_bibliometrika.csv")
    OUT_DIR = args.out_dir
else:
    CSV_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "lembar_koding_bibliometrika.csv")
    OUT_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visualizations")

os.makedirs(OUT_DIR, exist_ok=True)

# Font and style — academic serif aesthetic
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["STIX", "STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset":   "stix",
    "font.size":          11,
    "axes.titlesize":     13,
    "axes.titleweight":   "bold",
    "axes.labelsize":     11,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.edgecolor":     "#4B5563",
    "axes.labelcolor":    "#1F2937",
    "xtick.color":        "#374151",
    "ytick.color":        "#374151",
    "figure.dpi":         150,
    "figure.facecolor":   "white",
    "axes.facecolor":     "#FAFAFA",
    "grid.color":         "#D1D5DB",
    "grid.linestyle":     "--",
    "grid.alpha":         0.5,
    "legend.framealpha":  0.9,
    "legend.edgecolor":   "#9CA3AF",
    "legend.fontsize":    9,
})

# Academic color palette — muted, harmonious, print-safe
# Primary: slate blues / steel grays; Accents: muted warm tones
PALETTE = [
    "#2B4C7E",  # navy blue
    "#5B8C5A",  # sage green
    "#A45A52",  # muted brick
    "#6B7AA1",  # steel blue
    "#C49A6C",  # warm tan
    "#7A6C5D",  # warm gray
    "#567568",  # dark sage
    "#8E6C88",  # dusty plum
    "#4A7C7E",  # teal
    "#B07156",  # terracotta
    "#3E6B89",  # medium blue
    "#8B7355",  # khaki
    "#5C7457",  # olive
    "#6E5B7B",  # muted purple
    "#976F5C",  # warm brown
]

# ─── Load data ───────────────────────────────────────────────────────────────

def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Kriteria_Inklusi", "Dimasukkan") == "Dimasukkan":
                rows.append(row)
    return rows

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# ─── Helpers ─────────────────────────────────────────────────────────────────

def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✔  {name}")
    return path


def title_wrap(t, width=55):
    words = t.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


# ─── Sub-classification helpers ──────────────────────────────────────────────

def _text_pool(row):
    """Combine title + keywords into a single lowercase search string."""
    parts = [
        row.get("Judul", ""),
        row.get("Author_Keywords", ""),
        row.get("Index_Keywords", ""),
        row.get("Abstrak", ""),
    ]
    return " ".join(parts).lower()


_UMUM_RULES = [
    # (label, keyword_list)  — first match wins
    ("Gerakan sosial & protes",
     ["gerakan sosial", "social movement", "protes", "protest", "mobilisasi",
      "mobiliz", "demonstrasi", "demonstrat", "rally", "petition", "petisi",
      "change.org", "aksi massa", "resistance", "perlawanan", "solidarity",
      "solidaritas", "collective action", "aksi kolektif"]),
    ("Demokrasi & wacana publik",
     ["demokrasi", "democracy", "deliberat", "ruang publik", "public sphere",
      "wacana", "discourse", "opini publik", "public opinion", "partisipasi",
      "participat", "e-government", "civic engagement"]),
    ("Hukum, regulasi & advokasi",
     ["hukum", " law ", "regulasi", "regulation", " uu ", " ruu ",
      "kebijakan", "policy", "advokasi", "advocacy", "legislasi",
      "legislation", "ite", "cipta kerja", "omnibus"]),
    ("Narasi, identitas & budaya",
     ["identitas", "identity", "narrat", "naras", "budaya", "cultur",
      "freedom", "kebebasan", "censorship", "sensor", "semioti",
      "framing", "bingkai", "counter-narrat", "kontra-naras"]),
    ("Studi platform spesifik",
     ["twitter", "facebook", "instagram", "tiktok", "youtube",
      "whatsapp", "telegram", "buzzer", "bot ", "algorithm"]),
    ("Kampanye & komunikasi strategis",
     ["kampanye", "campaign", "branding", "marketing", "public relation",
      "humas", "corporate", "csr", "strateg"]),
]


def sub_classify_umum(row):
    """Assign a sub-theme to a 'Digital activism (umum)' article."""
    text = _text_pool(row)
    for label, keywords in _UMUM_RULES:
        for kw in keywords:
            if kw in text:
                return label
    return "Digital activism (lainnya)"


_THEORY_RULES = [
    ("Analisis wacana / CDA",
     ["discourse analysis", "analisis wacana", "critical discourse",
      "cda", "fairclough", "van dijk"]),
    ("Framing theory",
     ["framing", "bingkai", "entman", "frame analysis"]),
    ("Ruang publik (Habermas)",
     ["public sphere", "ruang publik", "habermas", "deliberat"]),
    ("Teori jaringan / ANT / SNA",
     ["network theory", "actor-network", "ant ", "social network analysis",
      "sna", "latour", "castells"]),
    ("Semiotika / analisis tanda",
     ["semioti", "semiology", "peirce", "saussure", "tanda", "sign "]),
    ("Ekonomi politik media",
     ["political economy", "ekonomi politik", "media economics"]),
    ("Teori partisipasi & civic",
     ["participat", "partisipasi", "civic", "engagement",
      "citizenship", "kewarganegaraan"]),
    ("Komunikasi persuasif / retorika",
     ["persuas", "rhetor", "retorika", "propaganda"]),
]


def infer_theory(row):
    """Infer an implied theoretical approach for 'Campuran' articles."""
    text = _text_pool(row)
    for label, keywords in _THEORY_RULES:
        for kw in keywords:
            if kw in text:
                return label
    return "Tidak eksplisit (deskriptif-empiris)"

# ─── 1. Annual Publication Trend ─────────────────────────────────────────────

def plot_trend(rows):
    years = [safe_int(r["Tahun_Terbit"]) for r in rows if safe_int(r["Tahun_Terbit"]) >= 2010]
    year_counts = Counter(years)
    xs = sorted(year_counts)
    ys = [year_counts[y] for y in xs]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(xs, ys, color=PALETTE[0], width=0.65, alpha=0.85, zorder=3)
    ax.plot(xs, ys, "o-", color=PALETTE[2], linewidth=2, markersize=6, zorder=4)

    # Annotate bars
    for bar, y in zip(bars, ys):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                str(y), ha="center", va="bottom", fontsize=9, color="#1e293b")

    ax.set_xlabel("Tahun Publikasi", labelpad=8)
    ax.set_ylabel("Jumlah Artikel", labelpad=8)
    ax.set_title("Tren Publikasi Artikel (2010–2025)")
    ax.set_xticks(xs)
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_ylim(0, max(ys) * 1.18)

    fig.tight_layout()
    return save(fig, "trend_publikasi.png")


# ─── 2. Theme Distribution ───────────────────────────────────────────────────

def plot_theme(rows):
    themes = [r["Tema_Utama"] for r in rows if r["Tema_Utama"]]
    counts = Counter(themes).most_common(12)
    labels = [title_wrap(c[0], 40) for c in counts]
    vals   = [c[1] for c in counts]
    colors = PALETTE[:len(vals)]

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], alpha=0.88)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontsize=10)

    ax.set_xlabel("Jumlah Artikel")
    ax.set_title("Distribusi Tema Utama dalam Bibliometrika")
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(vals) * 1.15)
    fig.tight_layout()
    return save(fig, "distribusi_tema.png")


# ─── 2b. Detailed Theme Distribution ("umum" broken down) ───────────────────

def _reclassify_theme(row):
    """Return the theme directly."""
    return row.get("Tema_Utama", "").strip()


def plot_theme_detail(rows):
    themes = [_reclassify_theme(r) for r in rows if r.get("Tema_Utama", "").strip()]
    counts = Counter(themes).most_common(15)
    labels = [title_wrap(c[0], 40) for c in counts]
    vals   = [c[1] for c in counts]

    # Color-code: sub-themes from "umum" get a warm gradient, others keep palette
    umum_subs = {label for label, _ in _UMUM_RULES} | {"Digital activism (lainnya)"}
    WARM = ["#A45A52", "#C49A6C", "#B07156", "#8B7355", "#976F5C", "#D2B48C", "#CD853F"]
    COOL = ["#2B4C7E", "#5B8C5A", "#6B7AA1", "#567568", "#4A7C7E", "#3E6B89", "#5C7457", "#465945"]
    warm_idx, cool_idx = 0, 0
    colors = []
    for c in counts:
        raw = c[0]
        if raw in umum_subs:
            colors.append(WARM[warm_idx % len(WARM)])
            warm_idx += 1
        else:
            colors.append(COOL[cool_idx % len(COOL)])
            cool_idx += 1

    fig, ax = plt.subplots(figsize=(13, 7.5))
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], alpha=0.88)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontsize=10)

    ax.set_xlabel("Jumlah Artikel")
    ax.set_title('Distribusi Tema (Detail): Kategori Tema Umum Dipecah', pad=14)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(vals) * 1.18)

    # Legend to distinguish sub-theme vs original
    legend_patches = [
        mpatches.Patch(color=WARM[0], label='Sub-tema dari "Digital activism (umum)"'),
        mpatches.Patch(color=COOL[0], label="Tema spesifik (asli)"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9, framealpha=0.85)

    fig.tight_layout()
    return save(fig, "distribusi_tema_detail.png")


# ─── 3. Local vs International Researcher ────────────────────────────────────

def plot_origin(rows):
    collab_counts = Counter(r["Kolaborasi"] for r in rows if r["Kolaborasi"])

    fig, ax2 = plt.subplots(figsize=(8, 5))

    # Horizontal bar: collaboration type
    collab_items = collab_counts.most_common()
    c_labels = [title_wrap(i[0], 32) for i in collab_items]
    c_vals   = [i[1] for i in collab_items]
    colors2  = PALETTE[:len(c_vals)]
    
    if not c_vals:
        return None
        
    ax2.barh(c_labels[::-1], c_vals[::-1], color=colors2[::-1], alpha=0.85)
    for i, v in enumerate(c_vals[::-1]):
        ax2.text(v + 0.1, i, str(v), va="center", fontsize=10)
    ax2.set_xlabel("Jumlah Artikel")
    ax2.set_title("Tipe Kolaborasi Peneliti")
    ax2.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax2.set_xlim(0, max(c_vals) * 1.18)

    fig.tight_layout()
    return save(fig, "tipe_kolaborasi.png")


# ─── 3b. Top Local Institutions ──────────────────────────────────────────────

def plot_top_institutions(rows):
    """Bar chart of top 15 institutions by article count."""
    afils = [
        r.get("Afiliasi_Penulis_Pertama", "").strip()
        for r in rows
        if r.get("Afiliasi_Penulis_Pertama", "").strip()
    ]
    counts = Counter(afils).most_common(15)
    if not counts:
        return None

    labels = [title_wrap(c[0], 42) for c in counts]
    vals   = [c[1] for c in counts]
    colors = PALETTE[:len(vals)]

    fig, ax = plt.subplots(figsize=(13, 7))
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], alpha=0.88)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontsize=10)

    ax.set_xlabel("Jumlah Artikel")
    ax.set_title(
        'Top 15 Institusi Berdasarkan Afiliasi Penulis Pertama',
        pad=12
    )
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(vals) * 1.2)
    fig.tight_layout()
    return save(fig, "top_institusi.png")


# ─── 4. Top Journals ─────────────────────────────────────────────────────────

def plot_journals(rows):
    journals = [r["Nama_Jurnal_Prosiding"].strip() for r in rows if r["Nama_Jurnal_Prosiding"].strip()]
    counts   = Counter(journals).most_common(15)
    labels   = [title_wrap(c[0], 45) for c in counts]
    vals     = [c[1] for c in counts]

    fig, ax = plt.subplots(figsize=(12, 7))
    colors  = [PALETTE[i % len(PALETTE)] for i in range(len(vals))]
    bars    = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], alpha=0.88)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontsize=9)

    ax.set_xlabel("Jumlah Artikel")
    ax.set_title("15 Jurnal/Prosiding Terbanyak: Bibliometrika")
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(vals) * 1.2)
    fig.tight_layout()
    return save(fig, "top_jurnal.png")


# ─── 5. Top Countries ────────────────────────────────────────────────────────

def plot_countries(rows):
    COUNTRY_MAP = {
        "ID": "Indonesia",   "US": "USA",           "GB": "UK",
        "AU": "Australia",   "NL": "Netherlands",   "MY": "Malaysia",
        "SG": "Singapore",   "DE": "Germany",       "CA": "Canada",
        "NZ": "New Zealand", "PH": "Philippines",   "IN": "India",
        "HK": "Hong Kong",   "JP": "Japan",         "KR": "South Korea",
        "NO": "Norway",      "SE": "Sweden",        "DK": "Denmark",
        "FR": "France",      "IT": "Italy",         "CN": "China",
    }
    cc_list = [r["Negara_Afiliasi"].strip() for r in rows if r["Negara_Afiliasi"].strip()]
    counts  = Counter(cc_list).most_common(12)
    labels  = [COUNTRY_MAP.get(c[0], c[0]) for c in counts]
    vals    = [c[1] for c in counts]
    colors  = PALETTE[:len(counts)]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, vals, color=colors, alpha=0.88, zorder=3)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(v), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Jumlah Artikel")
    ax.set_title("Top Negara Afiliasi Peneliti (Bibliometrika)")
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.tick_params(axis="x", rotation=30)

    fig.tight_layout()
    return save(fig, "top_negara.png")


# ─── 6. Keyword Co-occurrence Network ────────────────────────────────────────

def parse_keywords(kw_str: str) -> list:
    if not kw_str:
        return []
    # Split on ; or ,
    parts = re.split(r"[;,]", kw_str)
    cleaned = []
    for p in parts:
        p = p.strip().lower()
        p = re.sub(r"\s+", " ", p)
        if 2 < len(p) < 50:
            cleaned.append(p)
    return cleaned


# Keywords to exclude (too generic / noise)
STOP_KEYWORDS = {
    "indonesia", "indonesian", "social media", "media", "internet",
    "online", "digital", "activism", "digital activism", "online activism",
    "study", "analysis", "research", "paper", "case", "using",
    "based", "social network", "network", "information",
}


def plot_keyword_network(rows, min_freq=2, min_cooccur=2, max_nodes=40):
    # Count keyword frequencies
    kw_freq: Counter = Counter()
    # Count co-occurrences
    cooccur: Counter = Counter()

    for row in rows:
        kws_raw = row.get("Author_Keywords", "") + ";" + row.get("Index_Keywords", "")
        kws = [k for k in parse_keywords(kws_raw) if k not in STOP_KEYWORDS]
        kws = list(dict.fromkeys(kws))  # deduplicate per article
        kw_freq.update(kws)
        for pair in combinations(sorted(kws), 2):
            cooccur[pair] += 1

    # Filter
    valid_kws = {k for k, v in kw_freq.items() if v >= min_freq}
    valid_kws = set(list(sorted(valid_kws, key=lambda x: -kw_freq[x]))[:max_nodes])

    G = nx.Graph()
    for kw in valid_kws:
        G.add_node(kw, freq=kw_freq[kw])

    for (a, b), weight in cooccur.items():
        if a in valid_kws and b in valid_kws and weight >= min_cooccur:
            G.add_edge(a, b, weight=weight)

    # Remove isolates
    G.remove_nodes_from(list(nx.isolates(G)))

    if len(G.nodes) == 0:
        print("  ⚠️  No nodes after filtering — keyword network skipped.")
        return None

    # Layout
    pos = nx.spring_layout(G, k=2.2, seed=42, iterations=80)

    # Node sizes proportional to frequency
    freqs    = [G.nodes[n]["freq"] for n in G.nodes]
    freq_min = min(freqs) if freqs else 1
    freq_max = max(freqs) if freqs else 1
    node_sizes = [
        300 + 1800 * (G.nodes[n]["freq"] - freq_min) / max(freq_max - freq_min, 1)
        for n in G.nodes
    ]

    # Edge widths proportional to co-occurrence weight
    weights    = [G[u][v]["weight"] for u, v in G.edges]
    w_max      = max(weights) if weights else 1
    edge_widths = [0.5 + 3.5 * w / w_max for w in weights]
    edge_colors = [plt.cm.Blues(0.3 + 0.6 * w / w_max) for w in weights]  # type: ignore

    # Node colors by degree (community-like)
    degrees  = dict(G.degree())
    deg_max  = max(degrees.values()) if degrees else 1
    node_colors = [plt.cm.YlGnBu(0.3 + 0.6 * degrees[n] / deg_max) for n in G.nodes]  # type: ignore

    # Draw
    fig, ax = plt.subplots(figsize=(16, 12))
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        width=edge_widths, edge_color=edge_colors, alpha=0.6
    )
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_size=node_sizes, node_color=node_colors,
        alpha=0.92, linewidths=0.8, edgecolors="white"
    )
    # Labels: only for nodes with freq >= 3
    label_nodes = {n: n for n in G.nodes if G.nodes[n]["freq"] >= 3}
    nx.draw_networkx_labels(
        G, pos, labels=label_nodes, ax=ax,
        font_size=8, font_color="#1e293b", font_weight="bold"
    )

    ax.set_title(
        "Keyword Co-occurrence Network — Bibliometrika\n"
        f"(n={len(G.nodes)} nodes, threshold: freq≥{min_freq}, co-occur≥{min_cooccur})",
        pad=16
    )
    ax.axis("off")

    # Legend: node size
    legend_elems = [
        mpatches.Patch(color=plt.cm.YlGnBu(0.9), label="Frekuensi tinggi / sentral"),  # type: ignore
        mpatches.Patch(color=plt.cm.YlGnBu(0.4), label="Frekuensi rendah / periferal"),  # type: ignore
    ]
    ax.legend(handles=legend_elems, loc="lower left", fontsize=9,
              framealpha=0.85, edgecolor="#94a3b8")

    fig.tight_layout()
    return save(fig, "keyword_cooccurrence.png")


# ─── 7. Country Collaboration Network ────────────────────────────────────────

COUNTRY_MAP_FULL = {
    "ID": "Indonesia",   "US": "USA",        "GB": "UK",
    "AU": "Australia",   "NL": "Netherlands","MY": "Malaysia",
    "SG": "Singapore",   "DE": "Germany",    "CA": "Canada",
    "NZ": "New Zealand", "PH": "Philippines","IN": "India",
    "HK": "Hong Kong",   "JP": "Japan",      "KR": "South Korea",
    "NO": "Norway",      "SE": "Sweden",     "DK": "Denmark",
    "FR": "France",      "IT": "Italy",      "CN": "China",
    "TW": "Taiwan",      "TH": "Thailand",   "ZA": "South Africa",
    "BR": "Brazil",      "ES": "Spain",      "BE": "Belgium",
    "FI": "Finland",     "CH": "Switzerland","AT": "Austria",
}


def plot_country_network(rows, min_collab=1):
    country_articles: Counter = Counter()
    collab_pairs: Counter     = Counter()

    for row in rows:
        cc_str = row.get("Semua_Negara_Afiliasi", "").strip()
        if not cc_str:
            continue
            
        ccs = [COUNTRY_MAP_FULL.get(c.strip(), c.strip()) for c in cc_str.split(";") if c.strip()]
        
        # Count individual country appearances
        for c in ccs:
            country_articles[c] += 1
            
        # Count combinations
        if len(ccs) > 1:
            for pair in combinations(sorted(ccs), 2):
                collab_pairs[pair] += 1

    # Build graph
    G = nx.Graph()
    for country, count in country_articles.items():
        if count >= 1:
            G.add_node(country, count=count)

    for (a, b), weight in collab_pairs.items():
        if G.has_node(a) and G.has_node(b) and weight >= min_collab:
            G.add_edge(a, b, weight=weight)

    if len(G.nodes) < 2:
        print("  ⚠️  Not enough data for country network.")
        return None

    pos = nx.spring_layout(G, k=3, seed=7, weight="weight")

    # Use a single color for all nodes now
    node_colors  = [PALETTE[2] for _ in G.nodes]

    weights      = [G[u][v].get("weight", 1) for u, v in G.edges]
    w_max        = max(weights) if weights else 1
    edge_widths  = [0.8 + 3 * w / w_max for w in weights]

    fig, ax = plt.subplots(figsize=(14, 10))
    nx.draw_networkx_edges(
        G, pos, ax=ax, width=edge_widths,
        edge_color="#94a3b8", alpha=0.7
    )
    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_size=1200,
        node_color=node_colors, alpha=0.88,
        linewidths=1, edgecolors="white"
    )
    import matplotlib.patheffects as path_effects
    labels = nx.draw_networkx_labels(
        G, pos, ax=ax, font_size=8.5,
        font_color="#0F172A", font_weight="bold"
    )
    for _, t in labels.items():
        t.set_path_effects([path_effects.withStroke(linewidth=2.5, foreground="white")])

    ax.set_title(
        "Jaringan Kolaborasi Negara — Bibliometrika\n"
        "(Ukuran node = jumlah artikel; Tebal garis = intensitas kolaborasi)",
        pad=14
    )
    ax.axis("off")

    legend_elems = [
        mpatches.Patch(color=PALETTE[0], label="Indonesia"),
        mpatches.Patch(color=PALETTE[2], label="Negara lain"),
    ]
    ax.legend(handles=legend_elems, loc="lower left", fontsize=9, framealpha=0.85)

    fig.tight_layout()
    return save(fig, "kolaborasi_negara.png")


# ─── 8. Citations per Year (Scatter + Line) ───────────────────────────────────

def plot_citation_trend(rows):
    year_data: dict = defaultdict(list)
    for row in rows:
        y   = safe_int(row["Tahun_Terbit"])
        cit = safe_int(row["Total_Sitasi"])
        if y >= 2010:
            year_data[y].append(cit)

    years     = sorted(year_data)
    avg_cit   = [sum(year_data[y]) / len(year_data[y]) for y in years]
    total_cit = [sum(year_data[y]) for y in years]
    counts    = [len(year_data[y]) for y in years]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Top: avg citation per year
    ax1.set_ylabel("Rata-rata Sitasi", color=PALETTE[3], fontweight="bold")
    ax1.fill_between(years, avg_cit, alpha=0.15, color=PALETTE[3])
    ax1.plot(years, avg_cit, "o-", color=PALETTE[3], linewidth=2, markersize=7)
    for i, txt in enumerate(avg_cit):
        if txt > 0:
            ax1.annotate(f"{txt:.1f}", (years[i], avg_cit[i]), 
                         textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)

    ax1.set_ylim(0, max(avg_cit) * 1.3)
    ax1.set_title("Rata-rata Sitasi per Artikel menurut Tahun Publikasi")
    ax1.yaxis.grid(True, linestyle="--", alpha=0.4)

    # Bottom: total citations stacked with article count
    ax2.bar(years, total_cit, color=PALETTE[0], alpha=0.7, label="Total Sitasi", zorder=3)
    ax2.set_ylabel("Total Sitasi", color=PALETTE[0], fontweight="bold")
    ax2b = ax2.twinx()
    ax2b.plot(years, counts, "s--", color=PALETTE[2], linewidth=1.5, markersize=6, label="Jml Artikel")
    ax2b.set_ylabel("Jumlah Artikel", color=PALETTE[2], fontweight="bold")
    ax2.set_title("Total Sitasi dan Jumlah Artikel per Tahun")
    ax2.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax2.set_xticks(years)
    ax2.tick_params(axis="x", rotation=45)

    fig.suptitle("Analisis Dampak Sitasi: Bibliometrika",
                 fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()
    return save(fig, "sitasi_per_tahun.png")


# ─── 9. Thematic Evolution over Time (with reclassified sub-themes) ──────────

def plot_theme_evolution(rows):
    data = []
    for row in rows:
        y = safe_int(row["Tahun_Terbit"])
        t = _reclassify_theme(row)
        if y >= 2010 and t:
            data.append((y, t))
            
    if not data: return None
    
    df = pd.DataFrame(data, columns=["Year", "Theme"])
    top_themes = df["Theme"].value_counts().nlargest(7).index.tolist()
    
    # Only keep top themes to avoid cluttered lines
    avail_cols = [c for c in top_themes if c in pd.crosstab(df["Year"], df["Theme"]).columns]
    ct = pd.crosstab(df["Year"], df["Theme"])[avail_cols]
    
    min_y = int(df["Year"].min()) if not df.empty else 2010
    max_y = int(df["Year"].max()) if not df.empty else 2025
    all_years = list(range(min_y, max_y + 1))
    ct = ct.reindex(all_years, fill_value=0)
    
    fig, ax = plt.subplots(figsize=(14, 6.5))
    markers = ['o', 's', '^', 'D', 'v', 'P', 'X']
    
    for i, col in enumerate(ct.columns):
        ax.plot(ct.index, ct[col], marker=markers[i % len(markers)], linewidth=2.5, markersize=7, label=title_wrap(col, 30))
        
    ax.set_title("Evolusi Top 7 Tema (dengan Sub-tema Detail) dari Waktu ke Waktu", pad=15)
    ax.set_xlabel("Tahun Publikasi")
    ax.set_ylabel("Jumlah Artikel per Tahun")
    ax.set_xticks(all_years)
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_ylim(0, max(ct.max()) * 1.15) if not ct.empty else None
    
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., title=" Tema", fontsize=9)
    
    fig.tight_layout()
    return save(fig, "evolusi_tema.png")


# ─── 10. Co-citation Network (Jaringan Ko-sitasi) ──────────────────────────

def plot_cocitation_network(rows, min_cooccur=2, max_nodes=35):
    ref_freq = Counter()
    cooccur = Counter()
    
    # 1. Count frequencies and co-occurrences of cited works
    for row in rows:
        refs_str = row.get("Referenced_Works", "")
        if not refs_str: continue
        refs = [r.strip() for r in refs_str.split(";") if r.strip()]
        refs = [r for r in refs if r.startswith("W")]
        
        ref_freq.update(refs)
        for pair in combinations(sorted(refs), 2):
            cooccur[pair] += 1
            
    if not ref_freq:
        print("  ⚠️  No referenced works found for co-citation network.")
        return None

    # 2. Select top nodes
    valid_refs = set(list(sorted(ref_freq.keys(), key=lambda x: -ref_freq[x]))[:max_nodes])
    
    # 3. Retrieve metadata for labels from OpenAlex (to show "Author, Year")
    labels = {}
    try:
        # Correct syntax for OR filter: openalex:W1|W2|W3
        filters = "openalex:" + "|".join(list(valid_refs))
        url = f"https://api.openalex.org/works?filter={filters}&per-page=50&select=id,authorships,publication_year"
        req = urllib.request.Request(url, headers={"User-Agent": "bibliometric-research/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            for w in data.get("results", []):
                wid = w.get("id", "").replace("https://api.openalex.org/", "").replace("https://openalex.org/", "")
                year = w.get("publication_year") or ""
                authors = w.get("authorships", [])
                if authors:
                    author_name = authors[0].get("author", {}).get("display_name", "")
                    if author_name:
                        parts = author_name.split()
                        last_name = parts[0] if ',' in parts[0] else parts[-1]
                        last_name = last_name.replace(',', '').title()
                        labels[wid] = f"{last_name} ({year})"
                if wid not in labels:
                    labels[wid] = f"Ref {wid[-4:]}"
    except Exception as e:
        print(f"  ⚠️  Error fetching metadata: {e}")
        for w in valid_refs: labels[w] = w
        
    for w in valid_refs:
        if w not in labels:
            labels[w] = f"Ref {w[-4:]}"
            
    # 4. Build Graph
    G = nx.Graph()
    for w in valid_refs:
        # require minimum frequency to be isolated? We'll let min_cooccur handle structural noise
        G.add_node(w, freq=ref_freq[w])
        
    for (a, b), weight in cooccur.items():
        if a in valid_refs and b in valid_refs and weight >= min_cooccur:
            G.add_edge(a, b, weight=weight)
            
    G.remove_nodes_from(list(nx.isolates(G)))
    if len(G.nodes) == 0:
        print("  ⚠️  Co-citation graph empty after filtering.")
        return None
        
    # 5. Draw Graph
    pos = nx.spring_layout(G, k=3, seed=42, iterations=100)
    
    freqs = [G.nodes[n]["freq"] for n in G.nodes]
    f_min, f_max = min(freqs), max(freqs)
    f_range = max(f_max - f_min, 1)
    
    node_sizes = [600 + 2400 * (G.nodes[n]["freq"] - f_min) / f_range for n in G.nodes]
    
    degrees = dict(G.degree())
    deg_max = max(degrees.values()) if degrees else 1
    node_colors = [plt.cm.YlGnBu(0.4 + 0.6 * (degrees[n] / deg_max))[:3] for n in G.nodes]
    
    weights = [G[u][v]["weight"] for u, v in G.edges]
    w_max = max(weights) if weights else 1
    edge_widths = [0.5 + 4 * (w / w_max) for w in weights]
    
    fig, ax = plt.subplots(figsize=(16, 12))
    
    nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths, edge_color="#CBD5E1", alpha=0.6)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, 
                           edgecolors="white", linewidths=1.5, alpha=0.9)
                           
    label_dict = {n: labels[n] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=label_dict, ax=ax, font_size=8, 
                            font_weight="bold", font_color="#0F172A")
                            
    ax.set_title("Jaringan Ko-sitasi (Co-citation Network)\n"
                 "(Mengakarkan Teori: Referensi yang paling sering disitasi bersama secara struktural)", 
                 pad=20)
    ax.axis("off")
    fig.tight_layout()
    return save(fig, "jaringan_kositasi.png")


# ─── 11. Top Authors by Total Citations ──────────────────────────────────────

def plot_top_authors(rows):
    author_cits = defaultdict(int)
    for row in rows:
        authors_str = row.get("Penulis", "")
        cit = safe_int(row.get("Total_Sitasi", 0))
        if not authors_str or cit == 0: continue
        
        # Split authors by ; and remove et al.
        authors = [a.strip() for a in authors_str.split(";")]
        for a in authors:
            if a.lower() != "et al.":
                author_cits[a] += cit
                
    counts = Counter(author_cits).most_common(15)
    if not counts: return None
    
    labels = [title_wrap(c[0], 35) for c in counts]
    vals   = [c[1] for c in counts]

    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(labels[::-1], vals[::-1], color=PALETTE[0], alpha=0.88)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + max(vals)*0.01, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontsize=10)

    ax.set_xlabel("Total Sitasi yang Diperoleh")
    ax.set_title("15 Penulis dengan Total Sitasi Terbanyak dalam Korpus")
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(vals) * 1.15)
    fig.tight_layout()
    return save(fig, "top_penulis.png")

# ─── 12. Most Frequent Theories (with inferred sub-categories) ──────────────

def _reclassify_theory(row):
    """Return the theory directly."""
    return row.get("Teori_Kerangka", "").strip()


def plot_top_theories(rows):
    theories = [_reclassify_theory(r) for r in rows if r.get("Teori_Kerangka", "").strip()]
    counts = Counter(theories).most_common(14)
    if not counts: return None

    labels = [title_wrap(c[0], 40) for c in counts]
    vals   = [c[1] for c in counts]

    # Muted warm vs cool color palettes
    inferred_labels = {label for label, _ in _THEORY_RULES}
    WARM_T = ["#A45A52", "#C49A6C", "#B07156", "#8B7355", "#976F5C", "#D2B48C", "#CD853F", "#BC8F8F"]
    COOL_T = ["#2B4C7E", "#5B8C5A", "#6B7AA1", "#567568", "#4A7C7E", "#3E6B89", "#5C7457", "#465945"]
    warm_idx, cool_idx = 0, 0
    colors = []
    for c in counts:
        raw = c[0]
        if raw in inferred_labels:
            colors.append(WARM_T[warm_idx % len(WARM_T)])
            warm_idx += 1
        else:
            colors.append(COOL_T[cool_idx % len(COOL_T)])
            cool_idx += 1

    fig, ax = plt.subplots(figsize=(13, 7.5))
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], alpha=0.88)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(bar.get_width() + max(vals)*0.01, bar.get_y() + bar.get_height()/2,
                str(v), va="center", fontsize=10)

    ax.set_xlabel("Jumlah Artikel")
    ax.set_title(
        'Teori/Kerangka Konseptual: Kategori "Campuran" Dipecah\n'
        '(Inferensi berdasarkan kata kunci judul & abstrak)',
        pad=12
    )
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(vals) * 1.18)

    legend_patches = [
        mpatches.Patch(color=WARM_T[0], label='Inferensi dari "Campuran"'),
        mpatches.Patch(color=COOL_T[0], label="Teori eksplisit (asli)"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9, framealpha=0.85)

    fig.tight_layout()
    return save(fig, "top_teori.png")


# ─── 12b. Theory vs Method Heatmap ───────────────────────────────────────────

def plot_theory_method_matrix(rows):
    """Heatmap showing the relationship between declared theories and methods."""
    pairs = []
    for r in rows:
        theory = r.get("Teori_Kerangka", "").strip()
        method = r.get("Metode_Penelitian", "").strip()
        if theory and method:
            # Use reclassified theory
            rc_theory = _reclassify_theory(r)
            # Simplify compound methods: take first part
            method_clean = method.split(";")[0].strip()
            pairs.append((rc_theory, method_clean))

    if not pairs:
        return None

    df = pd.DataFrame(pairs, columns=["Theory", "Method"])

    # Keep only theories with >= 5 articles and methods with >= 3
    theory_counts = df["Theory"].value_counts()
    method_counts = df["Method"].value_counts()
    keep_theories = theory_counts[theory_counts >= 5].index.tolist()
    keep_methods  = method_counts[method_counts >= 3].index.tolist()

    df_filt = df[df["Theory"].isin(keep_theories) & df["Method"].isin(keep_methods)]
    if df_filt.empty:
        return None

    ct = pd.crosstab(df_filt["Theory"], df_filt["Method"])

    # Wrap long labels
    ct.index   = [title_wrap(i, 35) for i in ct.index]
    ct.columns = [title_wrap(c, 22) for c in ct.columns]

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(ct.values, cmap="Blues", aspect="auto")

    ax.set_xticks(range(len(ct.columns)))
    ax.set_yticks(range(len(ct.index)))
    ax.set_xticklabels(ct.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticklabels(ct.index, fontsize=9)

    # Annotate cells
    for i in range(len(ct.index)):
        for j in range(len(ct.columns)):
            val = ct.values[i, j]
            if val > 0:
                color = "white" if val > ct.values.max() * 0.6 else "#1e293b"
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=9, fontweight="bold", color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.7, label="Jumlah Artikel")

    ax.set_title(
        "Matriks Teori × Metode Penelitian\n"
        "(Menunjukkan korelasi antara kerangka teoritis dan pendekatan metodologis)",
        pad=14
    )
    ax.set_xlabel("Metode Penelitian", labelpad=10)
    ax.set_ylabel("Teori / Kerangka Konseptual", labelpad=10)

    fig.tight_layout()
    return save(fig, "teori_vs_metode.png")


# ─── 13. Theory Evolution (Stacked Area) ─────────────────────────────────────

def plot_theory_evolution(rows):
    """Stacked area chart of reclassified theories over time."""
    data = []
    for row in rows:
        y = safe_int(row["Tahun_Terbit"])
        t = _reclassify_theory(row)
        if y >= 2012 and t:
            data.append((y, t))

    if not data:
        return None

    df = pd.DataFrame(data, columns=["Year", "Theory"])
    top_theories = df["Theory"].value_counts().nlargest(8).index.tolist()

    # Crosstab & fill
    ct_full = pd.crosstab(df["Year"], df["Theory"])
    avail = [c for c in top_theories if c in ct_full.columns]
    ct = ct_full[avail]
    min_y, max_y = int(df["Year"].min()), int(df["Year"].max())
    ct = ct.reindex(range(min_y, max_y + 1), fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 7))
    wrapped_labels = [title_wrap(c, 30) for c in ct.columns]
    ax.stackplot(
        ct.index, *[ct[col] for col in ct.columns],
        labels=wrapped_labels,
        alpha=0.82,
    )
    ax.set_title(
        "Evolusi Kerangka Teoritis dari Waktu ke Waktu (Stacked Area)\n"
        "(Menunjukkan kapan setiap pendekatan teoritis masuk ke wacana)",
        pad=14,
    )
    ax.set_xlabel("Tahun Publikasi")
    ax.set_ylabel("Jumlah Artikel")
    ax.set_xticks(range(min_y, max_y + 1))
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1),
        borderaxespad=0.0, title="Teori", fontsize=8,
    )
    fig.tight_layout()
    return save(fig, "evolusi_teori.png")


# ─── 14. Foundational Reference Genealogy ─────────────────────────────────────

def plot_reference_genealogy(rows, top_n=20):
    """Timeline of the most-cited foundational references in the corpus."""
    ref_freq = Counter()
    for row in rows:
        refs_str = row.get("Referenced_Works", "")
        if not refs_str:
            continue
        for r in refs_str.split(";"):
            r = r.strip()
            if r.startswith("W"):
                ref_freq[r] += 1

    if not ref_freq:
        print("  ⚠️  No referenced works found.")
        return None

    top_refs = [wid for wid, _ in ref_freq.most_common(top_n)]

    # Resolve metadata via OpenAlex
    meta = {}  # wid -> {author, year, title}
    try:
        filters = "openalex:" + "|".join(top_refs)
        url = (
            f"https://api.openalex.org/works?filter={filters}"
            f"&per-page={top_n}&select=id,title,authorships,publication_year"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "bibliometric-research/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            for w in data.get("results", []):
                wid = (
                    w.get("id", "")
                    .replace("https://api.openalex.org/", "")
                    .replace("https://openalex.org/", "")
                )
                year = w.get("publication_year") or 0
                title = w.get("title", "") or ""
                authors = w.get("authorships", [])
                author_name = ""
                if authors:
                    raw = authors[0].get("author", {}).get("display_name", "")
                    if raw:
                        parts = raw.split()
                        author_name = parts[-1].replace(",", "").title()
                meta[wid] = {
                    "author": author_name,
                    "year": year,
                    "title": title[:70],
                }
    except Exception as e:
        print(f"  ⚠️  OpenAlex fetch error: {e}")

    # Build plot data — skip entries that failed metadata resolution
    entries = []
    for wid in top_refs:
        freq = ref_freq[wid]
        m = meta.get(wid, {})
        year = m.get("year", 0)
        title = m.get("title", "")
        # Skip references with unresolved metadata (year=0 or no title)
        if not year or year < 1950 or not title:
            continue
        label = (
            f"{m.get('author', '?')} ({year})\n"
            f"{title_wrap(title, 45)}"
        )
        entries.append((year, freq, label, wid))

    entries.sort(key=lambda x: x[0])

    fig, ax = plt.subplots(figsize=(14, 9))
    y_positions = list(range(len(entries)))
    years = [e[0] for e in entries]
    freqs = [e[1] for e in entries]
    labels_list = [e[2] for e in entries]

    # Size proportional to citation frequency
    max_freq = max(freqs) if freqs else 1
    sizes = [200 + 1200 * (f / max_freq) for f in freqs]
    colors_g = [plt.cm.YlGnBu(0.4 + 0.6 * f / max_freq) for f in freqs]  # type: ignore

    ax.scatter(years, y_positions, s=sizes, c=colors_g, alpha=0.85,
              edgecolors="white", linewidths=1.5, zorder=3)

    for i, (yr, freq, label, _) in enumerate(entries):
        ax.annotate(
            f"{label}\n[Disitasi {freq}× dalam korpus]",
            (yr, i),
            xytext=(18, 0),
            textcoords="offset points",
            fontsize=7.5,
            va="center",
            ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#F8FAFC",
                      edgecolor="#CBD5E1", alpha=0.9),
        )

    ax.set_xlabel("Tahun Publikasi Referensi Asli", labelpad=10)
    ax.set_yticks([])
    ax.set_title(
        "Genealogi Referensi Fondasi (Foundational Reference Timeline)\n"
        "(Karya-karya paling banyak disitasi secara kolektif oleh korpus)",
        pad=14,
    )
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(min(years) - 1, max(years) + 4)
    fig.tight_layout()
    return save(fig, "genealogi_referensi.png")


# ─── 15. Citation Impact by Theme ─────────────────────────────────────────────

def plot_citation_by_theme(rows):
    """Horizontal bar chart of average citations per reclassified theme."""
    theme_cits = defaultdict(list)
    for r in rows:
        theme = _reclassify_theme(r)
        cit = safe_int(r.get("Total_Sitasi", 0))
        if theme:
            theme_cits[theme].append(cit)

    # Sort by avg citation descending
    stats = []
    for theme, cits in theme_cits.items():
        if len(cits) >= 2:
            avg = sum(cits) / len(cits)
            stats.append((theme, avg, len(cits), sum(cits)))
    stats.sort(key=lambda x: -x[1])

    if not stats:
        return None

    labels = [title_wrap(s[0], 35) for s in stats]
    avgs = [s[1] for s in stats]
    ns = [s[2] for s in stats]

    fig, ax = plt.subplots(figsize=(13, 8))
    bars = ax.barh(labels[::-1], avgs[::-1], color=PALETTE[0], alpha=0.88)

    for bar, avg_val, n in zip(bars, avgs[::-1], ns[::-1]):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            f"{avg_val:.1f}  (n={n})",
            va="center", fontsize=9,
        )

    ax.set_xlabel("Rata-rata Sitasi per Artikel")
    ax.set_title(
        "Dampak Sitasi per Tema (Reklasifikasi)\n"
        "(Rata-rata sitasi artikel dalam setiap sub-tema)",
        pad=12,
    )
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(0, max(avgs) * 1.25)
    fig.tight_layout()
    return save(fig, "dampak_sitasi_per_tema.png")


# ─── 16. Citation Impact by Collaboration Type ────────────────────────────────

def plot_citation_by_collaboration(rows):
    """Bar chart of avg citations by collaboration type."""
    collab_cits = defaultdict(list)
    for r in rows:
        collab = r.get("Kolaborasi", "").strip()
        cit = safe_int(r.get("Total_Sitasi", 0))
        if collab:
            collab_cits[collab].append(cit)

    stats = []
    for collab, cits in collab_cits.items():
        if len(cits) >= 2:
            avg = sum(cits) / len(cits)
            stats.append((collab, avg, len(cits)))
    stats.sort(key=lambda x: -x[1])

    if not stats:
        return None

    labels = [s[0] for s in stats]
    avgs = [s[1] for s in stats]
    ns = [s[2] for s in stats]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(labels, avgs, color=PALETTE[0], alpha=0.88, zorder=3)

    for bar, avg_val, n in zip(bars, avgs, ns):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{avg_val:.1f}\n(n={n})",
            ha="center", va="bottom", fontsize=9,
        )

    ax.set_ylabel("Rata-rata Sitasi")
    ax.set_title(
        "Dampak Sitasi Berdasarkan Tipe Kolaborasi\n"
        "(Apakah kolaborasi internasional menghasilkan sitasi lebih tinggi?)",
        pad=12,
    )
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax.set_ylim(0, max(avgs) * 1.3)
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    return save(fig, "dampak_sitasi_kolaborasi.png")


# ─── 17. Platform Evolution ───────────────────────────────────────────────────

def plot_platform_evolution(rows):
    """Line chart of platform-specific studies over time."""
    data = []
    for row in rows:
        y = safe_int(row["Tahun_Terbit"])
        p = row.get("Platform_yang_Dikaji", "").strip()
        if y >= 2014 and p and p != "Tidak spesifik / multi-platform":
            # Normalize compound platforms to first
            p_clean = p.split(";")[0].strip()
            data.append((y, p_clean))

    if not data:
        return None

    df = pd.DataFrame(data, columns=["Year", "Platform"])
    top_plats = df["Platform"].value_counts().nlargest(5).index.tolist()
    avail = [c for c in top_plats if c in pd.crosstab(df["Year"], df["Platform"]).columns]
    ct = pd.crosstab(df["Year"], df["Platform"])[avail]

    min_y, max_y = int(df["Year"].min()), int(df["Year"].max())
    ct = ct.reindex(range(min_y, max_y + 1), fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))
    markers = ["o", "s", "^", "D", "v"]

    for i, col in enumerate(ct.columns):
        ax.plot(
            ct.index, ct[col],
            marker=markers[i % len(markers)],
            linewidth=2.5, markersize=8,
            label=col,
        )

    ax.set_title(
        "Evolusi Platform yang Dikaji dari Waktu ke Waktu\n"
        "(Hanya artikel dengan platform spesifik, bukan \"multi-platform\")",
        pad=14,
    )
    ax.set_xlabel("Tahun Publikasi")
    ax.set_ylabel("Jumlah Artikel")
    ax.set_xticks(range(min_y, max_y + 1))
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    if not ct.empty:
        ax.set_ylim(0, max(ct.max()) * 1.2)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.85)
    fig.tight_layout()
    return save(fig, "evolusi_platform.png")


# ─── 18. Publisher/Indexer Classification ─────────────────────────────────────

_INTL_DOI_PREFIXES = {
    "10.1080": "Taylor & Francis",
    "10.3390": "MDPI",
    "10.1177": "SAGE",
    "10.1007": "Springer",
    "10.1017": "Cambridge UP",
    "10.1093": "Oxford UP",
    "10.1016": "Elsevier",
    "10.1002": "Wiley",
    "10.1111": "Wiley",
    "10.1186": "BioMed Central",
    "10.3389": "Frontiers",
    "10.1145": "ACM",
    "10.1109": "IEEE",
}


def classify_publisher(row):
    """Classify a row into publisher tier based on DOI prefix."""
    doi = row.get("DOI", "").strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    prefix = doi.split("/")[0] if doi else ""

    if prefix in _INTL_DOI_PREFIXES:
        return "Penerbit Internasional", _INTL_DOI_PREFIXES[prefix]
    if prefix == "10.2991":
        return "Prosiding Konferensi", "Atlantis Press"
    if prefix.startswith("10."):  # 5+ digit or any other unmapped DOI
        return "Jurnal Lainnya", ""
    if prefix:
        return "Lainnya", prefix
    return "Tanpa DOI", ""


def plot_publisher_distribution(rows):
    """Pie chart of publisher tiers + bar chart of citation impact per tier."""
    tier_counts = Counter()
    tier_cits = defaultdict(list)
    intl_detail = Counter()

    for r in rows:
        tier, detail = classify_publisher(r)
        tier_counts[tier] += 1
        cit = safe_int(r.get("Total_Sitasi", 0))
        tier_cits[tier].append(cit)
        if tier == "Penerbit Internasional" and detail:
            intl_detail[detail] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Pie chart
    tier_order = ["Jurnal Lainnya", "Penerbit Internasional",
                  "Prosiding Konferensi", "Lainnya", "Tanpa DOI"]
    dist = {t: tier_counts[t] for t in tier_order if tier_counts.get(t, 0) > 0}
    pie_labels = [f"{t}\n(n={v})" for t, v in dist.items()]
    pie_colors = ["#2B4C7E", "#5B8C5A", "#C49A6C", "#94A3B8", "#CBD5E1"]

    wedges, texts, autotexts = ax1.pie(
        dist.values(), labels=pie_labels, colors=pie_colors[:len(pie_labels)],
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=140, pctdistance=0.75,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax1.set_title("Distribusi Penerbit\n(Berdasarkan DOI prefix)", pad=10)

    # Bar chart: avg citation per tier
    bar_tiers = [t for t in tier_order if t in tier_cits and len(tier_cits[t]) >= 2]
    bar_avgs = [sum(tier_cits[t]) / len(tier_cits[t]) for t in bar_tiers]
    bar_ns = [len(tier_cits[t]) for t in bar_tiers]
    bar_labels = [title_wrap(t, 20) for t in bar_tiers]
    bar_colors = [pie_colors[tier_order.index(t)] if t in tier_order else "#94A3B8"
                  for t in bar_tiers]

    bars = ax2.bar(bar_labels, bar_avgs, color=bar_colors, alpha=0.88, zorder=3)
    for bar, avg_val, n in zip(bars, bar_avgs, bar_ns):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            f"{avg_val:.1f}\n(n={n})",
            ha="center", va="bottom", fontsize=9,
        )
    ax2.set_ylabel("Rata-rata Sitasi")
    ax2.set_title("Dampak Sitasi per Tier Penerbit", pad=10)
    ax2.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax2.set_ylim(0, max(bar_avgs) * 1.35 if bar_avgs else 10)
    ax2.tick_params(axis="x", rotation=15)

    fig.suptitle(
        "Klasifikasi Penerbit dan Dampak Sitasi",
        fontsize=14, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    return save(fig, "distribusi_penerbit.png")


# ─── 19. Theme × Method Heatmap ──────────────────────────────────────────────

def plot_theme_method_matrix(rows):
    """Heatmap: reclassified theme × declared research method."""
    pairs = []
    for r in rows:
        theme = _reclassify_theme(r)
        method = r.get("Metode_Penelitian", "").strip()
        if theme and method and method != "Tidak dinyatakan eksplisit":
            method_clean = method.split(";")[0].strip()
            pairs.append((theme, method_clean))

    if not pairs:
        return None

    df = pd.DataFrame(pairs, columns=["Theme", "Method"])
    theme_counts = df["Theme"].value_counts()
    method_counts = df["Method"].value_counts()
    keep_themes = theme_counts[theme_counts >= 2].index.tolist()
    keep_methods = method_counts[method_counts >= 2].index.tolist()

    df_filt = df[df["Theme"].isin(keep_themes) & df["Method"].isin(keep_methods)]
    if df_filt.empty:
        return None

    ct = pd.crosstab(df_filt["Theme"], df_filt["Method"])
    ct.index = [title_wrap(i, 30) for i in ct.index]
    ct.columns = [title_wrap(c, 22) for c in ct.columns]

    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(ct.values, cmap="YlGnBu", aspect="auto")

    ax.set_xticks(range(len(ct.columns)))
    ax.set_yticks(range(len(ct.index)))
    ax.set_xticklabels(ct.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticklabels(ct.index, fontsize=9)

    for i in range(len(ct.index)):
        for j in range(len(ct.columns)):
            val = ct.values[i, j]
            if val > 0:
                color = "white" if val > ct.values.max() * 0.6 else "#1e293b"
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=9, fontweight="bold", color=color)

    fig.colorbar(im, ax=ax, shrink=0.7, label="Jumlah Artikel")
    ax.set_title(
        "Matriks Tema × Metode Penelitian\n"
        "(Hanya artikel dengan metode yang dideklarasikan eksplisit)",
        pad=14,
    )
    ax.set_xlabel("Metode Penelitian", labelpad=10)
    ax.set_ylabel("Tema (Reklasifikasi)", labelpad=10)
    fig.tight_layout()
    return save(fig, "tema_vs_metode.png")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Bibliometric Visualization Generator")
    print(f"  Input : {CSV_PATH}")
    print(f"  Output: {OUT_DIR}/")
    print("=" * 60)

    rows = load_csv(CSV_PATH)
    print(f"\n📥 Loaded {len(rows)} rows\n")

    tasks = [
        ("📈 1.  Tren publikasi tahunan",           lambda: plot_trend(rows)),
        ("📊 2.  Distribusi tema",                   lambda: plot_theme(rows)),
        ("📊 2b. Distribusi tema (detail)",          lambda: plot_theme_detail(rows)),
        ("🌍 3.  Tipe Kolaborasi",                  lambda: plot_origin(rows)),
        ("🏛️  3b. Top institusi",                   lambda: plot_top_institutions(rows)),
        ("📰 4.  Top jurnal",                        lambda: plot_journals(rows)),
        ("🗺️  5.  Top negara afiliasi",              lambda: plot_countries(rows)),
        ("🕸️  6.  Keyword co-occurrence network",    lambda: plot_keyword_network(rows)),
        ("🤝 7.  Jaringan kolaborasi negara",        lambda: plot_country_network(rows)),
        ("⭐ 8.  Sitasi per tahun",                  lambda: plot_citation_trend(rows)),
        ("📈 9.  Evolusi tema (detail)",             lambda: plot_theme_evolution(rows)),
        ("🔗 10. Jaringan ko-sitasi referensi",      lambda: plot_cocitation_network(rows)),
        ("🏆 11. Top penulis berdasarkan sitasi",    lambda: plot_top_authors(rows)),
        ("📚 12. Teori/Kerangka (detail)",           lambda: plot_top_theories(rows)),
        ("🔥 12b.Matriks teori × metode",            lambda: plot_theory_method_matrix(rows)),
        ("📐 13. Evolusi teori (stacked area)",      lambda: plot_theory_evolution(rows)),
        ("🌳 14. Genealogi referensi fondasi",       lambda: plot_reference_genealogy(rows)),
        ("💡 15. Dampak sitasi per tema",            lambda: plot_citation_by_theme(rows)),
        ("🤝 16. Dampak sitasi per kolaborasi",      lambda: plot_citation_by_collaboration(rows)),
        ("🏢 17. Distribusi penerbit & dampak",      lambda: plot_publisher_distribution(rows)),
        ("🗂️  18. Matriks tema × metode",             lambda: plot_theme_method_matrix(rows)),
    ]

    generated = []
    for label, fn in tasks:
        print(f"{label}...")
        try:
            result = fn()
            if result:
                generated.append(result)
        except Exception as exc:
            print(f"  ⚠️  Skipped ({exc})")

    print(f"\n✅ Done! {len(generated)} visualizations saved to ./{OUT_DIR}/")
    for p in generated:
        print(f"   • {os.path.basename(p)}")


if __name__ == "__main__":
    main()
