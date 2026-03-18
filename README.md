# HukomAI

AI-Powered Legal Document Classification for Philippine Supreme Court Decisions.

HukomAI is a research-driven project focused on automating the classification and analysis of Philippine Supreme Court (SC) decisions. It encompasses a robust data engineering pipeline, advanced NLP models for legal text, and an interactive exploration dashboard.

---

## 🚀 Phase 0: Data Engineering Pipeline

The project features a 7-stage automated pipeline in `src.data.pipeline` designed to build a high-quality legal corpus from scratch.

1.  **Scraping**: Automated extraction of SC decisions with a focus on capturing 'Issues' sections.
2.  **Auditing**: Validation of scraped files for consistency and completeness.
3.  **Fixing**: Automated repair of common formatting issues in legal text.
4.  **G.R. Family Grouping**: Initial deduplication by grouping related Case Numbers (G.R. Nos.).
5.  **Embedding-Based Dedup**: Semantic deduplication using sentence embeddings to catch near-duplicates.
6.  **Leakage Guard**: Prevention of data leakage by ensuring no overlap between training and evaluation splits.
7.  **Dataset Building**: Generation of the final cleaned CSV for model training.

**Run the pipeline:**
```bash
python -m src.data.pipeline
```
*Use `--help` to see options for skipping specific stages.*

---

## 📂 Project Structure

```text
HukomAI/
├── app.py                 # Streamlit entry point (stub)
├── docs/                  # Detailed Research & Implementation Docs
│   ├── data_engineering.md
│   ├── data_pipeline.md
│   ├── implementation_plan.md
│   └── timeline.md        # Phase-to-Paper Roadmap
├── src/
│   ├── app/               # Streamlit UI Components
│   ├── data/              # Data Pipeline Core (Scrapers, Dedup, etc.)
│   │   ├── scraper.py
│   │   ├── pipeline.py
│   │   └── ...
│   └── training/          # Model Training Strategies
│       ├── train_headtail.py   # Strategy for long legal docs
│       └── train_sliding.py    # Sliding window inference
├── tests/                 # Automated Test Suite
└── .dvc/                  # Data Version Control configuration
```

---

## 📊 Data Management (DVC)

We use **DVC (Data Version Control)** to manage large datasets and model weights without bloating the Git repository.

- **Storage**: Remote storage is configured on Google Drive.
- **Pulling Data**: If you have the credentials, run:
  ```bash
  dvc pull
  ```

---

## 🖥️ Interactive Dashboard

HukomAI includes a Streamlit-based interface for exploring the dataset and model predictions.

**Start the app:**
```bash
streamlit run app.py
```

---

## 📄 Documentation

For deep dives into the methodology, refer to the `docs/` folder:
- [Data Engineering Deep Dive](docs/data_engineering.md)
- [Project Roadmap & Timeline](docs/timeline.md)
