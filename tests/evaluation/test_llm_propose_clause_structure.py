"""Unit tests for llm_propose_clause_structure.py.

Mirrors tests/evaluation/test_propose_promotion_evidence.py's own
pattern exactly: business logic (propose_clause_structure) is tested
with an INJECTED query callable (a lambda), never a real or mocked
Ollama HTTP call -- query_ollama's own network glue (reused directly
from propose_promotion_evidence.py) stays untested here, verified only
by a real CI run, the same policy as every Stanza-dependent test in
this project.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from llm_propose_clause_structure import (  # noqa: E402
    build_prompt,
    propose_clause_structure,
    propose_clause_structure_with_reason,
)


class BuildPromptTests(unittest.TestCase):
    def test_prompt_includes_the_sentence_and_lemma(self) -> None:
        prompt = build_prompt("Waterloo announces Henry County", "announce")
        self.assertIn("Waterloo announces Henry County", prompt)
        self.assertIn("announce", prompt)
        self.assertIn('"voice"', prompt)
        self.assertIn("proper_noun", prompt)


class ProposeClauseStructureTests(unittest.TestCase):
    def test_a_well_formed_response_is_returned_as_is(self) -> None:
        response = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry"]},
            "agent": None,
        }
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertEqual(structure, response)

    def test_a_voice_null_abstention_becomes_none(self) -> None:
        # The model's own "not confident" signal (see the prompt's
        # explicit instruction) -- must never be treated as a usable
        # structure.
        response = {"voice": None, "subject": None, "object": None, "agent": None}
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertIsNone(structure)

    def test_a_query_exception_becomes_none(self) -> None:
        def failing_query(prompt: str) -> dict:
            raise RuntimeError("boom")

        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", failing_query
        )
        self.assertIsNone(structure)

    def test_a_non_dict_response_becomes_none(self) -> None:
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: "not a dict"
        )
        self.assertIsNone(structure)

    def test_a_missing_voice_key_becomes_none(self) -> None:
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: {"subject": {}}
        )
        self.assertIsNone(structure)


class ProposeClauseStructureWithReasonTests(unittest.TestCase):
    """Real corpus evaluation data showed propose_clause_structure's own
    None outcome dominating LLM-tier attempts, with no way to tell a
    technical failure apart from the model's own deliberate abstention.
    These mirror ProposeClauseStructureTests's five cases exactly, but
    additionally assert the specific reason code each one now carries.
    """

    def test_a_well_formed_response_has_no_decline_reason(self) -> None:
        response = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry"]},
            "agent": None,
        }
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertEqual(structure, response)
        self.assertEqual(reason, "")

    def test_a_voice_null_abstention_is_not_a_technical_failure(self) -> None:
        response = {"voice": None, "subject": None, "object": None, "agent": None}
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "voice-null-abstention")

    def test_a_query_exception_is_reported_distinctly(self) -> None:
        def failing_query(prompt: str) -> dict:
            raise RuntimeError("boom")

        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", failing_query
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "query-exception")

    def test_a_non_dict_response_is_reported_distinctly(self) -> None:
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: "not a dict"
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "non-dict-response")

    def test_a_missing_voice_key_is_reported_distinctly_from_an_explicit_null(
        self,
    ) -> None:
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: {"subject": {}}
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "missing-voice-key")

    def test_calls_query_exactly_once(self) -> None:
        calls: list[str] = []

        def counting_query(prompt: str) -> dict:
            calls.append(prompt)
            return {"voice": None, "subject": None, "object": None, "agent": None}

        propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", counting_query
        )
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
