"""
pipeline.py – Phase 0 orchestrator for HukomAI data engineering.

Runs each Phase 0 step in sequence. Each step can be skipped via CLI flags.

Usage:
    python -m src.data.pipeline                          # full run
    python -m src.data.pipeline --skip-scrape            # skip scraping (use existing corpus)
    python -m src.data.pipeline --skip-embedding-dedup   # skip embedding-based dedup
    python -m src.data.pipeline --dry-run-leakage        # preview leakage guard without writing

Steps:
    1. scraper.run_scraper()
    2. auditor.check_files()
    3. fixer.fix_files()
    4. deduplicator.run_gr_grouping()
    5. deduplicator.run_embedding_dedup()   (skippable)
    6. leakage_guard.run()
    7. dataset_builder.build()
"""

import argparse
import time


def run_pipeline(
    skip_scrape: bool          = False,
    skip_audit_fix: bool       = False,
    skip_gr_grouping: bool     = False,
    skip_embedding_dedup: bool = False,
    skip_leakage: bool         = False,
    skip_build: bool           = False,
    dry_run_leakage: bool      = False,
    sim_threshold: float       = None,
) -> None:
    start = time.time()
    print("\n" + "=" * 60)
    print("  HukomAI – Phase 0 Pipeline")
    print("=" * 60 + "\n")

    # ── Step 1: Scrape ──────────────────────────────────────────
    if not skip_scrape:
        print("▶ Step 1/7 – Scraping corpus...")
        from src.data.scraper import run_scraper
        run_scraper()
    else:
        print("⏭  Step 1/7 – Skipped (--skip-scrape)")

    # ── Step 2+3: Audit + Fix ────────────────────────────────────
    if not skip_audit_fix:
        print("\n▶ Step 2/7 – Auditing corpus...")
        from src.data.auditor import check_files
        check_files()

        print("\n▶ Step 3/7 – Fixing flagged files...")
        from src.data.fixer import fix_files
        fix_files()
    else:
        print("⏭  Step 2-3/7 – Skipped (--skip-audit-fix)")

    # ── Step 4: G.R. Family Grouping ────────────────────────────
    if not skip_gr_grouping:
        print("\n▶ Step 4/7 – G.R. family grouping...")
        from src.data.deduplicator import run_gr_grouping
        run_gr_grouping()
    else:
        print("⏭  Step 4/7 – Skipped (--skip-gr-grouping)")

    # ── Step 5: Embedding-Based Dedup ───────────────────────────
    if not skip_embedding_dedup:
        print("\n▶ Step 5/7 – Embedding-based dedup...")
        from src.data.deduplicator import run_embedding_dedup
        kwargs = {}
        if sim_threshold is not None:
            kwargs["threshold"] = sim_threshold
        run_embedding_dedup(**kwargs)
    else:
        print("⏭  Step 5/7 – Skipped (--skip-embedding-dedup)")

    # ── Step 6: Leakage Guard ────────────────────────────────────
    if not skip_leakage:
        print("\n▶ Step 6/7 – Leakage guard...")
        from src.data.leakage_guard import run as run_leakage
        run_leakage(dry_run=dry_run_leakage)
    else:
        print("⏭  Step 6/7 – Skipped (--skip-leakage)")

    # ── Step 7: Dataset Build ────────────────────────────────────
    if not skip_build:
        print("\n▶ Step 7/7 – Building Phase 0 dataset CSV...")
        from src.data.dataset_builder import build
        build()
    else:
        print("⏭  Step 7/7 – Skipped (--skip-build)")

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  ✅ Phase 0 Pipeline Complete  [{elapsed:.1f}s]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HukomAI Phase 0 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--skip-scrape",          action="store_true", help="Skip Step 1 (scraping)")
    parser.add_argument("--skip-audit-fix",       action="store_true", help="Skip Steps 2-3 (audit + fix)")
    parser.add_argument("--skip-gr-grouping",     action="store_true", help="Skip Step 4 (G.R. grouping)")
    parser.add_argument("--skip-embedding-dedup", action="store_true", help="Skip Step 5 (embedding dedup)")
    parser.add_argument("--skip-leakage",         action="store_true", help="Skip Step 6 (leakage guard)")
    parser.add_argument("--skip-build",           action="store_true", help="Skip Step 7 (dataset build)")
    parser.add_argument("--dry-run-leakage",      action="store_true", help="Run leakage guard without writing files")
    parser.add_argument("--sim-threshold",        type=float,          help="Override cosine similarity threshold for embedding dedup")

    args = parser.parse_args()

    run_pipeline(
        skip_scrape          = args.skip_scrape,
        skip_audit_fix       = args.skip_audit_fix,
        skip_gr_grouping     = args.skip_gr_grouping,
        skip_embedding_dedup = args.skip_embedding_dedup,
        skip_leakage         = args.skip_leakage,
        skip_build           = args.skip_build,
        dry_run_leakage      = args.dry_run_leakage,
        sim_threshold        = args.sim_threshold,
    )
