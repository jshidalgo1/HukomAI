import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import os
from src.data.config import INPUT_CSV, CORPUS_DIR

# --- CONFIGURATION ---
OUTPUT_DIR = CORPUS_DIR
SLEEP_TIME = 0
MAX_SCRAPE_LIMIT = None  # Stop after scraping this many files (set to None for unlimited)


if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def clean_text(text):
    """
    CONTEXT-AWARE CLEANER:
    1. Removes Unicode spaces & Citations.
    2. Removes E-Library garbage.
    3. HEADER REMOVAL (Regex): Targets Justice Names first.
    4. HEADER REMOVAL (Colon): Only cuts if the header is UPPERCASE.
    """
    # 1. Normalize spaces
    text = text.replace(u'\xa0', u' ')

    # 2. Remove Citations [1]
    text = re.sub(r"\[\s*\d+\s*\]", "", text)

    # 3. Remove E-Library Garbage
    text = re.sub(r"E-Library.*?Printer Friendly(\s+\d+\s+\w+\.?\s+\d+)?", "", text, flags=re.IGNORECASE)

    # 4. REGEX HEADER REMOVAL (The Guillotine)
    # Finds "J.:" or "PER CURIAM:"
    header_pattern = (
        r"(?s)^.*?"
        r"(?:"
          r"\bPER\s+CURIAM|"
          r"\b[A-Z\s\.\-Ññ]+,?\s*"
          r"(?:C\.?J|J|JJ|P\.?J|J\.?P)"
        r")"
        r"\s*[:\.]"
    )
    # Scan deep (15k chars) to catch long title lists
    match = re.search(header_pattern, text[:40000], re.IGNORECASE)
    if match:
        text = text[match.end():]

    else:
        # 5. FALLBACK: THE UPPERCASE COLON CHECK
        # Finds the first colon in the first 500 characters
        first_colon_index = text.find(':')

        if first_colon_index != -1 and first_colon_index < 500:
            # Grab the text BEFORE the colon
            pre_text = text[:first_colon_index].strip()

            # CHECK: Is it mostly UPPERCASE? (Allowing for some noise)
            # Count letters only
            letters = [c for c in pre_text if c.isalpha()]
            if letters:
                upper_count = sum(1 for c in letters if c.isupper())
                ratio = upper_count / len(letters)

                # Rule: If > 70% of the letters before the colon are CAPS, it's a Header.
                # "MELO, J" -> 100% Caps -> CUT.
                # "reads as follows" -> 0% Caps -> KEEP.
                if ratio > 0.70:
                    text = text[first_colon_index + 1:]

    # 6. Footer & Garbage Removal
    text = re.sub(r"Source:\s*Supreme Court E-Library.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"={5,}", "", text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_sections(raw_text):
    clean_body = clean_text(raw_text)

    # 1. DEFINE SPLIT PATTERNS
    # Pattern for the start of the "Ruling" section (dispositive portion)
    ruling_start_pattern = (
        r"(?:"
          r"WHEREFORE|ACCORDINGLY|FALLO|"
          r"IN\s+VIEW\s+(?:HEREOF|THEREOF|WHEREOF|OF\s+(?:ALL\s+)?THE\s+FOREGOING)|"
          r"ALL\s+THE\s+FOREGOING\s+CONSIDERED|"
          r"IN\s+(?:THE\s+)?LIGHT\s+OF\s+(?:ALL\s+)?THE\s+FOREGOING|"
          r"CONSEQUENTLY"
        r")"
        r".{0,300}?"  # Context lookahead
        r"(?:"
          r"premises|judgment|decision|petition|considered|"
          r"Court|finds|respondent|guilty|hereby|accused|"
          r"foregoing|appeal|instant|AFFIRMED|REVERSED|MODIFIED|DISMISSED|"
          r"assailed"
        r")"
    )

    # Pattern for the start of the "Issues" section
    issues_start_pattern = (
        r"(?:THE\s+COURT\s+IS\s+CALLED\s+UPON\s+TO\s+RESOLVE|"
        r"THE\s+ISSUES\s+FOR\s+RESOLUTION\s+ARE|"
        r"THE\s+SOLE\s+ISSUE\s+IS|"
        r"THE\s+MAIN\s+ISSUE\s+IS|"
        r"THE\s+PRIMARY\s+ISSUE\s+IS|"
        r"THE\s+QUESTION\s+IS|"
        r"THE\s+COURT\s+MUST\s+DETERMINE|"
        r"WE\s+ARE\s+TASKED\s+TO\s+DETERMINE|"
        r"THE\s+PETITION\s+RAISES\s+THE\s+FOLLOWING\s+ISSUES|"
        r"THE\s+ISSUES\s+PRESENTED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+RESOLVED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+ADDRESSED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+CONSIDERED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+DECIDED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+PASSED\s+UPON\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+RULED\s+UPON\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+SETTLED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+TAKEN\s+UP\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+TACKLED\s+ARE|"
        r"THE\s+ISSUES\s+TO\s+BE\s+RESOLVED\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+ADDRESSED\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+CONSIDERED\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+DECIDED\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+PASSED\s+UPON\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+RULED\s+UPON\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+SETTLED\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+TAKEN\s+UP\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+TO\s+BE\s+TACKLED\s+ARE\s+AS\s+FOLLOWS|"
        r"THE\s+ISSUES\s+ARE"
        r")"
        r"(?:\s*[:\.]|\s+)" # Optional colon/period or space after the phrase
    )

    # Default values
    facts = clean_body
    issues = ""
    ruling = ""
    status = "SPLIT_FORCED_90_PERCENT" # Default if no semantic split

    # 2. FIND RULING SPLIT POINT
    ruling_matches = list(re.finditer(ruling_start_pattern, clean_body, re.IGNORECASE))
    ruling_split_index = -1

    if ruling_matches:
        last_ruling_match = ruling_matches[-1]
        ruling_split_index = last_ruling_match.start()
        status = "SPLIT_SUCCESS_SEMANTIC"
    elif "SO ORDERED" in clean_body:
        # Fallback: Find paragraph break before SO ORDERED
        so_ordered_idx = clean_body.rfind("SO ORDERED")
        # Look for a newline within 1000 chars before "SO ORDERED"
        last_newline = clean_body.rfind("\n", max(0, so_ordered_idx - 1000), so_ordered_idx)
        if last_newline != -1:
            ruling_split_index = last_newline
            status = "SPLIT_FALLBACK_NEWLINE"
        else:
            # If no newline, just split at SO ORDERED
            ruling_split_index = so_ordered_idx
            status = "SPLIT_FALLBACK_SO_ORDERED"

    if ruling_split_index != -1:
        facts_and_issues = clean_body[:ruling_split_index].strip()
        ruling = clean_body[ruling_split_index:].strip()
    else:
        # If no ruling pattern found, assume the last 10% is ruling
        ruling_split_index = int(len(clean_body) * 0.9)
        facts_and_issues = clean_body[:ruling_split_index].strip()
        ruling = clean_body[ruling_split_index:].strip()
        status = "SPLIT_FORCED_90_PERCENT"


    # 3. FIND ISSUES SPLIT POINT within facts_and_issues
    issues_matches = list(re.finditer(issues_start_pattern, facts_and_issues, re.IGNORECASE))
    issues_split_index = -1

    if issues_matches:
        # Take the first match for issues, as they usually appear early
        first_issues_match = issues_matches[0]
        issues_split_index = first_issues_match.start()

        facts = facts_and_issues[:issues_split_index].strip()
        issues = facts_and_issues[issues_split_index:].strip()
        if status == "SPLIT_FORCED_90_PERCENT": # If ruling was forced, issues split is still semantic
            status = "SPLIT_SUCCESS_SEMANTIC_ISSUES_RULING_FORCED"
        elif status == "SPLIT_FALLBACK_NEWLINE" or status == "SPLIT_FALLBACK_SO_ORDERED":
            status = "SPLIT_SUCCESS_SEMANTIC_ISSUES_RULING_FALLBACK"
        else:
            status = "SPLIT_SUCCESS_SEMANTIC_ALL"
    else:
        facts = facts_and_issues # If no issues found, everything before ruling is facts
        issues = "" # No issues section
        if status == "SPLIT_SUCCESS_SEMANTIC":
            status = "SPLIT_SUCCESS_SEMANTIC_RULING_ONLY"
        elif status == "SPLIT_FALLBACK_NEWLINE" or status == "SPLIT_FALLBACK_SO_ORDERED":
            status = "SPLIT_FALLBACK_RULING_ONLY"
        # If status was already FORCED_90_PERCENT, it remains so.


    # 4. RUTHLESS TAIL CUT (No Names, No Footnotes) for Ruling
    # Find the LAST "SO ORDERED" in the ruling text
    so_ordered_matches = list(re.finditer(r"SO\s+ORDERED[\.\!]?", ruling, re.IGNORECASE))

    if so_ordered_matches:
        last_so_match = so_ordered_matches[-1]
        ruling = ruling[:last_so_match.end()]

    return {
        "facts": facts,
        "issues": issues,
        "ruling": ruling,
        "status": status
    }


def run_scraper():
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print("Error: CSV file not found.")
        return

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    scraped_count = 0

    for index, row in df.iterrows():
        case_id = str(row['case_no']).replace("/", "_").replace(" ", "")

        # --- THE MAGIC SWITCH ---
        # We automatically switch to the printer-friendly version here
        original_url = row['case_link']
        url = original_url.replace("showdocs", "showdocsfriendly")

        save_path = f"{OUTPUT_DIR}/{case_id}.txt"

        if os.path.exists(save_path):
            continue

        # Check Limit
        if MAX_SCRAPE_LIMIT is not None and MAX_SCRAPE_LIMIT > 0 and scraped_count >= MAX_SCRAPE_LIMIT:
            print(f"🛑 Reached limit of {MAX_SCRAPE_LIMIT} scraped files. Stopping.")
            break

        print(f"[{index+1}/{len(df)}] Scraping Friendly: {case_id}...")

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
                    f.write(f"STATUS: {sections['status']}\n")
                    f.write("="*20 + " FACTS " + "="*20 + "\n")
                    f.write(sections['facts'] + "\n\n")
                    f.write("="*20 + " ISSUES " + "="*20 + "\n")
                    f.write(sections['issues'] + "\n\n") # Added issues section
                    f.write("="*20 + " RULING " + "="*20 + "\n")
                    f.write(sections['ruling'] + "\n")

            else:
                print(f"Failed (Status {response.status_code})")

            scraped_count += 1

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    run_scraper()
