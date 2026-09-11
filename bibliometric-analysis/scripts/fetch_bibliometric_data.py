#!/usr/bin/env python3
"""
fetch_bibliometric_data.py
--------------------------
Fetch real papers on digital activism in Indonesia from OpenAlex API
and export as a bibliometric coding sheet (CSV), following the
lembar koding defined in:
  Draft 3 - Digital Activism (Revised).md

Output: lembar_koding_bibliometrika.csv (same directory)

Usage:
  python3 fetch_bibliometric_data.py
"""

import urllib.request
import urllib.parse
import json
import csv
import time
import datetime
import sys
import argparse
import os

# ─── Config ──────────────────────────────────────────────────────────────────

OUTPUT_PATH = "lembar_koding_bibliometrika.csv"

BASE_URL = "https://api.openalex.org/works"

# OpenAlex polite pool header — append your contact via --email
HEADERS = {
    "User-Agent": "bibliometric-research/1.0"
}

# Search queries (Indonesian digital activism, 2010–2025)
QUERIES = [
    '"digital activism" AND ("Indonesia" OR "Indonesian")',
    '"online activism" AND ("Indonesia" OR "Indonesian")',
    '"hashtag activism" AND ("Indonesia" OR "Indonesian")',
    '"connective action" AND ("Indonesia" OR "Indonesian")',
    '"digital protest" AND ("Indonesia" OR "Indonesian")',
    '"social media activism" AND ("Indonesia" OR "Indonesian")',
    '"aktivisme digital" AND "Indonesia"',
    '"gerakan sosial" AND "media sosial" AND "Indonesia"',
]

PER_PAGE   = 100  # OpenAlex allows up to 200 per page
MAX_PAGES  = 10   # per query
MAX_ROWS   = 500  # final rows in CSV (sorted by citation count)
SLEEP_SEC  = 0.25 # polite delay between requests

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_abstract(inverted_index: dict) -> str:
    """Reconstructs the abstract from OpenAlex's abstract_inverted_index."""
    if not inverted_index:
        return ""
    try:
        word_index = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_index.append((pos, word))
        word_index.sort(key=lambda x: x[0])
        return " ".join([w[1] for w in word_index])
    except Exception:
        return ""


def fetch_works(query: str, per_page: int, max_pages: int) -> list:
    works = []
    for page in range(1, max_pages + 1):
        params = urllib.parse.urlencode({
            "search":  query,
            "filter":  "from_publication_date:2010-01-01,type:article,has_abstract:true",
            "per-page": per_page,
            "page":    page,
            "select":  (
                "id,doi,title,authorships,publication_year,"
                "primary_location,biblio,cited_by_count,"
                "keywords,concepts,language,abstract_inverted_index,referenced_works"
            ),
        })
        url = f"{BASE_URL}?{params}"
        retry = 0
        success = False
        while retry < 4:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data   = json.loads(resp.read().decode())
                    batch  = data.get("results", [])
                    works.extend(batch)
                    print(f"    page {page}: {len(batch)} results  (total so far: {len(works)})")
                    success = True
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry += 1
                    wait_time = (2 ** retry) + 2
                    print(f"    ⚠️  HTTP 429 Too Many Requests on page {page}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"    ⚠️  HTTP Error on page {page}: {e}")
                    break
            except Exception as exc:
                print(f"    ⚠️  Error on page {page}: {exc}")
                break
                
        if not success:
            break
            
        if len(batch) < per_page:
            break
        time.sleep(SLEEP_SEC)
    return works


def fmt_authors(authorships: list) -> str:
    names = []
    for a in authorships[:4]:
        raw = a.get("author", {}).get("display_name", "")
        if raw:
            parts = raw.strip().split()
            if len(parts) >= 2:
                raw = f"{parts[-1]}, {' '.join(parts[:-1])}"
            names.append(raw)
    if len(authorships) > 4:
        names.append("et al.")
    return "; ".join(names)


def first_affiliation(authorships: list) -> tuple:
    """Returns (institution_name, country_code)."""
    for a in authorships:
        for inst in a.get("institutions", []):
            name = inst.get("display_name", "")
            cc   = inst.get("country_code", "")
            if name or cc:
                return name, cc
    return "", ""


def collaboration_type(authorships: list) -> tuple:
    n = len(authorships)
    countries = set()
    for a in authorships:
        for inst in a.get("institutions", []):
            cc = inst.get("country_code", "")
            if cc:
                countries.add(cc)
    
    collab = ""
    if n == 1:
        collab = "Tunggal"
    elif not countries:
        collab = "Multi-penulis (afiliasi tidak diketahui)"
    elif len(countries) > 1:
        collab = "Multi-negara"
    else:
        collab = "Satu-negara"
        
    return collab, ";".join(list(countries))


def fmt_journal(primary_location: dict) -> str:
    if not primary_location:
        return ""
    src = primary_location.get("source") or {}
    return src.get("display_name", "")


def fmt_biblio(biblio: dict) -> str:
    if not biblio:
        return ""
    vol   = biblio.get("volume", "")
    issue = biblio.get("issue", "")
    fp    = biblio.get("first_page", "")
    lp    = biblio.get("last_page", "")
    vi    = f"{vol}({issue})" if vol and issue else vol
    pages = f"{fp}–{lp}" if fp and lp else fp
    parts = [p for p in [vi, pages] if p]
    return ", ".join(parts)


def cite_per_year(cited: int, pub_year: int) -> float:
    current = datetime.datetime.now().year
    years   = max(current - pub_year, 1)
    return round(cited / years, 1)


def extract_keywords(work: dict) -> tuple:
    """Returns (author_keywords_str, index_keywords_str)."""
    kws     = work.get("keywords", [])
    auth_kw = "; ".join(k.get("display_name", "") for k in kws[:6])
    concepts   = work.get("concepts", [])
    index_kw   = "; ".join(
        c.get("display_name", "")
        for c in concepts
        if c.get("level", 9) in (1, 2)
    )[:200]
    return auth_kw, index_kw


# ── Inferred fields from title + concepts ───────────────────────────────────

def infer_theme(title: str, concepts: list) -> tuple:
    level_1 = [c.get("display_name", "") for c in concepts if c.get("level") == 1]
    level_2 = [c.get("display_name", "") for c in concepts if c.get("level") == 2]
    
    tema = level_2[0] if level_2 else (level_1[0] if level_1 else "Unspecified Theme")
    subfield = level_1[0] if level_1 else "Unspecified Subfield"
    
    return tema, subfield


def infer_theory(title: str, concepts: list) -> str:
    level_3 = [c.get("display_name", "") for c in concepts if c.get("level") == 3]
    return level_3[0] if level_3 else "Unspecified Theory"


def infer_method(title: str, concepts: list) -> str:
    method_keywords = [
        "analysis", "method", "model", "algorithm", "technique", 
        "approach", "framework", "survey", "experiment", "study", 
        "evaluation", "review", "mapping", "mining", "network", "simulation"
    ]
    
    extracted = []
    for c in concepts:
        name = c.get("display_name", "")
        if any(kw in name.lower() for kw in method_keywords):
            extracted.append(name)
            
    if extracted:
        # Return top 2 method-like concepts
        return "; ".join(extracted[:2])
        
    return "Tidak dinyatakan eksplisit"


def infer_platform(title: str) -> str:
    t = (title or "").lower()
    platforms = []
    if any(w in t for w in ["twitter", "tweet", "x.com"]):
        platforms.append("Twitter/X")
    if "facebook" in t:
        platforms.append("Facebook")
    if "instagram" in t:
        platforms.append("Instagram")
    if "youtube" in t:
        platforms.append("YouTube")
    if "tiktok" in t:
        platforms.append("TikTok")
    if any(w in t for w in ["whatsapp", "telegram", "line"]):
        platforms.append("WhatsApp/Telegram/Line")
    if any(w in t for w in ["reddit", "discord"]):
        platforms.append("Reddit/Discord")
    return "; ".join(platforms) if platforms else "Tidak spesifik / multi-platform"


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch bibliometric data from OpenAlex.")
    parser.add_argument("--keywords", nargs="+", help="List of queries/keywords to search for.")
    parser.add_argument("--skip-filtering", action="store_true", help="Skip the Indonesia relevance filtering.")
    parser.add_argument("--email", help="Contact email for the OpenAlex polite pool (recommended).")
    parser.add_argument("--out-dir", default=".", help="Output directory.")
    args = parser.parse_args()

    if args.email:
        HEADERS["User-Agent"] += f" (mailto:{args.email})"

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, OUTPUT_PATH)

    queries_to_run = args.keywords if args.keywords else QUERIES

    print("=" * 60)
    print("  Bibliometric Coding Sheet Builder")
    print("  Source: OpenAlex API")
    print("=" * 60)
    if not args.email:
        print("  ℹ️  Pass --email <you@example.com> to join the OpenAlex polite pool.\n")

    all_works: list = []
    seen_ids: set   = set()

    for q in queries_to_run:
        print(f"\n🔍 Query: {q[:70]}...")
        batch = fetch_works(q, PER_PAGE, MAX_PAGES)
        added = 0
        for w in batch:
            wid = w.get("id", "")
            if wid and wid not in seen_ids:
                seen_ids.add(wid)
                all_works.append(w)
                added += 1
        print(f"   ✔  {added} new unique works  |  corpus: {len(all_works)}")

    # Sort: highest citation count first, then newest
    all_works.sort(
        key=lambda x: (-(x.get("cited_by_count") or 0),
                        -(x.get("publication_year") or 0))
    )

    print(f"\n📊 Building coding sheet (top {min(MAX_ROWS, len(all_works))} works)...")

    rows    = []
    skipped = 0

    for work in all_works:
        if len(rows) >= MAX_ROWS:
            break
        title = (work.get("title") or "").strip()
        if not title:
            skipped += 1
            continue
            
        abstract = get_abstract(work.get("abstract_inverted_index"))
        auth_kw, idx_kw = extract_keywords(work)
        
        i = len(rows) + 1

        year     = work.get("publication_year") or 0
        doi      = (work.get("doi") or "").replace("https://doi.org/", "").strip()
        lang     = work.get("language") or "en"
        lang_lbl = "Indonesia" if lang == "id" else "Inggris"
        cited    = work.get("cited_by_count") or 0
        concepts = work.get("concepts", [])

        authors  = fmt_authors(work.get("authorships", []))
        journal  = fmt_journal(work.get("primary_location") or {})
        biblio   = fmt_biblio(work.get("biblio") or {})
        aff, cc  = first_affiliation(work.get("authorships", []))
        origin   = cc if cc else "Tidak diketahui"
        collab, all_cc = collaboration_type(work.get("authorships", []))
        cpy      = cite_per_year(cited, year) if year else 0

        tema, subfield  = infer_theme(title, concepts)
        theory          = infer_theory(title, concepts)
        method          = infer_method(title, concepts)
        platform        = infer_platform(title)
        ref_works       = ";".join([ref.replace("https://openalex.org/", "") for ref in work.get("referenced_works", [])])

        rows.append({
            "Kode_Dokumen":             f"D{i:03d}",
            "Judul":                    title,
            "Penulis":                  authors,
            "Tahun_Terbit":             year,
            "Nama_Jurnal_Prosiding":    journal,
            "Volume_Halaman":           biblio,
            "DOI":                      doi,
            "Bahasa":                   lang_lbl,
            "Basis_Data_Sumber":        "OpenAlex",
            "Afiliasi_Penulis_Pertama": aff,
            "Negara_Afiliasi":          cc,
            "Semua_Negara_Afiliasi":    all_cc,
            "Asal_Peneliti":            origin,
            "Kolaborasi":               collab,
            "Total_Sitasi":             cited,
            "Cite_per_Year":            cpy,
            "Author_Keywords":          auth_kw,
            "Index_Keywords":           idx_kw,
            "Tema_Utama":               tema,
            "Subfield":                 subfield,
            "Teori_Kerangka":           theory,
            "Metode_Penelitian":        method,
            "Platform_yang_Dikaji":     platform,
            "Kriteria_Inklusi":         "Dimasukkan",
            "Alasan_Eksklusi":          "",
            "Referenced_Works":         ref_works,
            "Abstrak":                  abstract,
        })

    if not rows:
        print("❌ No data to write. Check your internet connection.")
        sys.exit(1)

    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Done!")
    print(f"   Output  : {out_path}")
    print(f"   Rows    : {len(rows)}  (skipped {skipped} empty-title works)")
    print(f"   Columns : {len(fieldnames)}")
    print("\n📋 Top 5 by citation count:")
    for r in rows[:5]:
        print(f"  {r['Kode_Dokumen']} | {r['Judul'][:55]:<55} | {r['Tahun_Terbit']} | ⭐ {r['Total_Sitasi']}")


if __name__ == "__main__":
    main()
