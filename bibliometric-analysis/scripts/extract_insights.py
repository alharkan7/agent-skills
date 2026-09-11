import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
import argparse

# Allow importing from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from visualize_bibliometric import (
    sub_classify_umum,
    infer_theory,
    _reclassify_theme,
    _reclassify_theory,
    classify_publisher,
)

CSV_PATH = "lembar_koding_bibliometrika.csv"
OUT_JSON = "insights_data.json"

def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Kriteria_Inklusi", "Dimasukkan") == "Dimasukkan":
                rows.append(row)
    return rows

def safe_int(x):
    try:
        return int(float(x))
    except (ValueError, TypeError):
        return 0

def parse_keywords(kw_str: str) -> list:
    if not kw_str: return []
    parts = re.split(r"[;,]", kw_str)
    cleaned = []
    for p in parts:
        p = re.sub(r"\s+", " ", p.strip().lower())
        if 2 < len(p) < 50:
            cleaned.append(p)
    return cleaned

STOP_KEYWORDS = {
    "indonesia", "indonesian", "social media", "media", "internet",
    "online", "digital", "activism", "digital activism", "online activism",
    "study", "analysis", "research", "paper", "case", "using",
    "based", "social network", "network", "information",
}

COUNTRY_MAP_FULL = {
    "ID": "Indonesia", "US": "USA", "GB": "UK", "AU": "Australia",
    "NL": "Netherlands", "MY": "Malaysia", "SG": "Singapore",
    "DE": "Germany", "CA": "Canada", "NZ": "New Zealand",
    "PH": "Philippines", "IN": "India", "HK": "Hong Kong",
    "JP": "Japan", "KR": "South Korea", "NO": "Norway",
    "SE": "Sweden", "DK": "Denmark", "FR": "France",
    "IT": "Italy", "CN": "China", "TW": "Taiwan", "TH": "Thailand",
}

def main():
    parser = argparse.ArgumentParser(description="Extract bibliometric insights.")
    parser.add_argument("--out-dir", default=".", help="Output directory.")
    args = parser.parse_args()

    in_path = os.path.join(args.out_dir, CSV_PATH)
    out_path = os.path.join(args.out_dir, OUT_JSON)

    try:
        rows = load_csv(in_path)
    except FileNotFoundError:
        print(f"Error: Could not find {in_path}. Run data fetch script first.")
        sys.exit(1)

    data = {}

    
    # 1. Tren Publikasi
    years = [safe_int(r["Tahun_Terbit"]) for r in rows if safe_int(r["Tahun_Terbit"]) >= 2010]
    data["tren_publikasi"] = dict(sorted(Counter(years).items()))

    # 2. Tema (original)
    themes = [r["Tema_Utama"] for r in rows if r["Tema_Utama"]]
    data["distribusi_tema"] = dict(Counter(themes).most_common(12))

    # 2b. Tema (detail — "umum" broken down)
    themes_detail = [_reclassify_theme(r) for r in rows if r.get("Tema_Utama", "").strip()]
    data["distribusi_tema_detail"] = dict(Counter(themes_detail).most_common(18))

    # 3. Asal Peneliti & Kolaborasi
    data["asal_peneliti"] = dict(Counter(r["Asal_Peneliti"] for r in rows if r["Asal_Peneliti"]))
    data["kolaborasi"] = dict(Counter(r["Kolaborasi"] for r in rows if r["Kolaborasi"]))

    # 3b. Top Institusi
    afils = [
        r.get("Afiliasi_Penulis_Pertama", "").strip()
        for r in rows
        if r.get("Afiliasi_Penulis_Pertama", "").strip()
    ]
    data["top_institusi"] = dict(Counter(afils).most_common(10))

    # 4. Top Jurnal
    journals = [r["Nama_Jurnal_Prosiding"].strip() for r in rows if r["Nama_Jurnal_Prosiding"].strip()]
    data["top_jurnal"] = dict(Counter(journals).most_common(15))

    # 5. Top Negara
    cc_list = [r["Negara_Afiliasi"].strip() for r in rows if r["Negara_Afiliasi"].strip()]
    counts = Counter(cc_list).most_common(12)
    data["top_negara"] = {COUNTRY_MAP_FULL.get(k, k): v for k, v in counts}

    # 6. Keywords
    kw_freq = Counter()
    for row in rows:
        kws_raw = row.get("Author_Keywords", "") + ";" + row.get("Index_Keywords", "")
        kws = [k for k in parse_keywords(kws_raw) if k not in STOP_KEYWORDS]
        kw_freq.update(list(dict.fromkeys(kws)))
    data["top_keywords"] = dict(kw_freq.most_common(20))

    # 7. Kolaborasi Negara
    collab_pairs = Counter()
    for row in rows:
        cc_str = row.get("Semua_Negara_Afiliasi", "").strip()
        if not cc_str:
            continue
        ccs = [COUNTRY_MAP_FULL.get(c.strip(), c.strip()) for c in cc_str.split(";") if c.strip()]
        if len(ccs) > 1:
            for pair in combinations(sorted(ccs), 2):
                collab_pairs[" & ".join(pair)] += 1
    data["kolaborasi_negara"] = dict(collab_pairs.most_common(10))

    # 8. Sitasi per Tahun
    year_data = defaultdict(list)
    for row in rows:
        y = safe_int(row["Tahun_Terbit"])
        cit = safe_int(row["Total_Sitasi"])
        if y >= 2010: year_data[y].append(cit)
    
    data["sitasi"] = {}
    for y in sorted(year_data):
        cits = year_data[y]
        data["sitasi"][y] = {
            "total_articles": len(cits),
            "total_citations": sum(cits),
            "avg_citations": round(sum(cits)/len(cits), 1)
        }

    # 12. Teori (original)
    theories_orig = [r.get("Teori_Kerangka", "").strip() for r in rows if r.get("Teori_Kerangka", "").strip()]
    data["distribusi_teori"] = dict(Counter(theories_orig).most_common(12))

    # 12b. Teori (detail — "Campuran" broken down)
    theories_detail = [_reclassify_theory(r) for r in rows if r.get("Teori_Kerangka", "").strip()]
    data["distribusi_teori_detail"] = dict(Counter(theories_detail).most_common(16))

    # 12c. Teori × Metode matrix (sparse representation)
    theory_method_pairs = Counter()
    for r in rows:
        theory = r.get("Teori_Kerangka", "").strip()
        method = r.get("Metode_Penelitian", "").strip()
        if theory and method:
            rc_theory = _reclassify_theory(r)
            method_clean = method.split(";")[0].strip()
            theory_method_pairs[(rc_theory, method_clean)] += 1
    data["teori_vs_metode"] = {
        f"{t} | {m}": v for (t, m), v in theory_method_pairs.most_common(30)
    }

    # 13. Theory evolution by year
    theory_year = defaultdict(lambda: Counter())
    for r in rows:
        y = safe_int(r["Tahun_Terbit"])
        t = _reclassify_theory(r)
        if y >= 2012 and t:
            theory_year[t][y] += 1
    # Flatten: {theory: {year: count}}
    data["evolusi_teori"] = {
        theory: dict(sorted(yc.items()))
        for theory, yc in sorted(theory_year.items(), key=lambda x: -sum(x[1].values()))
        if sum(yc.values()) >= 5
    }

    # 15. Citation impact by theme
    theme_cits = defaultdict(list)
    for r in rows:
        theme = _reclassify_theme(r)
        cit = safe_int(r.get("Total_Sitasi", 0))
        if theme:
            theme_cits[theme].append(cit)
    data["dampak_sitasi_per_tema"] = {
        theme: {"avg": round(sum(c)/len(c), 1), "n": len(c), "total": sum(c)}
        for theme, c in sorted(theme_cits.items(), key=lambda x: -sum(x[1])/len(x[1]))
        if len(c) >= 2
    }

    # 16. Citation impact by collaboration type
    collab_cit_data = defaultdict(list)
    for r in rows:
        collab = r.get("Kolaborasi", "").strip()
        cit = safe_int(r.get("Total_Sitasi", 0))
        if collab:
            collab_cit_data[collab].append(cit)
    data["dampak_sitasi_kolaborasi"] = {
        collab: {"avg": round(sum(c)/len(c), 1), "n": len(c)}
        for collab, c in sorted(collab_cit_data.items(), key=lambda x: -sum(x[1])/len(x[1]))
        if len(c) >= 2
    }

    # Citation impact by language
    lang_cits = defaultdict(list)
    for r in rows:
        lang = r.get("Bahasa", "").strip()
        cit = safe_int(r.get("Total_Sitasi", 0))
        if lang:
            lang_cits[lang].append(cit)
    data["dampak_sitasi_bahasa"] = {
        lang: {"avg": round(sum(c)/len(c), 1), "n": len(c), "total": sum(c)}
        for lang, c in sorted(lang_cits.items(), key=lambda x: -sum(x[1])/len(x[1]))
    }

    # 18. Publisher/Indexer distribution
    tier_counts = Counter()
    tier_cits = defaultdict(list)
    for r in rows:
        tier, _ = classify_publisher(r)
        tier_counts[tier] += 1
        cit = safe_int(r.get("Total_Sitasi", 0))
        tier_cits[tier].append(cit)
    data["distribusi_penerbit"] = dict(tier_counts.most_common())
    data["dampak_sitasi_penerbit"] = {
        tier: {"avg": round(sum(c)/len(c), 1), "n": len(c)}
        for tier, c in sorted(tier_cits.items(), key=lambda x: -sum(x[1])/len(x[1]))
        if len(c) >= 2
    }

    # 19. Theme × Method matrix
    theme_method_pairs = Counter()
    for r in rows:
        theme = _reclassify_theme(r)
        method = r.get("Metode_Penelitian", "").strip()
        if theme and method and method != "Tidak dinyatakan eksplisit":
            method_clean = method.split(";")[0].strip()
            theme_method_pairs[(theme, method_clean)] += 1
    data["tema_vs_metode"] = {
        f"{t} | {m}": v for (t, m), v in theme_method_pairs.most_common(30)
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Insights written to {out_path}")

if __name__ == "__main__":
    main()
