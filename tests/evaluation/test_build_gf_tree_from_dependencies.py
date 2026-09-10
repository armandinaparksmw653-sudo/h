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

    def test_a_non_article_determiner_is_out_of_scope(self) -> None:
        # "a"/"an"/"the" are in scope (see CommonNounNpTests below) --
        # "every"/"this"/etc are not: OpenIndefCN/OpenDefCN only ever
        # produce "a"/"the", so this module isn't confident guessing a
        # shape for anything else.
        words = [
            word(1, "Every", "every", "DET", "det", 2, 0),
            word(2, "county", "county", "NOUN", "nsubj", 3, 6),
            word(3, "announces", "announce", "VERB", "root", 0, 13),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 23),
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

    def test_a_lemma_mismatched_with_uds_own_root_is_out_of_scope(self) -> None:
        # Guards the case resolve_action's positional fallback (used
        # whenever dependency_hint's dep_status isn't "direct-argument")
        # resolved a *different* word than UD's own root -- must not
        # silently build a tree around the wrong clause.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertIsNone(build_gf_tree(words, "sign", GF_FUNCTIONS))


class CommonNounNpTests(unittest.TestCase):
    def test_indefinite_common_noun_object(self) -> None:
        # "Waterloo announces a programme"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "a", "a", "DET", "det", 4, 19),
            word(4, "programme", "programme", "NOUN", "obj", 2, 21),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenIndefCN "programme" "programme"))',
        )

    def test_definite_common_noun_subject(self) -> None:
        # "The county announces Henry"
        words = [
            word(1, "The", "the", "DET", "det", 2, 0),
            word(2, "county", "county", "NOUN", "nsubj", 3, 4),
            word(3, "announces", "announce", "VERB", "root", 0, 11),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 21),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenDefCN "county" "county") '
            '(Compl CTX_announce (OpenPN "Henry"))',
        )

    def test_indefinite_common_noun_with_adjective(self) -> None:
        # "Waterloo announces a large county"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "a", "a", "DET", "det", 5, 19),
            word(4, "large", "large", "ADJ", "amod", 5, 21),
            word(5, "county", "county", "NOUN", "obj", 2, 27),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenAdjIndefCN "large" "county" "county"))',
        )

    def test_definite_common_noun_with_adjective(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 5, 19),
            word(4, "large", "large", "ADJ", "amod", 5, 23),
            word(5, "county", "county", "NOUN", "obj", 2, 29),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenAdjDefCN "large" "county" "county"))',
        )

    def test_a_common_noun_with_no_determiner_at_all_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "programmes", "programme", "NOUN", "obj", 2, 19),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_two_adjectives_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "a", "a", "DET", "det", 6, 19),
            word(4, "large", "large", "ADJ", "amod", 6, 21),
            word(5, "old", "old", "ADJ", "amod", 6, 27),
            word(6, "county", "county", "NOUN", "obj", 2, 31),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


class PassiveClauseTests(unittest.TestCase):
    def test_passive_with_a_proper_noun_agent(self) -> None:
        # "Waterloo was announced by Henry"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 9),
            word(3, "announced", "announce", "VERB", "root", 0, 13),
            word(4, "by", "by", "ADP", "case", 5, 23),
            word(5, "Henry", "Henry", "PROPN", "obl", 3, 26),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(PassCompl CTX_announce (OpenPN "Henry"))',
        )

    def test_passive_without_a_by_agent_is_out_of_scope(self) -> None:
        # grammar/Metonymy.gf's PassCompl always needs an agent NP -- no
        # bare-passive alternative exists in the grammar at all.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 9),
            word(3, "announced", "announce", "VERB", "root", 0, 13),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


class RelativeClauseTests(unittest.TestCase):
    def test_relative_clause_on_the_object(self) -> None:
        # "Waterloo praises Tolstoy, (that) announces Henry" -- a
        # relativized *object* shape, the relativizer itself elided (as
        # real UD "acl:relcl" annotations correctly do when it's
        # dropped), since ModifyRelVP's own shape ("NP which VP") has no
        # room for a relative clause with its own separate subject word
        # (see test_relative_clause_with_its_own_subject_is_out_of_scope
        # below) -- ModifyRelVP's own linearization always says
        # "which"/"that" regardless of what the original relative
        # pronoun even was, so there's nothing to separately represent.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "announces", "announce", "VERB", "acl:relcl", 3, 26),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 36),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_praise (ModifyRelVP (OpenPN "Tolstoy") '
            '(Compl CTX_announce (OpenPN "Henry"))))',
        )

    def test_relative_clause_with_its_own_subject_is_out_of_scope(self) -> None:
        # ModifyRelVP's own shape ("NP which VP") has no room for the
        # relative clause's own separate subject.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "who", "who", "PRON", "nsubj", 5, 26),
            word(5, "announces", "announce", "VERB", "acl:relcl", 3, 30),
            word(6, "Henry", "Henry", "PROPN", "obj", 5, 40),
        ]
        self.assertIsNone(build_gf_tree(words, "praise", GF_FUNCTIONS))


class FrontedDateClauseTests(unittest.TestCase):
    def test_on_fronted_date(self) -> None:
        # "On 2010, Waterloo announces Henry"
        words = [
            word(1, "On", "on", "ADP", "case", 2, 0),
            word(2, "2010", "2010", "PROPN", "obl", 4, 3),
            word(3, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 10),
            word(4, "announces", "announce", "VERB", "root", 0, 19),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 29),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'OnFrontedS (OpenPN "2010") '
            '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry")))',
        )

    def test_in_and_from_fronted_dates(self) -> None:
        for preposition, constructor in (("In", "InFrontedS"), ("From", "FromFrontedS")):
            with self.subTest(preposition=preposition):
                words = [
                    word(1, preposition, preposition.lower(), "ADP", "case", 2, 0),
                    word(2, "2010", "2010", "PROPN", "obl", 4, len(preposition) + 1),
                    word(
                        3, "Waterloo", "Waterloo", "PROPN", "nsubj", 4,
                        len(preposition) + 7,
                    ),
                    word(
                        4, "announces", "announce", "VERB", "root", 0,
                        len(preposition) + 16,
                    ),
                    word(
                        5, "Henry", "Henry", "PROPN", "obj", 4,
                        len(preposition) + 26,
                    ),
                ]
                tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
                self.assertEqual(
                    tree,
                    f'{constructor} (OpenPN "2010") '
                    '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry")))',
                )

    def test_a_trailing_non_fronted_date_oblique_is_out_of_scope(self) -> None:
        # The same "on"+obl shape, but positioned *after* the subject --
        # not fronted, so not this construction (and general trailing
        # oblique-PP attachment is out of scope entirely -- see the
        # module docstring).
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 4, 19),
            word(4, "on", "on", "ADP", "case", 6, 25),
            word(5, "2010", "2010", "PROPN", "obl", 2, 28),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


class SubordinateClauseTests(unittest.TestCase):
    def test_fronted_because_clause(self) -> None:
        # "Because Tolstoy announces Henry, Waterloo announces Mary"
        words = [
            word(1, "Because", "because", "SCONJ", "mark", 3, 0),
            word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, 8),
            word(3, "announces", "announce", "VERB", "advcl", 6, 16),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 26),
            word(5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 34),
            word(6, "announces", "announce", "VERB", "root", 0, 43),
            word(7, "Mary", "Mary", "PROPN", "obj", 6, 53),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'BecauseS (Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry"))) '
            '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Mary")))',
        )

    def test_trailing_although_clause(self) -> None:
        # "Waterloo announces Mary, although Tolstoy announces Henry"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Mary", "Mary", "PROPN", "obj", 2, 19),
            word(4, "although", "although", "SCONJ", "mark", 6, 25),
            word(5, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 6, 34),
            word(6, "announces", "announce", "VERB", "advcl", 2, 42),
            word(7, "Henry", "Henry", "PROPN", "obj", 6, 52),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'SAlthoughS (Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Mary"))) '
            '(Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry")))',
        )

    def test_if_and_when_both_map_correctly(self) -> None:
        for subordinator, fronted_constructor in (("if", "IfS"), ("when", "WhenS")):
            with self.subTest(subordinator=subordinator):
                words = [
                    word(1, subordinator.capitalize(), subordinator, "SCONJ", "mark", 3, 0),
                    word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, len(subordinator) + 1),
                    word(
                        3, "announces", "announce", "VERB", "advcl", 6,
                        len(subordinator) + 9,
                    ),
                    word(4, "Henry", "Henry", "PROPN", "obj", 3, len(subordinator) + 19),
                    word(
                        5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6,
                        len(subordinator) + 27,
                    ),
                    word(
                        6, "announces", "announce", "VERB", "root", 0,
                        len(subordinator) + 36,
                    ),
                    word(7, "Mary", "Mary", "PROPN", "obj", 6, len(subordinator) + 46),
                ]
                tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
                self.assertEqual(
                    tree,
                    f'{fronted_constructor} '
                    '(Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry"))) '
                    '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Mary")))',
                )

    def test_an_unrecognized_subordinator_is_out_of_scope(self) -> None:
        words = [
            word(1, "Since", "since", "SCONJ", "mark", 2, 0),
            word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, 6),
            word(3, "announces", "announce", "VERB", "advcl", 6, 14),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 24),
            word(5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 32),
            word(6, "announces", "announce", "VERB", "root", 0, 41),
            word(7, "Mary", "Mary", "PROPN", "obj", 6, 51),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


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
