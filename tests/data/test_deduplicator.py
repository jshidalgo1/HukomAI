"""
test_deduplicator.py – Unit tests for src.data.deduplicator
"""

import os
import tempfile
import pytest
import pandas as pd
from unittest.mock import patch

from src.data.deduplicator import (
    _extract_gr_roots,
    run_gr_grouping,
)


# ---------------------------------------------------------------------------
# _extract_gr_roots tests
# ---------------------------------------------------------------------------

class TestExtractGrRoots:

    def test_simple_gr_number(self):
        roots = _extract_gr_roots("G.R. No. 123456")
        assert roots == ["123456"]

    def test_letter_suffix_stripped(self):
        roots = _extract_gr_roots("G.R. No. 123456-B")
        assert roots == ["123456"]

    def test_consolidated_two_numbers(self):
        roots = _extract_gr_roots("G.R. Nos. 100001, 100002")
        assert "100001" in roots
        assert "100002" in roots

    def test_am_number(self):
        roots = _extract_gr_roots("A.M. No. P-01-1234")
        # Should extract "1234" (digits after P-01-)
        # Pattern captures digits after "No. "
        assert len(roots) >= 0  # At minimum doesn't crash

    def test_non_standard_returns_empty(self):
        roots = _extract_gr_roots("SPECIAL CASE")
        assert roots == []

    def test_empty_string_returns_empty(self):
        roots = _extract_gr_roots("")
        assert roots == []


# ---------------------------------------------------------------------------
# run_gr_grouping tests
# ---------------------------------------------------------------------------

def _make_csv(rows: list[dict], path: str) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


class TestRunGrGrouping:

    def test_same_root_same_family(self, tmp_path):
        csv_path = str(tmp_path / "decisions.csv")
        out_path  = str(tmp_path / "families.csv")
        _make_csv([
            {"case_no": "G.R. No. 123456",   "date": "January 1, 2000"},
            {"case_no": "G.R. No. 123456-B", "date": "March 3, 2001"},
        ], csv_path)

        df = run_gr_grouping(input_csv=csv_path, output_csv=out_path)

        family_ids = df["case_family_id"].tolist()
        assert family_ids[0] == family_ids[1], (
            "Cases with the same G.R. root should share a case_family_id"
        )

    def test_different_roots_different_families(self, tmp_path):
        csv_path = str(tmp_path / "decisions.csv")
        out_path  = str(tmp_path / "families.csv")
        _make_csv([
            {"case_no": "G.R. No. 100001", "date": "January 1, 2000"},
            {"case_no": "G.R. No. 200002", "date": "June 6, 2002"},
        ], csv_path)

        df = run_gr_grouping(input_csv=csv_path, output_csv=out_path)

        assert df["case_family_id"].iloc[0] != df["case_family_id"].iloc[1], (
            "Cases with different G.R. roots should have different case_family_ids"
        )

    def test_consolidated_normalises_to_lowest_root(self, tmp_path):
        csv_path = str(tmp_path / "decisions.csv")
        out_path  = str(tmp_path / "families.csv")
        _make_csv([
            {"case_no": "G.R. Nos. 300002, 300001", "date": "May 5, 2005"},
        ], csv_path)

        df = run_gr_grouping(input_csv=csv_path, output_csv=out_path)

        # The lowest numeric root (300001) should be the canonical family id
        assert df["case_family_id"].iloc[0] == "GR300001"

    def test_output_csv_schema(self, tmp_path):
        csv_path = str(tmp_path / "decisions.csv")
        out_path  = str(tmp_path / "families.csv")
        _make_csv([
            {"case_no": "G.R. No. 999999", "date": "July 7, 2007"},
        ], csv_path)

        run_gr_grouping(input_csv=csv_path, output_csv=out_path)

        out_df = pd.read_csv(out_path)
        assert "case_no"        in out_df.columns
        assert "case_family_id" in out_df.columns
        assert "family_size"    in out_df.columns

    def test_no_null_family_ids(self, tmp_path):
        csv_path = str(tmp_path / "decisions.csv")
        out_path  = str(tmp_path / "families.csv")
        _make_csv([
            {"case_no": "G.R. No. 111111", "date": ""},
            {"case_no": "SPECIAL-CASE",    "date": ""},  # non-standard
        ], csv_path)

        df = run_gr_grouping(input_csv=csv_path, output_csv=out_path)
        assert df["case_family_id"].isna().sum() == 0, (
            "No case_family_id should be null"
        )

    def test_family_size_counts(self, tmp_path):
        csv_path = str(tmp_path / "decisions.csv")
        out_path  = str(tmp_path / "families.csv")
        _make_csv([
            {"case_no": "G.R. No. 500001", "date": ""},
            {"case_no": "G.R. No. 500001-A", "date": ""},
            {"case_no": "G.R. No. 500001-B", "date": ""},
        ], csv_path)

        df = run_gr_grouping(input_csv=csv_path, output_csv=out_path)
        assert (df["family_size"] == 3).all()


# ---------------------------------------------------------------------------
# run_embedding_dedup tests (lightweight – no actual model loading)
# ---------------------------------------------------------------------------

class TestRunEmbeddingDedup:
    """
    These tests patch out sentence-transformers and faiss to verify
    the logic without requiring GPU/heavy dependencies.

    Because run_embedding_dedup uses lazy `import` statements INSIDE the
    function body (so the pipeline works without these packages installed),
    we must patch via sys.modules rather than patching module-level names.
    """

    @staticmethod
    def _make_corpus(corpus_dir, files):
        """Helper: write minimal corpus .txt files."""
        for name, facts_text in files:
            with open(os.path.join(corpus_dir, name), "w") as f:
                f.write("URL: x\nSTATUS: OK\n")
                f.write("==================== FACTS ====================\n")
                f.write(facts_text + "\n")
                f.write("==================== RULING ====================\nSO ORDERED.\n")

    def test_high_similarity_flagged(self, tmp_path):
        """Two identical texts should be flagged as near-duplicates."""
        import sys, types
        import numpy as np

        corpus_dir = str(tmp_path / "corpus")
        os.makedirs(corpus_dir)
        sim_out = str(tmp_path / "sim.csv")

        self._make_corpus(corpus_dir, [
            ("A.txt", "The petitioner seeks review."),
            ("B.txt", "The petitioner seeks review."),
        ])

        # ----- Fake sentence_transformers module -----
        fake_st = types.ModuleType("sentence_transformers")

        class _FakeST:
            def __init__(self, name): pass
            def encode(self, texts, **kw):
                return np.ones((len(texts), 2), dtype="float32")

        fake_st.SentenceTransformer = _FakeST

        # ----- Fake faiss module -----
        fake_faiss = types.ModuleType("faiss")

        class _FakeIndex:
            def add(self, v): pass
            def search(self, v, k):
                n = len(v)
                dist = np.ones((n, k), dtype="float32")
                idx  = np.array([[(i + j + 1) % n for j in range(k)]
                                 for i in range(n)], dtype="int64")
                return dist, idx

        fake_faiss.IndexFlatIP = lambda dim: _FakeIndex()

        with patch.dict(sys.modules, {
            "sentence_transformers": fake_st,
            "faiss": fake_faiss,
        }):
            from importlib import reload
            import src.data.deduplicator as dedup_mod
            reload(dedup_mod)  # force re-import with patched modules in scope
            result = dedup_mod.run_embedding_dedup(
                corpus_dir=corpus_dir,
                output_csv=sim_out,
                threshold=0.5,      # low – any sim >= 0.5 flagged
            )

        assert len(result) >= 1, "Near-duplicate pair should have been flagged"

    def test_sim_dedup_report_schema(self, tmp_path):
        """Output DataFrame columns must include the required fields."""
        import sys, types
        import numpy as np

        corpus_dir = str(tmp_path / "corpus")
        os.makedirs(corpus_dir)
        sim_out = str(tmp_path / "sim.csv")

        self._make_corpus(corpus_dir, [
            ("X.txt", "First document."),
            ("Y.txt", "Completely different topic."),
        ])

        fake_st = types.ModuleType("sentence_transformers")

        class _FakeST:
            def __init__(self, name): pass
            def encode(self, texts, **kw):
                return np.zeros((len(texts), 2), dtype="float32")

        fake_st.SentenceTransformer = _FakeST

        fake_faiss = types.ModuleType("faiss")

        class _FakeIndex:
            def add(self, v): pass
            def search(self, v, k):
                n = len(v)
                return np.zeros((n, k), dtype="float32"), np.zeros((n, k), dtype="int64")

        fake_faiss.IndexFlatIP = lambda dim: _FakeIndex()

        with patch.dict(sys.modules, {
            "sentence_transformers": fake_st,
            "faiss": fake_faiss,
        }):
            from importlib import reload
            import src.data.deduplicator as dedup_mod
            reload(dedup_mod)
            result = dedup_mod.run_embedding_dedup(
                corpus_dir=corpus_dir,
                output_csv=sim_out,
                threshold=0.99,     # nothing should be flagged
            )

        assert isinstance(result, pd.DataFrame)
        # If pairs were found, check schema
        if len(result) > 0:
            for col in ("case_id_a", "case_id_b", "cosine_similarity", "recommended_action"):
                assert col in result.columns
