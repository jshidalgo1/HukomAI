# Phase 0 – Data Engineering & Scrubbing: Implementation Plan

**Goal:** Produce a clean, leakage-free, structurally enriched dataset from the existing ~31k Supreme Court decision corpus, ready for Phase 1 labeling. This work feeds directly into **Paper 1: HukomBench – Dataset & Labeling**.

---

## Current State (What Already Exists)

| Script | Role | Status |
|---|---|---|
| [scraper.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/scraper.py) | Scrapes SC decisions; splits into `facts` + `ruling` | ✅ Exists |
| [auditor.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/auditor.py) | Flags files with bad splits, header residue, etc. | ✅ Exists |
| [fixer.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/fixer.py) | Re-processes flagged files | ✅ Exists |
| [archiver.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/archiver.py) | Moves bad files to quarantine | ✅ Exists |
| [refetcher.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/refetcher.py) | Re-downloads flagged files from the web | ✅ Exists |
| [rescue_mission.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/rescue_mission.py) | Re-downloads locally-fixed files | ✅ Exists |
| [labeler.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/labeler.py) | Regex-based verdict labeling → [hukom_dataset_final.csv](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/hukom_dataset_final.csv) | ✅ Exists (Phase 1 concern) |

**Gaps vs. Phase 0 roadmap:**
- No `issues` section extraction (only `facts` + `ruling`)
- No duplicate/family grouping by G.R. number
- No leakage prevention (verdict cues still live in `facts`)
- No structured CSV with enriched fields (`year`, `case_title`, `case_family_id`, `issues`)
- No centralized config (paths are hardcoded per file)
- No pipeline orchestrator

---

## Proposed Changes

### Config Layer

#### [NEW] [config.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/config.py)

Centralize all hardcoded paths and constants used across scripts.

```python
# Shared constants
INPUT_CSV   = "sc_decisions.csv"
CORPUS_DIR  = "hukom_corpus_friendly"
QUARANTINE  = "hukom_quarantine"
AUDIT_FILE  = "audit_report.csv"
DATASET_OUT = "hukom_phase0_dataset.csv"
FAMILY_OUT  = "family_groups.csv"
```

Update all existing scripts ([scraper.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/scraper.py), [auditor.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/auditor.py), [fixer.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/fixer.py), [archiver.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/archiver.py), [refetcher.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/refetcher.py), [rescue_mission.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/rescue_mission.py)) to import from `config.py` instead of repeating constants.

---

### Scraper Enhancement

#### [MODIFY] [scraper.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/scraper.py)

Extend [extract_sections()](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/scraper.py#81-138) to detect a third `issues` block between facts and ruling.

**New logic:**
- Search for headers like `ISSUE`, `THE ISSUE`, `ISSUES PRESENTED`, `QUESTION PRESENTED` using regex.
- If found, carve out an `issues` field between `facts` and `ruling`.
- If not found, `issues` defaults to `""` (empty string).

Updated file format:
```
URL: ...
STATUS: ...
==================== FACTS ====================
...
==================== ISSUES ====================
...
==================== RULING ====================
...
```

---

### New Modules

#### [NEW] [deduplicator.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/deduplicator.py)

Groups cases into "families" to prevent near-duplicates from bleeding across train/val/test splits.

**Logic:**
1. Load [sc_decisions.csv](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/sc_decisions.csv).
2. Parse G.R. numbers (e.g., `G.R. No. 123456` and `G.R. No. 123456-B` belong to the same family).
3. Assign each row a `case_family_id` (e.g., `GR123456`).
4. Export `family_groups.csv` with columns: `case_no`, `case_family_id`, `family_size`.

> [!NOTE]
> Embedding-based deduplication (cosine similarity filtering) is marked as **optional** in the roadmap and will be implemented as a separate, toggleable step in a future iteration.

---

#### [NEW] [leakage_guard.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/leakage_guard.py)

Scrubs explicit verdict-cue keywords from the `facts` section to prevent the model from "learning" the outcome from the input.

**Scrub target keywords (case-insensitive):**
```
affirmed, reversed, modified, dismissed, acquitted, convicted,
granted, denied, set aside, reinstated, nullified, annulled,
remanded, moot
```

**Logic:**
1. For each `.txt` file in the corpus, extract the `facts` section.
2. Run regex substitution replacing cue phrases with `[REDACTED]`.
3. Overwrite the file's facts block with the scrubbed version, annotating the status line as [(LEAKAGE_GUARD_APPLIED)](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/fixer.py#24-115).
4. Log a per-file count of words scrubbed.

> [!IMPORTANT]
> The `ruling` section is **never used as a model input feature** — it is only used for label generation in Phase 1. `leakage_guard.py` only modifies the `facts` block.

---

#### [NEW] [dataset_builder.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/dataset_builder.py)

Reads the cleaned corpus and emits a single structured output CSV to replace the ad-hoc [hukom_dataset_final.csv](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/hukom_dataset_final.csv) approach.

**Output schema:**
| Column | Source |
|---|---|
| `case_id` | filename (e.g., `G.R.No.12345.txt`) |
| `year` | parsed from [sc_decisions.csv](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/sc_decisions.csv) |
| `case_title` | parsed from [sc_decisions.csv](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/sc_decisions.csv) |
| `facts` | scrubbed facts block from corpus |
| `issues` | issues block (empty if not found) |
| `ruling` | ruling block |
| `case_family_id` | from `family_groups.csv` |
| `split_status` | from corpus file STATUS line |

Output file: `hukom_phase0_dataset.csv`

---

#### [NEW] [pipeline.py](file:///Users/najmahal/Desktop/PersonalProjects/HukomAI/src/data/pipeline.py)

Orchestrates the full Phase 0 pipeline in one runnable script:

```
Step 1: scraper.run_scraper()
Step 2: auditor.check_files()
Step 3: fixer.fix_files()        # or refetcher.refetch_files()
Step 4: deduplicator.run()
Step 5: leakage_guard.run()
Step 6: dataset_builder.build()
```

Each step can be toggled on/off via command-line flags or a config dict. Final output: `hukom_phase0_dataset.csv`.

---

## Verification Plan

### New Automated Tests

Since there are no existing tests in the codebase, we will create a `tests/` directory with the following:

#### `tests/data/test_leakage_guard.py`
- Tests that verdict cue keywords are successfully replaced with `[REDACTED]` in sample facts text.
- Tests that the `ruling` section is NOT modified.
- Tests that files with no cue words are unchanged.
- **Run with:** `python -m pytest tests/data/test_leakage_guard.py`

#### `tests/data/test_deduplicator.py`
- Tests that cases with the same G.R. number root are assigned the same `case_family_id`.
- Tests that cases with different G.R. numbers are assigned different family IDs.
- Tests the output CSV schema (correct columns, no null family IDs).
- **Run with:** `python -m pytest tests/data/test_deduplicator.py`

#### `tests/data/test_dataset_builder.py`
- Tests that the output CSV has all required columns.
- Tests that no row has a `ruling` value in the `facts` column.
- **Run with:** `python -m pytest tests/data/test_dataset_builder.py`

### Manual Spot-Check
1. After running `pipeline.py`, open `hukom_phase0_dataset.csv` in a spreadsheet tool.
2. Pick 10 random rows and verify:
   - `facts` does **not** contain obvious verdict words (affirmed, reversed, etc.)
   - `issues` is populated where possible
   - `case_family_id` groups related G.R. numbers correctly
   - `ruling` is present and non-empty
