# Project Hukom-AI: Master Development Roadmap
**Project Goal:** Predict Supreme Court decisions based on factual patterns using NLP (RoBERTa/BERT).
**Current Status:** Entering **Phase 2 (Model Training)**.
**Hardware Strategy:** Optimized for T4 GPU (Google Colab) using Head+Tail & Sliding Window strategies.

---

## 🛠️ Technical Stack
* **Language:** Python 3.9+
* **Data Pipeline:**
    * `hukom_scraper.py` (Smart Scraper)
    * `hukom_auditor.py` (QA Tool)
    * `hukom_labeler_v4.py` (Regex Classification)
* **Modeling:** `PyTorch`, `Hugging Face Transformers`, `Scikit-Learn`
* **Training Scripts:** `train_headtail.py`, `train_sliding.py`
* **Interface:** `Streamlit`

---

## 📅 Phase 0: Data Engineering & Scrubbing (COMPLETED)
**Goal:** Acquire 30,000 clean, sectioned text files.

### Week 1-2: Scraper Development & Execution
- [x] **Analyze Source:** Identified "Printer Friendly" URLs and "Wherefore/In View Hereof" split patterns.
- [x] **Build Smart Scraper:** Developed `hukom_scraper.py` with Regex splitting and "Ruthless Cutter" for signatories.
- [x] **Quality Assurance:** Developed `hukom_auditor.py` and `hukom_refetcher.py` to heal broken files.
- [x] **Mass Execution:** Scraped ~31,000 files.
- [x] **Final Purge:** Archived ~124 problematic files (0.4% outlier rate).

---

## 📅 Phase 1: Labeling & Balancing (COMPLETED)
**Goal:** Convert text Rulings into mathematical labels (0-3).

### Week 3: Label Engineering
- [x] **Develop Labeler:** Created `hukom_labeler_v4.py` with administrative penalty detection.
- [x] **Keyword Mapping:**
    * **Label 0 (Defense Win):** Acquitted, Reversed, Granted, Reinstated.
    * **Label 1 (State Win):** Affirmed, Convicted, Denied, Suspended/Fined (Admin).
    * **Label 2 (Modification):** Modified, Partially Granted.
    * **Label 3 (Other):** Remanded, Moot, Compromise.
- [x] **Final Stats:** Achieved 96.8% labeling success rate.

---

## 📅 Phase 2: Model Training (The "Brain") - CURRENT STEP
**Goal:** Fine-tune Transformer models using two distinct strategies to balance speed vs. accuracy.

### Week 4: Setup & Baseline
- [ ] **Data Splitting:** Create `hukom_utils.py` to split data (80% Train / 10% Val / 10% Test) and remove "-1" unknowns.
- [ ] **Establish Baseline:** Train a simple `TF-IDF + SVM` model.
    -   *Goal:* Record the "Score to Beat" (likely ~65% F1).
- [ ] **Class Weighting:** Implement "Computed Class Weights" to handle the imbalance (since Label 1 is 2x larger than Label 0).

### Week 5: Strategy A - "Head + Tail" (Efficiency)
- [ ] **Develop Script:** Write `train_headtail.py`.
- [ ] **Tokenization Strategy:** Truncate text to: **First 128 tokens** (Intro) + **Last 384 tokens** (Conclusion of Facts).
- [ ] **Execution:** Train `RoBERTa-Tagalog-Base` on Colab T4 (FP16 enabled).
- [ ] **Evaluation:** Record F1-Macro score.

### Week 6: Strategy B - "Sliding Window" (Accuracy)
- [ ] **Develop Script:** Write `train_sliding.py`.
- [ ] **Tokenization Strategy:** Chunk long texts into multiple 512-token segments with overlap.
- [ ] **Execution:** Train overnight (slower process due to 3x data volume).
- [ ] **Comparison:** Compare Strategy A vs. Strategy B results.

---

## 📅 Phase 3: Evaluation & "Lawbytes" Defense
**Goal:** Prove the model learns "Law," not just "Keywords."

### Week 7: Metrics & Analysis
- [ ] **Confusion Matrix:** specific focus on False Positives (Did we send an innocent person to jail?).
- [ ] **Benchmarking:** Create the final comparison table:
    * *Baseline (SVM)* vs. *Generic BERT* vs. *Hukom-AI (RoBERTa)*.

### Week 8: Explainability (XAI)
- [ ] **Implement LIME:** Build a visualization tool to highlight *why* the model predicted "Acquittal".
- [ ] **Validation:** Verify if highlighted words align with legal concepts (e.g., "broken chain", "inconsistent testimony").

---

## 📅 Phase 4: Deployment & Documentation
**Goal:** Present the findings.

### Week 9: Application Interface
- [ ] **Build UI:** Create a Streamlit app.
- [ ] **Input:** Paste Fact Pattern.
- [ ] **Output:** Predicted Verdict + Confidence Score + Highlighted Key Phrases.

### Week 10: Writing the Paper
- [ ] **Methodology Section:** Document the "Header Guillotine" and "Semantic Splitter" (Phase 0).
- [ ] **Results Section:** Present the "Strategy A vs. B" comparison.
- [ ] **Submission.**