# Hukom-AI Enhanced Roadmap – Comprehensive Description

## Phase 0 – Data Engineering & Scrubbing
**Goal:** Acquire a clean, structured dataset suitable for modeling, while preventing data leakage.

- **Dataset Cleaning**
  - Scrape Supreme Court decisions (~31,000 cases) and remove formatting artifacts.
  - Section the text into `facts`, `issues`, and `ruling` to enable structured analysis.
- **Duplicate Case Handling**
  - Group cases by family (same petition, incident, or G.R. number) to prevent near-duplicate cases from leaking between training, validation, and test splits.
  - Optional similarity-based filtering using embeddings to detect text overlaps.
- **Leakage Prevention**
  - Remove explicit outcome keywords (e.g., “affirmed,” “reversed”) from the `facts` section to avoid the model memorizing verdict cues.
  - Ensure `ruling` sections are not used as input features.

---

## Phase 1 – Labeling & Multi-Task Setup
**Goal:** Convert unstructured rulings into structured labels and enrich the dataset with reasoning metadata.

- **Hybrid Labeling Pipeline**
  - Use regex-based labeling for fast automatic assignment.
  - Deploy LLM fallback (Gemini-1.5 Flash → Gemini-1.5 Pro → Claude 3.5 Sonnet) for ambiguous or unknown labels.
  - Structured JSON output:  
    ```json
    {
      "label": 0-3,
      "reasoning": "short textual explanation"
    }
    ```
- **Multi-task Labeling**
  - Assign **verdict labels** (0-3) corresponding to defense/state/modification/other outcomes.
  - Assign **reasoning categories**, e.g.:
    - Evidence insufficiency
    - Procedural issue
    - Credibility
    - Legal interpretation
- **Case Type Annotation**
  - Categorize each case by legal domain: criminal, civil, labor, tax, administrative, election.
- **Manual QA & Verification**
  - Compare LLM outputs (Flash vs Pro) and inspect reasoning fields for quality.
  - Resolve conflicts through human review.

---

## Phase 2 – Model Training
**Goal:** Train models that can handle long legal texts and predict verdicts and reasoning.

- **Long Document Strategies**
  - **Head + Tail Strategy:** Use first 128 tokens (intro/facts) + last 384 tokens (conclusion/ruling summary). Efficient for T4 GPUs.
  - **Sliding Window Strategy:** Chunk texts into overlapping 512-token segments for accurate processing of long documents.
- **Feature Integration**
  - **Panel Composition:** Encode justices as embeddings or one-hot features.
  - **Case Type:** Include legal domain as categorical feature.
  - **Citation Count:** Number of precedents cited in the ruling.
- **Multi-task Training**
  - Predict both `verdict` and `reasoning category` simultaneously.
  - Loss function: `verdict_loss + reasoning_loss`.
- **Ensemble Modeling**
  - Combine Head+Tail and Sliding Window strategies.
  - Aggregate predictions through probability averaging or majority voting.

---

## Phase 3 – Evaluation & LLM Comparison
**Goal:** Evaluate model generalization, explainability, and compare fine-tuned models with LLM baselines.

- **Temporal & Generalization Evaluation**
  - Test models on cases from later years to simulate real-world deployment.
  - Prevent leakage by maintaining chronological splits.
- **LLM Benchmarking**
  - Compare zero-shot and few-shot performance of:
    - Gemini-1.5 Flash
    - Gemini-1.5 Pro
    - Claude 3.5 Sonnet
  - Evaluate both **accuracy** and **reasoning explanations**.
- **Fine-Tuned Model Comparison**
  - Compare RoBERTa Head+Tail, Sliding Window, and ensemble models against LLM performance.
- **Explainability**
  - Apply LIME/SHAP to highlight key text features contributing to predictions.
  - Evaluate contribution of panel composition, citations, and case type features.

---

## Phase 4 – Deployment & Broader Features
**Goal:** Build an interactive application, release the benchmark, and explore optional Philippine-specific NLP enhancements.

- **Streamlit App**
  - Input: Paste fact patterns (cleaned, leakage-free).
  - Output: Predicted verdict, reasoning category, confidence score, highlighted key phrases.
- **Optional: Code-Switching Analysis**
  - Detect Tagalog-English ratios in cases.
  - Analyze model performance on code-switched legal text.
- **Optional: Citation Graph**
  - Build a network of precedent citations to provide relational reasoning features.
- **Open Dataset & Benchmark Tasks**
  - Structured release including:
    ```
    case_id, year, case_title, facts, issues, ruling, verdict_label, reasoning_category, case_type, citations, panel_justices
    ```
  - Benchmark tasks:
    - Task 1: Legal Judgment Prediction (facts → verdict)
    - Task 2: Case Type Classification (facts → case type)
    - Task 3: Reasoning Extraction (ruling → reasoning category)
  - Include baseline models for reproducibility.

---

## Multi-Paper Strategy
**Goal:** Split the project into multiple, publishable papers with distinct contributions.

1. **Paper 1: HukomBench – Dataset & Labeling**
   - Release the structured dataset with hybrid labeling pipeline and toolkit.
   - Venue: LegalNLP@ACL, LREC.

2. **Paper 2: Modeling Long Legal Texts**
   - Evaluate Head+Tail vs Sliding Window strategies, multi-task learning, and ensembles.
   - Venue: ACL/EMNLP Legal NLP tracks, ICAIL.

3. **Paper 3: LLM Benchmarking vs Fine-Tuned Models**
   - Compare LLMs (Flash, Pro, Claude 3.5) with fine-tuned models.
   - Include cost vs performance analysis.
   - Venue: AI/LLM workshops.

4. **Paper 4: Multi-Task Judicial Reasoning Analysis**
   - Focus on verdict + reasoning multi-task learning, explainability, and reasoning insights.
   - Venue: XAI workshops, ICAIL.

5. **Paper 5 (Optional): Multilingual / Philippine Legal NLP**
   - Analyze code-switching, citation graph features, or other Philippine-specific challenges.
   - Venue: Multilingual NLP workshops, Legal NLP conferences.

---

## Key Takeaways
- Dataset quality and leakage prevention are critical for credible results.
- Multi-task labels and enriched features improve both accuracy and explainability.
- Hybrid LLM + fine-tuned ensemble provides robust performance.
- Framing the research around **learning judicial reasoning patterns** enhances publishability.
- Splitting the project into multiple papers maximizes impact and citation potential.