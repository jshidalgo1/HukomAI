"""
config.py – Shared path constants and configuration for the HukomAI Phase 0 pipeline.

All data scripts should import from here rather than hardcoding paths locally.
"""

# --- INPUT ---
INPUT_CSV = "sc_decisions.csv"         # Master list of SC decisions with URLs

# --- CORPUS DIRECTORIES ---
CORPUS_DIR = "hukom_corpus_friendly"   # Clean, scraped .txt files (facts + issues + ruling)
QUARANTINE  = "hukom_quarantine"       # Bad files moved here by archiver.py

# --- AUDIT ---
AUDIT_FILE = "audit_report.csv"        # Output of auditor.py – flagged files

# --- DEDUPLICATION ---
FAMILY_OUT    = "family_groups.csv"    # G.R. number family groupings
SIM_DEDUP_OUT = "sim_dedup_report.csv" # Embedding-based near-duplicate pairs

# --- FINAL DATASET ---
DATASET_OUT = "hukom_phase0_dataset.csv"  # Canonical Phase 0 structured CSV

# --- EMBEDDING DEDUP SETTINGS ---
EMBEDDING_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_BATCH     = 512    # Docs per encoding batch
FACTS_SNIPPET_CHARS = 512    # Chars of facts to embed per case
SIM_THRESHOLD       = 0.92   # Cosine similarity cutoff for near-duplicate flagging
FAISS_TOP_K         = 5      # Nearest neighbors to retrieve per document (excl. self)

# --- LEAKAGE GUARD ---
LEAKAGE_KEYWORDS = [
    r"\baff?irm(?:ed|s|ing)?\b",
    r"\brevers(?:ed|es|ing|al)?\b",
    r"\bmodif(?:ied|ies|ication|ying)?\b",
    r"\bdismiss(?:ed|es|ing|al)?\b",
    r"\bacquit(?:ted|s|ting|tal)?\b",
    r"\bconvict(?:ed|s|ing|ion)?\b",
    r"\bgranted\b",
    r"\bdenied\b",
    r"\bset\s+aside\b",
    r"\breinstated?\b",
    r"\bnullif(?:ied|ies|ication)?\b",
    r"\bannull(?:ed|ment|ing)?\b",
    r"\bremand(?:ed|ing|s)?\b",
    r"\bmoot(?:ed)?\b",
]
