import os
import re
import pandas as pd

# --- CONFIGURATION ---
INPUT_DIR = "hukom_corpus_friendly"
OUTPUT_CSV = "hukom_dataset_final.csv"


def get_label(ruling_text):
    text = ruling_text.upper()

    # --- PRIORITY 1: REMAND / OTHER / SETTLEMENT (Label 3) ---
    if re.search(r"(REMAND|MOOT|RETURNED|RE-RAFFLE|COMPROMISE|AMICABLE|SETTLEMENT|CLOSED|TERMINATED)", text):
        return 3

    # --- PRIORITY 2: MODIFICATION (Label 2) ---
    if re.search(r"(MODIF|PARTIALLY)", text):
        return 2

    # --- PRIORITY 3: DEFENSE WIN / REVERSAL / NULLIFICATION (Label 0) ---
    if re.search(r"(ACQUIT|REVERSE|GRANTED|GRANTING|SET\s+ASIDE|SETS\s+ASIDE|REINSTATE|NULLIFY|DECLARE\s+VOID|ANNUL|MADE\s+PERMANENT)", text):
        return 0

    # --- PRIORITY 4: PROSECUTION WIN / AFFIRMATION / LIABILITY (Label 1) ---
    if re.search(r"(AFFIRM|DENIED|DENYING|DISMISSED|DISMISSING|GUILTY|CONVICT|SENTENCE|ORDERED\s+TO\s+PAY)", text):
        return 1
    if re.search(r"(SUSPEND|FINE|REPRIMAND|ADMONISH|LIABLE|DISBAR|FORFEIT|REVOKED)", text):
        return 1

    # --- PRIORITY 5: UNKNOWN (Label -1) ---
    return -1


def label_corpus():
    if not os.path.exists(INPUT_DIR):
        print(f"Directory '{INPUT_DIR}' not found.")
        return

    data = []
    stats = {0: 0, 1: 0, 2: 0, 3: 0, -1: 0}

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    print(f"Final Labeling Run: {len(files)} files...\n")

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if "========== RULING ==========" in content:
                parts = content.split("========== RULING ==========")
                ruling_text = parts[1].strip()

                label = get_label(ruling_text)

                data.append({
                    "filename": filename,
                    "label": label,
                    "text": content
                })

                stats[label] += 1
            else:
                stats[-1] += 1

        except Exception as e:
            print(f"Error reading {filename}: {e}")

    # --- SAVE RESULTS ---
    df = pd.DataFrame(data)
    # Save a "Lite" version for quick checking (Filename + Label)
    df[["filename", "label"]].to_csv(OUTPUT_CSV, index=False)

    print("-" * 40)
    print("FINAL DATASET STATS")
    print(f"Label 0 (Defense Win):   {stats[0]}")
    print(f"Label 1 (State Win):     {stats[1]}")
    print(f"Label 2 (Modification):  {stats[2]}")
    print(f"Label 3 (Remand/Moot):   {stats[3]}")
    print(f"Label -1 (Unknown):      {stats[-1]}")
    print("-" * 40)
    print(f"Ready for Phase 2! Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    label_corpus()
