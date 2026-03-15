import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import csv
from src.data.scraper import extract_sections  # Reuse scraper's core extraction logic

# --- CONFIGURATION ---
MASTER_CSV = "sc_decisions.csv"         # Source of URLs
INPUT_DIR = "hukom_corpus_friendly"     # Where files are saved
REPORT_FILE = "audit_report.csv"        # List of bad files to refetch
SLEEP_TIME = 0                          # Be polite to the server!


def refetch_files():
    # 1. Load the list of bad files from the Audit Report
    if not os.path.exists(REPORT_FILE):
        print(f"Report '{REPORT_FILE}' not found. Run auditor.py first.")
        return

    bad_filenames = set()
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bad_filenames.add(row['filename'])

    if not bad_filenames:
        print("Audit report is empty. Nothing to refetch.")
        return

    print(f"🎯 Targeted Refetch: {len(bad_filenames)} files marked for re-downloading...")

    # 2. Load the Master CSV to get the URLs
    try:
        df = pd.read_csv(MASTER_CSV)
    except FileNotFoundError:
        print(f"Error: {MASTER_CSV} not found.")
        return

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    success_count = 0
    fail_count = 0

    # 3. Loop through the Master CSV
    for index, row in df.iterrows():
        case_id = str(row['case_no']).replace("/", "_").replace(" ", "")
        filename = f"{case_id}.txt"

        # ONLY process if this file is in our "Bad List"
        if filename in bad_filenames:
            url = row['case_link'].replace("showdocs", "showdocsfriendly")
            save_path = f"{INPUT_DIR}/{filename}"

            print(f"🔄 Refetching: {filename}...")

            try:
                response = requests.get(url, headers=headers, timeout=20)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.extract()

                    text_content = soup.get_text()
                    sections = extract_sections(text_content)

                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(f"URL: {url}\n")
                        f.write(f"STATUS: {sections['status']} (REFETCHED)\n")
                        f.write("="*20 + " FACTS " + "="*20 + "\n")
                        f.write(sections['facts'] + "\n\n")
                        f.write("="*20 + " RULING " + "="*20 + "\n")
                        f.write(sections['ruling'] + "\n")

                    success_count += 1
                else:
                    print(f"❌ Failed to download (Status {response.status_code})")
                    fail_count += 1

            except Exception as e:
                print(f"❌ Error: {e}")
                fail_count += 1

            time.sleep(SLEEP_TIME)

    print("\n" + "=" * 40)
    print(f"REFETCH COMPLETE")
    print(f"✅ Refreshed: {success_count}")
    print(f"❌ Failed:    {fail_count}")
    print("=" * 40)
    print("Run auditor.py one last time to verify.")


if __name__ == "__main__":
    refetch_files()
