#!/usr/bin/env python3
"""Build a GF abstract-syntax tree directly from a UD dependency parse.

Phase 1 of the "Stanza instead of GF-as-parser" transition (see
docs/contextual-tower.md's own section on this and the plan file this
session used). Today, run_automatic_contextual_pipeline.py asks GF's own
parser to turn a raw English sentence into a tree -- meaning every
sentence shape GF hasn't been hand-taught a grammar rule for fails with
gf-parse-empty, however semantically simple it is. This module instead
walks a UD dependency graph (already computed once, offline, by
annotate_dependency_hints.py -- the same tool resolve_action's own
dependency_hint already relies on) and constructs the *text* of a GF
tree directly, in the exact syntax grammar/Metonymy.gf's constructors
already define. compile_gf_constraints (contextual_rule_compiler.py)
consumes tree text with its own, GF-independent parse_gf_tree/ARITIES
walker -- so a hand-built tree in the same syntax is a drop-in
replacement for one GF's parser would have produced; nothing downstream
of it (the TSV-encoded constraints that actually reach the Haskell/Agda
formal core) changes shape at all. See run_automatic_contextual_pipeline.py
for where this plugs in: try this first, and only fall back to asking
GF's own parser to read the raw sentence when this returns None.

Deliberately narrow on purpose (see docs/contextual-tower.md for why an
incremental, CI-measured rollout beats trying to cover all of UD at
once): only the simplest possible transitive clause -- a single root
verb with exactly one nsubj and exactly one obj/iobj, each a proper noun
(1-3 compound-chained tokens, matching OpenPN/OpenPN2/OpenPN3's own
existing token-count limit) or a personal pronoun (he/she/it/they).
Anything else -- a passive, a PP modifier, coordination, a relative
clause, a determiner, more than one clause -- returns None rather than
risk building an inaccurate tree; the caller's contract is to fall back
to the legacy GF-parser-on-raw-text path whenever this does, so the
worst case is byte-identical to today's behaviour, never a regression.
"""

from __future__ import annotations

from typing import Any

# Every UD word in the sentence must have one of these deprels for Phase
# 1 to even attempt a tree -- anything else (obl, amod, nmod, advcl,
# xcomp, ccomp, aux:pass, mark, cc, conj, appos, acl, det, ...) means the
# sentence needs a construction this narrow first slice doesn't build,
# so build_gf_tree bails out to None rather than silently drop or
# misrepresent that content. "det" is deliberately excluded too: proper
# nouns/pronouns (the only NPs this phase builds) essentially never take
# one in real WiMCor/ConMeC text, and silently ignoring a real one would
# mean dropping meaningful content, which this module never does.
_PHASE1_ALLOWED_DEPRELS = {"root", "nsubj", "obj", "iobj", "compound", "punct"}

_PRONOUN_CONSTRUCTORS = {
    "he": "HePN",
    "she": "ShePN",
    "it": "ItPN",
    "they": "TheyPN",
}

_PROPER_NOUN_CONSTRUCTORS = {1: "OpenPN", 2: "OpenPN2", 3: "OpenPN3"}


def _np_pieces(words: list[dict[str, Any]], head: dict[str, Any]) -> tuple[str, ...] | None:
    """The (constructor, *string-args) pieces for one NP, or None.

    Only ever builds from a PROPN (via its own direct "compound"
    children -- one level, matching this phase's own narrow scope) or a
    PRON whose lemma is one of he/she/it/they. Any other UPOS (a common
    noun, a numeral, ...) is out of scope for Phase 1.
    """
    if head["upos"] == "PROPN":
        chain = [head] + [
            word
            for word in words
            if word["head"] == head["id"]
            and word["deprel"] == "compound"
            and word["upos"] == "PROPN"
        ]
        chain.sort(key=lambda word: word["start_char"])
        constructor = _PROPER_NOUN_CONSTRUCTORS.get(len(chain))
        if constructor is None:
            return None
        return (constructor, *(word["text"] for word in chain))
    if head["upos"] == "PRON":
        constructor = _PRONOUN_CONSTRUCTORS.get(head["lemma"].casefold())
        if constructor is None:
            return None
        return (constructor,)
    return None


def _render_np(pieces: tuple[str, ...]) -> str | None:
    constructor, *args = pieces
    if any('"' in arg or "\\" in arg for arg in args):
        # Defensive only -- Stanza tokenizes a literal quote as its own
        # token, so a PROPN/PRON surface form realistically never
        # contains one. Bail rather than emit unparseable GF syntax.
        return None
    if not args:
        return constructor
    quoted = " ".join(f'"{arg}"' for arg in args)
    return f"({constructor} {quoted})"


def build_gf_tree(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str | None:
    """Build GF tree text for one clause, or None if Phase 1 can't.

    ``words`` is a flat list of UD word dicts -- the same shape
    annotate_dependency_hints.py's new "ud_words" hint field carries --
    each with "id", "head" (0 for the root), "deprel", "upos", "lemma",
    "text", "start_char", "end_char". ``lemma`` is the already-resolved
    action lemma (resolve_action/propose_contextual_scenario.py's
    "action" field) -- reused as-is, never recomputed here; this module
    only places it into a tree, using ``gf_function_by_lemma`` (a
    lemma -> "CTX_<hash>" reverse lookup built from
    data/contextual-gf-actions.json, the same source
    compile_gf_constraints already reads as its own "gf_actions") to
    find the matching V2 constructor GF's parser would otherwise have
    had to find via its own lexicon lookup.
    """
    if any(word["deprel"] not in _PHASE1_ALLOWED_DEPRELS for word in words):
        return None
    roots = [word for word in words if word["deprel"] == "root"]
    if len(roots) != 1:
        return None
    root = roots[0]
    if root["upos"] not in {"VERB", "AUX"}:
        return None
    subjects = [
        word for word in words if word["head"] == root["id"] and word["deprel"] == "nsubj"
    ]
    objects = [
        word
        for word in words
        if word["head"] == root["id"] and word["deprel"] in {"obj", "iobj"}
    ]
    if len(subjects) != 1 or len(objects) != 1:
        # grammar/Metonymy.gf has no intransitive VP (Compl/PassCompl
        # both require an object NP) -- an object-less clause is out of
        # scope for the whole grammar today, not just this phase.
        return None
    subject_pieces = _np_pieces(words, subjects[0])
    object_pieces = _np_pieces(words, objects[0])
    if subject_pieces is None or object_pieces is None:
        return None
    subject_np = _render_np(subject_pieces)
    object_np = _render_np(object_pieces)
    if subject_np is None or object_np is None:
        return None
    gf_function = gf_function_by_lemma.get(lemma)
    if gf_function is None:
        return None
    return f"Pred {subject_np} (Compl {gf_function} {object_np})"


def load_gf_function_by_lemma(actions_json: dict[str, Any]) -> dict[str, str]:
    """lemma -> "CTX_<hash>" reverse lookup from a loaded contextual-gf-actions.json.

    Mirrors run_automatic_contextual_pipeline.py's own
    ``{action["gf_function"]: action["lemma"] for ...}`` (the direction
    compile_gf_constraints needs), just inverted for this module's own
    lemma-to-function direction.
    """
    return {
        action["lemma"]: action["gf_function"] for action in actions_json["actions"]
    }
