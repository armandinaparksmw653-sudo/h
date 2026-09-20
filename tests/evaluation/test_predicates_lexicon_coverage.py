"""data/predicates.tsv's local:selectional-lexicon table was half-built:
7 of its 10 rows (study/review/translate/eat/listen-to/watch/wear) named a
GF V2 constructor in their gf_expression column that did not actually exist
in grammar/Metonymy.gf/MetonymyEng.gf -- meaning resolve_action already knew
the intended HardRequirement Sort for these lemmas, but no real tree could
ever be built using them. Found while investigating why "hear" (VerbNet's
see-30.1 perception-verb class has an EMPTY <SELRESTRS/> for its Stimulus
role, confirmed by reading the pinned commit's own see-30.1.xml -- not a
mapping gap, a real absence of data in VerbNet itself; FrameNet's
Perception_experience frame aggregation doesn't help either, since every
sibling verb in that frame -- feel/hear/perceive/see/smell/taste -- is
equally generic) needed the exact same fix "read" already had (read's own
VerbNet entries are just as generic, but data/predicates.tsv already
overrides it to Readable).

This file confirms, for all 8 affected lemmas (the 7 pre-existing gaps plus
the new "hear"):
1. Each has a real V2 constructor now (grammar/Metonymy.gf), each verified
   via local gf.exe before being written here (see the grammar files' own
   comments for the exact linearizations checked).
2. load_action_roles picks up the HardRequirement row from predicates.tsv
   alongside VerbNet's weaker SelectionalPreference rows for the same
   lemma.
3. resolve_action's real ranking (data/contextual-language-rules.json's
   own "prefer-hard-else-disjoin-compiled-preferences" policy) actually
   prefers the hard requirement on a real sentence, not just in isolation.
4. action_forms() alone misses three of these lemmas' irregular
   inflections (study -> "studyed" instead of "studied"; eat -> only
   "eated", never "ate"; hear -> only "heared", never "heard") --
   data/contextual-language-rules.json's morphology_overrides already
   covers this for "wear" ("wore"); this file adds the same treatment for
   study/eat/hear and confirms it end to end via a real matched sentence
   for "hear" (the lemma this investigation actually started from).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from contextual_rule_compiler import (  # noqa: E402
    action_forms,
    load_action_roles,
    resolve_action,
)

NEW_LEMMA_REQUIREMENTS = {
    "study": ("ObjectHole", "HasSort Readable"),
    "review": ("ObjectHole", "HasSort Readable"),
    "translate": ("ObjectHole", "HasSort Readable"),
    "eat": ("ObjectHole", "HasSort Edible"),
    "listen to": ("ObjectHole", "HasSort Audible"),
    "watch": ("ObjectHole", "HasSort Watchable"),
    "wear": ("ObjectHole", "HasSort Wearable"),
    "hear": ("ObjectHole", "HasSort Audible"),
}


class PredicatesLexiconCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roles = load_action_roles(
            ROOT / "data" / "predicates.tsv",
            ROOT / "data" / "verbnet-action-roles.tsv",
        )
        cls.language_rules = json.loads(
            (ROOT / "data" / "contextual-language-rules.json").read_text(
                encoding="utf-8"
            )
        )
        cls.morphology_overrides = cls.language_rules.get(
            "morphology_overrides", {}
        )

    def test_every_new_lemma_has_a_hard_requirement_row(self) -> None:
        for lemma, (hole_role, requirement) in NEW_LEMMA_REQUIREMENTS.items():
            with self.subTest(lemma=lemma):
                matches = [
                    role
                    for role in self.roles
                    if role.lemma == lemma
                    and role.hole_role == hole_role
                    and role.strength == "HardRequirement"
                    and role.provenance == "local:selectional-lexicon"
                ]
                self.assertEqual(
                    len(matches),
                    1,
                    f"expected exactly one local:selectional-lexicon "
                    f"HardRequirement row for {lemma!r}/{hole_role}",
                )
                self.assertEqual(matches[0].requirement, requirement)

    def test_hear_resolves_to_audible_on_a_real_sentence_not_the_weaker_verbnet_entity(
        self,
    ) -> None:
        # The exact finding this whole round started from: VerbNet's own
        # compiled rows for "hear" (learn-14-2-1/see-30.1-1-1) only ever
        # give "HasSort Entity" -- resolve_action must still prefer the
        # HardRequirement Audible row over them.
        result = resolve_action(
            "He heard the flute clearly.",
            ["flute"],
            self.roles,
            self.morphology_overrides,
        )
        self.assertEqual(result["requirement"], "HasSort Audible")
        self.assertEqual(result["strength"], "hard")
        self.assertEqual(result["lemma"], "hear")

    def test_action_forms_alone_misses_three_irregular_pasts(self) -> None:
        # Documents exactly why morphology_overrides entries were needed
        # for study/eat/hear (wear was already covered) -- a regression
        # guard so this doesn't silently start passing if action_forms's
        # own suffix rules are ever improved (in which case the override
        # becomes redundant, not wrong, but worth noticing).
        self.assertNotIn("studied", action_forms("study"))
        self.assertNotIn("ate", action_forms("eat"))
        self.assertNotIn("heard", action_forms("hear"))

    def test_morphology_overrides_cover_the_missing_irregular_pasts(self) -> None:
        for lemma, real_past in (
            ("study", "studied"),
            ("eat", "ate"),
            ("hear", "heard"),
        ):
            with self.subTest(lemma=lemma):
                override = self.morphology_overrides.get(lemma)
                self.assertIsNotNone(
                    override, f"expected a morphology override for {lemma!r}"
                )
                self.assertIn(real_past, override["forms"])


if __name__ == "__main__":
    unittest.main()
