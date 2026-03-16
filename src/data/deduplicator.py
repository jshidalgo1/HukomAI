"""
deduplicator.py – Two-phase deduplication for the HukomAI Phase 0 pipeline.

Phase 1: Deterministic G.R. number family grouping.
Phase 2: Embedding-based near-duplicate detection using sentence-transformers + FAISS.
"""

import re
import os
import csv
import pandas as pd
from src.data.config import (
    INPUT_CSV, CORPUS_DIR, FAMILY_OUT, SIM_DEDUP_OUT,
    EMBEDDING_MODEL, EMBEDDING_BATCH, FACTS_SNIPPET_CHARS, SIM_THRESHOLD, FAISS_TOP_K
)


# ---------------------------------------------------------------------------
# PHASE 1 – G.R. NUMBER FAMILY GROUPING
# ---------------------------------------------------------------------------

# Matches: "G.R. No. 123456", "G.R. Nos. 123456-57", "A.M. No. P-01-1234", etc.
_GR_PATTERN = re.compile(
    r"(?:G\.?R\.|A\.?M\.|A\.?C\.|O\.?G\.?)\s*No[s]?\.\s*([\d\-–, ]+)",
    re.IGNORECASE
)


def _extract_gr_roots(case_no: str) -> list[str]:
    """
    Extract numeric G.R. roots from a case_no string.
    e.g. 'G.R. No. 123456-B' -> ['123456']
         'G.R. Nos. 100001, 100002' -> ['100001', '100002']
    Returns a list of strings (may be empty for non-standard identifiers).
    """
    matches = _GR_PATTERN.findall(str(case_no))
    roots = []
    for match in matches:
        # Split consolidated numbers (e.g. "100001, 100002" or "100001-02")
        parts = re.split(r"[,\s]+", match.strip())
        for part in parts:
            # Keep only leading digits (strip letter suffixes like '-B')
            num = re.match(r"\d+", part.strip())
            if num:
                roots.append(num.group(0))
    return roots


def run_gr_grouping(input_csv: str = INPUT_CSV, output_csv: str = FAMILY_OUT) -> pd.DataFrame:
    """
    Phase 1: Assign each case row a case_family_id based on G.R. number root.
    Consolidated appeals (multiple roots) resolve to the numerically lowest root.
    Outputs family_groups.csv and returns the grouped DataFrame.
    """
    print("=" * 50)
    print("PHASE 1 – G.R. Family Grouping")
    print("=" * 50)

    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"❌ Error: {input_csv} not found.")
        return pd.DataFrame()

    family_ids = []
    for _, row in df.iterrows():
        roots = _extract_gr_roots(str(row.get("case_no", "")))
        if roots:
            # Choose the numerically smallest root as canonical family ID
            canonical = min(roots, key=lambda x: int(x))
            family_ids.append(f"GR{canonical}")
        else:
            # Fallback: use sanitized case_no itself
            sanitized = re.sub(r"[^A-Za-z0-9]", "", str(row.get("case_no", "UNKNOWN")))
            family_ids.append(f"GR_{sanitized}")

    df["case_family_id"] = family_ids

    # Compute family sizes
    size_map = df["case_family_id"].value_counts().to_dict()
    df["family_size"] = df["case_family_id"].map(size_map)

    # Save
    out_df = df[["case_no", "case_family_id", "family_size"]]
    out_df.to_csv(output_csv, index=False)

    multi = (df["family_size"] > 1).sum()
    print(f"✅ {len(df)} cases processed → {df['case_family_id'].nunique()} unique families")
    print(f"   {multi} cases share a family with at least one other case")
    print(f"   Saved to: {output_csv}\n")

    return df


# ---------------------------------------------------------------------------
# PHASE 2 – EMBEDDING-BASED SIMILARITY DEDUPLICATION
# ---------------------------------------------------------------------------

def _load_facts_snippets(corpus_dir: str, snippet_chars: int) -> tuple[list[str], list[str]]:
    """
    Load facts snippets (first `snippet_chars` chars) from the corpus directory.
    Returns (case_ids, snippets) parallel lists.
    """
    case_ids, snippets = [], []
    for fname in os.listdir(corpus_dir):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(corpus_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract facts block
            if "========== FACTS ==========" in content:
                facts_raw = content.split("========== FACTS ==========")[1]
                # Strip everything from ISSUES or RULING onward
                for sep in ["========== ISSUES ==========", "========== RULING =========="]:
                    if sep in facts_raw:
                        facts_raw = facts_raw.split(sep)[0]
                snippet = facts_raw.strip()[:snippet_chars]
            else:
                snippet = content[:snippet_chars]
            case_ids.append(os.path.splitext(fname)[0])
            snippets.append(snippet)
        except Exception as e:
            print(f"  ⚠️  Skipping {fname}: {e}")
    return case_ids, snippets


def run_embedding_dedup(
    corpus_dir: str = CORPUS_DIR,
    output_csv: str = SIM_DEDUP_OUT,
    model_name: str = EMBEDDING_MODEL,
    batch_size: int = EMBEDDING_BATCH,
    snippet_chars: int = FACTS_SNIPPET_CHARS,
    threshold: float = SIM_THRESHOLD,
    top_k: int = FAISS_TOP_K,
) -> pd.DataFrame:
    """
    Phase 2: Embed facts snippets and use FAISS to find near-duplicate pairs
    with cosine similarity >= threshold. Flags only – does not delete files.
    Outputs sim_dedup_report.csv and returns the pairs DataFrame.
    """
    print("=" * 50)
    print("PHASE 2 – Embedding-Based Similarity Deduplication")
    print("=" * 50)

    # --- Lazy-import heavy dependencies so pipeline still runs without them ---
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError as e:
        print(f"⚠️  Skipping Phase 2 – missing dependency: {e}")
        print("   Install with: pip install sentence-transformers faiss-cpu")
        return pd.DataFrame()

    print(f"📦 Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"📂 Loading facts snippets from: {corpus_dir}")
    case_ids, snippets = _load_facts_snippets(corpus_dir, snippet_chars)
    n = len(snippets)
    print(f"   {n} documents loaded")

    if n == 0:
        print("❌ No documents found. Skipping.")
        return pd.DataFrame()

    # --- Encode in batches ---
    print(f"🔢 Encoding in batches of {batch_size}...")
    embeddings = model.encode(
        snippets,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-normalize for cosine via inner product
    )

    # --- Build FAISS index (IndexFlatIP = cosine similarity after L2-norm) ---
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype("float32"))

    # --- Query: find top-(k+1) neighbors for each doc (first result is self) ---
    k = min(top_k + 1, n)
    print(f"🔍 Searching for near-duplicates (threshold = {threshold})...")
    distances, indices = index.search(embeddings.astype("float32"), k)

    # --- Collect flagged pairs (deduplicated: only store (a,b) where a < b) ---
    seen = set()
    pairs = []
    for i in range(n):
        for j_rank in range(1, k):  # skip rank 0 (self)
            j = int(indices[i][j_rank])
            sim = float(distances[i][j_rank])
            if sim >= threshold:
                pair_key = (min(i, j), max(i, j))
                if pair_key not in seen:
                    seen.add(pair_key)
                    pairs.append({
                        "case_id_a": case_ids[pair_key[0]],
                        "case_id_b": case_ids[pair_key[1]],
                        "cosine_similarity": round(sim, 4),
                        "recommended_action": "review_and_assign_same_split",
                    })

    result_df = pd.DataFrame(pairs)
    if not result_df.empty:
        result_df = result_df.sort_values("cosine_similarity", ascending=False)
        result_df.to_csv(output_csv, index=False)
        print(f"\n✅ {len(result_df)} near-duplicate pairs found (sim ≥ {threshold})")
        print(f"   Saved to: {output_csv}")
    else:
        print(f"\n✅ No near-duplicate pairs found above threshold {threshold}")

    return result_df


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HukomAI Deduplicator (Phase 0)")
    parser.add_argument("--skip-embedding-dedup", action="store_true",
                        help="Skip Phase 2 embedding-based deduplication")
    parser.add_argument("--threshold", type=float, default=SIM_THRESHOLD,
                        help=f"Cosine similarity threshold (default: {SIM_THRESHOLD})")
    args = parser.parse_args()

    run_gr_grouping()

    if not args.skip_embedding_dedup:
        run_embedding_dedup(threshold=args.threshold)
    else:
        print("⏭️  Skipping Phase 2 (--skip-embedding-dedup flag set)")
