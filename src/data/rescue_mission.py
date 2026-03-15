import os
import csv
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from src.data.scraper import extract_sections  # Reuse scraper's core extraction logic

# --- CONFIGURATION ---
INPUT_DIR = "hukom_corpus_friendly"
MASTER_CSV = "sc_decisions.csv"
SLEEP_TIME = 0


def rescue_files():
    if not os.path.exists(INPUT_DIR):
        print("Directory not found.")
        return

    print("🔍 Scanning for locally 'Fixed' files that might be truncated...")

    files_to_rescue = []

    # 1. Identify files that were locally modified
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(INPUT_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                f.readline()           # Read first line (URL)
                status = f.readline()  # Read second line (STATUS)

                if "(FIXED)" in status:
                    files_to_rescue.append(filename)
        except Exception:
            continue

    if not files_to_rescue:
        print("✅ No locally fixed files found. Your dataset is likely consistent.")
        return

    print(f"🚨 Found {len(files_to_rescue)} files that were locally fixed.")
    print("   Starting fresh download to ensure no text is missing...")

    # 2. Load URLs
    df = pd.read_csv(MASTER_CSV)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # 3. Re-download them
    count = 0
    for filename in files_to_rescue:
        target_id = os.path.splitext(filename)[0]

        row = None
        for idx, r in df.iterrows():
            cid = str(r['case_no']).replace("/", "_").replace(" ", "")
            if cid == target_id:
                row = r
                break

        if row is not None:
            url = row['case_link'].replace("showdocs", "showdocsfriendly")
            save_path = os.path.join(INPUT_DIR, filename)

            print(f"[{count+1}/{len(files_to_rescue)}] 🔄 Refetching: {filename}...")

            try:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.extract()

                    sections = extract_sections(soup.get_text())

                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(f"URL: {url}\n")
                        f.write(f"STATUS: {sections['status']} (REFETCHED)\n")
                        f.write("="*20 + " FACTS " + "="*20 + "\n")
                        f.write(sections['facts'] + "\n\n")
                        f.write("="*20 + " RULING " + "="*20 + "\n")
                        f.write(sections['ruling'] + "\n")
                    count += 1
                else:
                    print(f"❌ Download failed for {filename}")
            except Exception as e:
                print(f"❌ Error downloading {filename}: {e}")

            time.sleep(SLEEP_TIME)
        else:
            print(f"⚠️ Could not find URL for {filename} in CSV")

    print("\n" + "="*30)
    print(f"Rescue Mission Complete. {count} files restored.")


if __name__ == "__main__":
    rescue_files()
