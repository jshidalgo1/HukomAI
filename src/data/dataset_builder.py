"""
dataset_builder.py – Builds the canonical Phase 0 structured CSV (hukom_phase0_dataset.csv).

Reads the cleaned corpus, merges metadata from sc_decisions.csv,
applies case_family_id from family_groups.csv, marks near-duplicates
from sim_dedup_report.csv, and exports one row per case.

Output schema:
  case_id, year, case_title, facts, issues, ruling,
  case_family_id, family_size, is_near_duplicate, split_status
"""

import os
import re
import pandas as pd
from src.data.config import (
    INPUT_CSV, CORPUS_DIR, FAMILY_OUT, SIM_DEDUP_OUT, DATASET_OUT
)

# Corpus separators (must match scraper.py)
SEP_FACTS  = "========== FACTS =========="
SEP_ISSUES = "========== ISSUES =========="
SEP_RULING = "========== RULING =========="


def _parse_corpus_file(content: str) -> dict:
    """Extract facts, issues, ruling and split_status from a corpus file."""
    lines = content.split("\n", 2)
    status_line = ""
    for line in lines[:3]:
        if line.startswith("STATUS:"):
            status_line = line.replace("STATUS:", "").strip()
            break

    facts = issues = ruling = ""

    if SEP_FACTS in content:
        after_facts = content.split(SEP_FACTS, 1)[1]
        if SEP_RULING in after_facts:
            if SEP_ISSUES in after_facts:
                facts_issues, ruling = after_facts.split(SEP_RULING, 1)
                facts, issues = facts_issues.split(SEP_ISSUES, 1)
            else:
                facts, ruling = after_facts.split(SEP_RULING, 1)
        else:
            facts = after_facts

    return {
        "facts":        facts.strip(),
        "issues":       issues.strip(),
        "ruling":       ruling.strip(),
        "split_status": status_line,
    }


def build(
    input_csv: str   = INPUT_CSV,
    corpus_dir: str  = CORPUS_DIR,
    family_csv: str  = FAMILY_OUT,
    sim_csv: str     = SIM_DEDUP_OUT,
    output_csv: str  = DATASET_OUT,
) -> pd.DataFrame:
    """
    Build the Phase 0 dataset CSV.
    Returns the final DataFrame.
    """
    print("=" * 50)
    print("DATASET BUILDER")
    print("=" * 50)

    # --- 1. Load master metadata CSV ---
    try:
        meta_df = pd.read_csv(input_csv)
        # Normalise column names to lowercase
        meta_df.columns = [c.strip().lower() for c in meta_df.columns]
        print(f"✅ Loaded metadata: {len(meta_df)} rows from {input_csv}")
    except FileNotFoundError:
        print(f"❌ {input_csv} not found. Metadata columns will be empty.")
        meta_df = pd.DataFrame()

    # Build a lookup: case_id -> meta row
    meta_lookup = {}
    if not meta_df.empty:
        for _, row in meta_df.iterrows():
            raw_id = str(row.get("case_no", ""))
            canon  = raw_id.replace("/", "_").replace(" ", "")
            meta_lookup[canon] = row

    # --- 2. Load family groups ---
    family_lookup = {}    # case_no -> {case_family_id, family_size}
    if os.path.exists(family_csv):
        fam_df = pd.read_csv(family_csv)
        for _, row in fam_df.iterrows():
            canon = str(row["case_no"]).replace("/", "_").replace(" ", "")
            family_lookup[canon] = {
                "case_family_id": row["case_family_id"],
                "family_size":    row["family_size"],
            }
        print(f"✅ Loaded family groups: {len(fam_df)} rows from {family_csv}")
    else:
        print(f"⚠️  {family_csv} not found — run deduplicator.py first")

    # --- 3. Load near-duplicate flags ---
    near_dup_ids = set()
    if os.path.exists(sim_csv):
        sim_df = pd.read_csv(sim_csv)
        near_dup_ids = set(sim_df["case_id_a"]) | set(sim_df["case_id_b"])
        print(f"✅ Loaded near-duplicate report: {len(near_dup_ids)} flagged cases from {sim_csv}")
    else:
        print(f"ℹ️  {sim_csv} not found — is_near_duplicate will default to False")

    # --- 4. Read corpus files ---
    files = [f for f in os.listdir(corpus_dir) if f.endswith(".txt")]
    print(f"\n📂 Reading {len(files)} corpus files from {corpus_dir}...")

    rows = []
    for fname in files:
        case_id = os.path.splitext(fname)[0]
        fpath   = os.path.join(corpus_dir, fname)

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"  ⚠️  Could not read {fname}: {e}")
            continue

        parsed = _parse_corpus_file(content)
        meta   = meta_lookup.get(case_id, {})
        family = family_lookup.get(case_id, {"case_family_id": None, "family_size": None})

        # Parse year from date field or case_no
        year = None
        raw_date = str(meta.get("date", "") if hasattr(meta, "get") else "")
        year_match = re.search(r"\b(19|20)\d{2}\b", raw_date)
        if year_match:
            year = int(year_match.group(0))

        rows.append({
            "case_id":          case_id,
            "year":             year,
            "case_title":       meta.get("case_title", "") if hasattr(meta, "get") else "",
            "facts":            parsed["facts"],
            "issues":           parsed["issues"],
            "ruling":           parsed["ruling"],
            "case_family_id":   family["case_family_id"],
            "family_size":      family["family_size"],
            "is_near_duplicate": case_id in near_dup_ids,
            "split_status":     parsed["split_status"],
        })

    # --- 5. Build and save DataFrame ---
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Dataset built: {len(df)} rows")
    print(f"   Issues found:        {(df['issues'] != '').sum()} / {len(df)}")
    print(f"   Near-duplicates:     {df['is_near_duplicate'].sum()}")
    print(f"   Missing case_family: {df['case_family_id'].isna().sum()}")
    print(f"   Saved to: {output_csv}")

    return df


if __name__ == "__main__":
    build()
