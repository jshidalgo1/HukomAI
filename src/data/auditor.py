import os
import re
import csv

# --- CONFIGURATION ---
INPUT_DIR = "hukom_corpus_friendly"
OUTPUT_REPORT = "audit_report.csv"  # The list of files to fix
CHECK_LIMIT = 500
FOOTER_LIMIT = 1000


def check_files():
    if not os.path.exists(INPUT_DIR):
        print(f"Directory '{INPUT_DIR}' not found.")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    print(f"Auditing {len(files)} files...\n")

    clean_count = 0
    problematic_files = []  # Store tuples: (filename, issue_type)

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                content = "".join(lines)

            issues = []

            # --- CHECK 1: STATUS CHECK ---
            status_line = lines[1] if len(lines) > 1 and "STATUS:" in lines[1] else ""
            if not status_line:
                status_line = lines[0] if "STATUS:" in lines[0] else ""

            if "SPLIT_SUCCESS" not in status_line:
                issues.append("BAD_SPLIT")

            # --- ISOLATE FACTS ---
            if "========== FACTS ==========" in content:
                parts = content.split("========== FACTS ==========")
                if "========== RULING ==========" in parts[1]:
                    raw_facts = parts[1].split("========== RULING ==========")[0].strip()
                else:
                    raw_facts = parts[1].strip()
            else:
                raw_facts = content[:CHECK_LIMIT]

            # --- CHECK 2: HEADER RESIDUE ---
            start_snippet = raw_facts[:CHECK_LIMIT]
            if re.search(r"(PER\s+CURIAM)", start_snippet, re.IGNORECASE):
                issues.append("HEADER_RESIDUE")

            # --- CHECK 3: CAPS LOCK HEADER ---
            clean_snippet = re.sub(r"[^a-zA-Z]", "", start_snippet)
            if len(clean_snippet) > 10:
                upper_ratio = sum(1 for c in clean_snippet if c.isupper()) / len(clean_snippet)
                if upper_ratio > 0.80:
                    issues.append("CAPS_LOCK_HEADER")

            # --- CHECK 4: CITATION RESIDUE ---
            if re.search(r"\[\s*\d+\s*\]", raw_facts):
                issues.append("CITATION_RESIDUE")

            # --- CHECK 5: FOOTER RESIDUE ---
            end_snippet = content[-FOOTER_LIMIT:]
            if re.search(r"(Source:\s*Supreme Court E-Library|Content Management System)", end_snippet, re.IGNORECASE):
                issues.append("FOOTER_RESIDUE")

            # --- REPORTING ---
            if issues:
                issue_str = ";".join(issues)
                problematic_files.append([filename, issue_str])
                print(f"FLAGS in {filename}: {issue_str}")
            else:
                clean_count += 1

        except Exception as e:
            print(f"[ERROR] Could not read {filename}: {e}")

    # --- SAVE TO CSV ---
    if problematic_files:
        with open(OUTPUT_REPORT, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["filename", "issues"])
            writer.writerows(problematic_files)
        print(f"\n📝 Saved {len(problematic_files)} problematic files to '{OUTPUT_REPORT}'")

    print("\n" + "=" * 40)
    print(f"AUDIT RESULTS")
    print(f"✅ Clean Files:       {clean_count}")
    print(f"❌ Problematic Files: {len(problematic_files)}")
    print("=" * 40)


if __name__ == "__main__":
    check_files()
