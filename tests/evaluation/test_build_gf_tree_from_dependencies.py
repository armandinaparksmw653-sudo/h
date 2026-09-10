"""Unit tests for build_gf_tree_from_dependencies's Phase 1 tree builder.

Words are plain dicts (id/head/deprel/upos/lemma/text/start_char/
end_char) -- the same flat shape annotate_dependency_hints.py's new
"ud_words" hint field carries after a JSON round-trip, deliberately not
a duck-typed Stanza-like object (build_gf_tree never sees a live Stanza
object, only its serialized form).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_gf_tree_from_dependencies import (  # noqa: E402
    build_gf_tree,
    load_gf_function_by_lemma,
)

GF_FUNCTIONS = {"announce": "CTX_announce", "praise": "CTX_praise"}


def word(
    id_: int,
    text: str,
    lemma: str,
    upos: str,
    deprel: str,
    head: int,
    start_char: int,
) -> dict:
    return {
        "id": id_,
        "text": text,
        "lemma": lemma,
        "upos": upos,
        "deprel": deprel,
        "head": head,
        "start_char": start_char,
        "end_char": start_char + len(text),
    }


class SimpleTransitiveClauseTests(unittest.TestCase):
    def test_single_word_proper_noun_subject_and_object(self) -> None:
        # "Waterloo announces Henry"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree, 'Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry"))'
        )

    def test_two_word_compound_proper_noun_uses_openpn2(self) -> None:
        # "Henry County announces Waterloo"
        words = [
            word(1, "Henry", "Henry", "PROPN", "compound", 2, 0),
            word(2, "County", "County", "PROPN", "nsubj", 3, 6),
            word(3, "announces", "announce", "VERB", "root", 0, 13),
            word(4, "Waterloo", "Waterloo", "PROPN", "obj", 3, 23),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN2 "Henry" "County") (Compl CTX_announce (OpenPN "Waterloo"))',
        )

    def test_three_word_compound_proper_noun_uses_openpn3(self) -> None:
        # "Waterloo announces The Royal Shipley School"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Royal", "Royal", "PROPN", "compound", 5, 19),
            word(4, "Shipley", "Shipley", "PROPN", "compound", 5, 25),
            word(5, "School", "School", "PROPN", "obj", 2, 33),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenPN3 "Royal" "Shipley" "School"))',
        )

    def test_four_word_compound_proper_noun_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "A", "A", "PROPN", "compound", 6, 19),
            word(4, "B", "B", "PROPN", "compound", 6, 21),
            word(5, "C", "C", "PROPN", "compound", 6, 23),
            word(6, "D", "D", "PROPN", "obj", 2, 25),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_pronoun_subject(self) -> None:
        # "He praises Tolstoy"
        words = [
            word(1, "He", "he", "PRON", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 3),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 11),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
        self.assertEqual(tree, 'Pred HePN (Compl CTX_praise (OpenPN "Tolstoy"))')

    def test_pronoun_object(self) -> None:
        # "Tolstoy praises them"
        words = [
            word(1, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 8),
            word(3, "them", "they", "PRON", "obj", 2, 16),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
        self.assertEqual(tree, 'Pred (OpenPN "Tolstoy") (Compl CTX_praise TheyPN)')

    def test_all_four_pronoun_constructors(self) -> None:
        for pronoun_lemma, constructor in (
            ("he", "HePN"),
            ("she", "ShePN"),
            ("it", "ItPN"),
            ("they", "TheyPN"),
        ):
            with self.subTest(pronoun_lemma=pronoun_lemma):
                words = [
                    word(1, pronoun_lemma, pronoun_lemma, "PRON", "nsubj", 2, 0),
                    word(2, "praises", "praise", "VERB", "root", 0, 3),
                    word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 11),
                ]
                tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
                self.assertEqual(
                    tree, f'Pred {constructor} (Compl CTX_praise (OpenPN "Tolstoy"))'
                )


class BailsOutToNoneTests(unittest.TestCase):
    def test_a_pp_modifier_is_out_of_scope(self) -> None:
        # "Waterloo announces Henry in Ontario"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "in", "in", "ADP", "case", 6, 25),
            word(5, "Ontario", "Ontario", "PROPN", "obl", 2, 28),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_determiner_is_out_of_scope(self) -> None:
        words = [
            word(1, "The", "the", "DET", "det", 2, 0),
            word(2, "county", "county", "NOUN", "nsubj", 3, 4),
            word(3, "announces", "announce", "VERB", "root", 0, 11),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 21),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_passive_clause_is_out_of_scope(self) -> None:
        words = [
            word(1, "Henry", "Henry", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 6),
            word(3, "announced", "announce", "VERB", "root", 0, 10),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_coordination_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "and", "and", "CCONJ", "cc", 6, 25),
            word(5, "Tolstoy", "Tolstoy", "PROPN", "conj", 3, 29),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_common_noun_subject_is_out_of_scope(self) -> None:
        words = [
            word(1, "county", "county", "NOUN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 7),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 17),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_no_object_is_out_of_scope(self) -> None:
        # grammar/Metonymy.gf has no intransitive VP at all.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_more_than_one_root_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "announces", "announce", "VERB", "root", 0, 30),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_lemma_missing_from_the_gf_action_lexicon_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "floreates", "floreate", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertIsNone(build_gf_tree(words, "floreate", GF_FUNCTIONS))

    def test_an_auxiliary_root_with_no_matching_shape_is_out_of_scope(self) -> None:
        # "He is Tolstoy" -- AUX root but no matching action lemma; also
        # exercises the AUX branch of the root-upos check.
        words = [
            word(1, "He", "he", "PRON", "nsubj", 2, 0),
            word(2, "is", "be", "AUX", "root", 0, 3),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 6),
        ]
        self.assertIsNone(build_gf_tree(words, "be", GF_FUNCTIONS))


class LoadGfFunctionByLemmaTests(unittest.TestCase):
    def test_inverts_the_gf_function_to_lemma_direction(self) -> None:
        actions_json = {
            "actions": [
                {"gf_function": "CTX_abc123", "lemma": "abandon"},
                {"gf_function": "CTX_def456", "lemma": "announce"},
            ]
        }
        self.assertEqual(
            load_gf_function_by_lemma(actions_json),
            {"abandon": "CTX_abc123", "announce": "CTX_def456"},
        )


if __name__ == "__main__":
    unittest.main()
