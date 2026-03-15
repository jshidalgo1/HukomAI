# HukomAI

AI-Powered Legal Document Classification for Philippine Supreme Court Decisions.

## Reorganized Structure

```text
HukomAI/
├── app.py (Streamlit Stub)
├── docs/ (Documentation)
│   ├── data_engineering.md
│   └── timeline.md
├── src/
│   ├── app/ (Streamlit Application)
│   │   └── app.py
│   ├── data/ (Data Pipeline)
│   │   ├── scraper.py
│   │   ├── labeler.py
│   │   ├── fixer.py
│   │   └── auditor.py
│   └── training/ (Model Training)
│       ├── utils.py
│       ├── train_headtail.py
│       └── train_sliding.py
└── .gitignore
```

## Running the App

```bash
streamlit run app.py
```
