"""Unit tests for run_contextual_corpus.py's run_one line-scanning.

Only the new "tree-source=" parsing is covered here -- the rest of
run_one's line-scan (gf-tree=/graph_sha256=/stage=/survivors=/...) has
no prior dedicated test file at all (confirmed before adding this one);
scoping this file to the new field keeps it focused rather than
retroactively covering everything else in the same commit.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "evaluation"))

import run_contextual_corpus  # noqa: E402


def completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["python3", "scripts/run_automatic_contextual_pipeline.py"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class RunOneTreeSourceTests(unittest.TestCase):
    def test_records_stanza_tree_source(self) -> None:
        stdout = (
            "gf-tree=Pred (OpenPN \"Waterloo\") (Compl Announce (OpenPN \"Henry\"))\n"
            "tree-source=stanza\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["tree_source"], "stanza")

    def test_records_gf_parser_tree_source(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["tree_source"], "gf-parser")

    def test_no_tree_source_line_means_no_field_at_all(self) -> None:
        # exit1/exit2 rows never reach tree-building, so no
        # "tree-source=" line is ever printed for them -- confirms the
        # field is absent (not defaulted to some placeholder), matching
        # row_tree_source's own "not-applicable" fallback in
        # score_contextual_detection.py.
        with patch(
            "subprocess.run",
            return_value=completed("", returncode=2),
        ):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertNotIn("tree_source", result)


if __name__ == "__main__":
    unittest.main()
