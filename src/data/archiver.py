import os
import csv
import shutil
from src.data.config import CORPUS_DIR, QUARANTINE, AUDIT_FILE

# --- CONFIGURATION ---
INPUT_DIR        = CORPUS_DIR
ARCHIVE_DIR      = QUARANTINE
REPORT_FILE      = AUDIT_FILE
SAFETY_THRESHOLD = 2000


def archive_bad_files():
    if not os.path.exists(REPORT_FILE):
        print(f"Report '{REPORT_FILE}' not found. Run auditor.py first.")
        return

    # 1. Load the list of bad files
    files_to_move = []
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            files_to_move.append(row['filename'])

    count = len(files_to_move)
    print(f"📦 Found {count} flagged files to archive.")

    # 2. Safety Check
    if count > SAFETY_THRESHOLD:
        print(f"🛑 SAFETY LOCK ENGAGED!")
        print(f"   You are trying to move {count} files. Check your audit report first.")
        return

    if count == 0:
        print("✅ No files to archive. Your dataset is clean!")
        return

    # 3. Create Archive Directory
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        print(f"Created directory: {ARCHIVE_DIR}")

    # 4. Execute Move
    moved_count = 0
    missing_count = 0

    for filename in files_to_move:
        src_path = os.path.join(INPUT_DIR, filename)
        dst_path = os.path.join(ARCHIVE_DIR, filename)

        if os.path.exists(src_path):
            try:
                shutil.move(src_path, dst_path)
                moved_count += 1
            except Exception as e:
                print(f"Error moving {filename}: {e}")
        else:
            missing_count += 1

    print("-" * 40)
    print(f"📦 Archive Complete.")
    print(f"   Moved:   {moved_count} files to '{ARCHIVE_DIR}/'")
    print(f"   Missing: {missing_count} (Already deleted or moved)")

    remaining = len([f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")])
    print(f"✅ Main Dataset Size: {remaining} clean files.")


if __name__ == "__main__":
    archive_bad_files()
