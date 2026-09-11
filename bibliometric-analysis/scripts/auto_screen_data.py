import csv
import re
from collections import Counter
import sys
import argparse
import os

INPUT_FILE = "lembar_koding_bibliometrika.csv"
OUTPUT_FILE = "lembar_koding_bibliometrika_screened.csv"


def main():
    parser = argparse.ArgumentParser(description="Auto-screen bibliometric data.")
    parser.add_argument("--skip-filtering", action="store_true", help="Skip the Indonesia relevance filtering.")
    parser.add_argument("--out-dir", default=".", help="Output directory.")
    args = parser.parse_args()

    in_path = os.path.join(args.out_dir, INPUT_FILE)

    print("Mulai proses auto-screening...")
    with open(in_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    screened_out = 0
    seen_titles = set()

    for row in rows:
        title_raw = row["Judul"]
        title = title_raw.lower()
        abstract = row.get("Abstrak", "").lower()
        
        # Default is included
        row["Kriteria_Inklusi"] = "Dimasukkan"
        row["Alasan_Eksklusi"] = ""

        # 1. Check for Duplicates
        title_clean = re.sub(r'[^a-z0-9]', '', title)
        if title_clean in seen_titles:
            row["Kriteria_Inklusi"] = "Dieksklusi"
            row["Alasan_Eksklusi"] = "Duplikasi"
            screened_out += 1
            continue
        seen_titles.add(title_clean)

        # 2. Check if abstract is too short
        words = abstract.split()
        if len(words) < 30:
            row["Kriteria_Inklusi"] = "Dieksklusi"
            row["Alasan_Eksklusi"] = "Abstrak tidak memadai / Bukan artikel penuh"
            screened_out += 1
            continue


    # Overwrite the original file for convenience, or save as new
    # Let's save as the same file to keep things clean
    # or save as screened output
    out_path = os.path.join(args.out_dir, INPUT_FILE)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nFile CSV telah diperbarui: {out_path}")
    print("=" * 50)
    print("SCREENING SELESAI")
    print("=" * 50)
    print(f"Total Dokumen       : {len(rows)}")
    print(f"Dimasukkan (Valid)  : {len(rows) - screened_out}")
    print(f"Dieksklusi          : {screened_out}")
    print("\nAlasan Eksklusi Breakdown:")
    
    reasons = [r["Alasan_Eksklusi"] for r in rows if r["Kriteria_Inklusi"] == "Dieksklusi"]
    reason_counts = Counter(reasons)
    for reason, count in reason_counts.items():
        print(f" - {reason}: {count} artikel")
    
    print(f"\nFile CSV telah diperbarui: {out_path}")

if __name__ == "__main__":
    main()
