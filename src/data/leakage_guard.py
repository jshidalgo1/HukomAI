"""
leakage_guard.py – Scrubs verdict-cue keywords from the 'facts' section
of each corpus file to prevent the model from memorising outcome signals.

Only the FACTS block is modified. ISSUES and RULING are left intact.
"""

import os
import re
from src.data.config import CORPUS_DIR, LEAKAGE_KEYWORDS

# Separator constants (must match scraper.py output format)
SEP_FACTS  = "========== FACTS =========="
SEP_ISSUES = "========== ISSUES =========="
SEP_RULING = "========== RULING =========="


def _scrub_facts(facts_text: str) -> tuple[str, int]:
    """
    Replace all leakage-keyword occurrences with [REDACTED].
    Returns (scrubbed_text, count_of_replacements).
    """
    count = 0

    def _replacer(match):
        nonlocal count
        count += 1
        return "[REDACTED]"

    scrubbed = facts_text
    for pattern in LEAKAGE_KEYWORDS:
        scrubbed = re.sub(pattern, _replacer, scrubbed, flags=re.IGNORECASE)

    return scrubbed, count


def _parse_file(content: str) -> dict:
    """
    Parse a corpus .txt file into its constituent blocks.
    Returns a dict with keys: header, facts, issues, ruling, has_issues.
    """
    result = {
        "header": "",
        "facts": "",
        "issues": "",
        "ruling": "",
        "has_issues": False,
    }

    if SEP_FACTS not in content:
        result["header"] = content
        return result

    parts = content.split(SEP_FACTS, 1)
    result["header"] = parts[0]
    remainder = parts[1]

    if SEP_RULING in remainder:
        if SEP_ISSUES in remainder:
            result["has_issues"] = True
            facts_and_issues, ruling_part = remainder.split(SEP_RULING, 1)
            facts_part, issues_part = facts_and_issues.split(SEP_ISSUES, 1)
            result["facts"] = facts_part
            result["issues"] = issues_part
        else:
            facts_part, ruling_part = remainder.split(SEP_RULING, 1)
            result["facts"] = facts_part
        result["ruling"] = ruling_part
    else:
        result["facts"] = remainder

    return result


def _rebuild_file(parsed: dict, scrubbed_facts: str) -> str:
    """Re-assemble the file content with the scrubbed facts block."""
    out = parsed["header"]
    out += SEP_FACTS + "\n"
    out += scrubbed_facts

    if parsed["has_issues"]:
        out += SEP_ISSUES + "\n"
        out += parsed["issues"]

    out += SEP_RULING + "\n"
    out += parsed["ruling"]
    return out


def run(corpus_dir: str = CORPUS_DIR, dry_run: bool = False) -> dict:
    """
    Apply leakage scrubbing to all corpus files.

    Args:
        corpus_dir: Path to the corpus directory.
        dry_run: If True, report what would be changed without writing files.

    Returns:
        Summary dict with total_files, modified_files, total_redactions.
    """
    print("=" * 50)
    print("LEAKAGE GUARD")
    print("=" * 50)
    if dry_run:
        print("ℹ️  DRY RUN MODE — no files will be written\n")

    if not os.path.exists(corpus_dir):
        print(f"❌ Directory '{corpus_dir}' not found.")
        return {}

    files = [f for f in os.listdir(corpus_dir) if f.endswith(".txt")]
    total_redactions = 0
    modified_count = 0

    for fname in files:
        fpath = os.path.join(corpus_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            parsed = _parse_file(content)
            scrubbed_facts, n_replaced = _scrub_facts(parsed["facts"])

            if n_replaced > 0:
                modified_count += 1
                total_redactions += n_replaced

                if not dry_run:
                    # Tag the STATUS line so we know this file was processed
                    header_updated = re.sub(
                        r"(STATUS:.*)",
                        r"\1 (LEAKAGE_GUARD_APPLIED)",
                        parsed["header"],
                        count=1,
                    )
                    parsed["header"] = header_updated
                    new_content = _rebuild_file(parsed, scrubbed_facts)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)

                print(f"  🛡️  {fname}: {n_replaced} keyword(s) redacted")

        except Exception as e:
            print(f"  ⚠️  Error processing {fname}: {e}")

    print("\n" + "=" * 50)
    print("LEAKAGE GUARD RESULTS")
    print(f"  📁 Files scanned:    {len(files)}")
    print(f"  ✏️  Files modified:   {modified_count}")
    print(f"  🔒 Total redactions: {total_redactions}")
    if dry_run:
        print("  ℹ️  No files written (dry run)")
    print("=" * 50)

    return {
        "total_files": len(files),
        "modified_files": modified_count,
        "total_redactions": total_redactions,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HukomAI Leakage Guard (Phase 0)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report changes without writing files")
    parser.add_argument("--corpus-dir", default=CORPUS_DIR,
                        help=f"Corpus directory (default: {CORPUS_DIR})")
    args = parser.parse_args()

    run(corpus_dir=args.corpus_dir, dry_run=args.dry_run)
