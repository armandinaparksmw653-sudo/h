#!/usr/bin/env python3
"""Build a GF abstract-syntax tree directly from a UD dependency parse.

Phase 1+ of the "Stanza instead of GF-as-parser" transition (see
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

Every accept path here was verified directly against the local GF
toolchain (`gf.exe`'s own `l -lang=MetonymyEng`, not just read from
source) before being written into this module -- including one real,
previously undocumented finding: PossNP/DefCN/IndefCN/ModifyRelCN/
ModifyRelCNVP (grammar/Metonymy.gf) cannot actually be constructed at
all today -- Metonymy.gf declares no function that *produces* a bare CN
from scratch, only ones that *consume* one, confirmed by GF's own type
checker rejecting `DefCN (OpenIndefCN ...)` with "Couldn't match
expected type CN against inferred type NP". (A handful of existing pure-
Python tests in tests/evaluation/test_compile_gf_constraints_copula_
relative_genitive.py exercise PossNP/DefCN with exactly that ill-typed
shape -- they test compile_gf_constraints's own tree-walking code
against text no real GF parse could ever produce, the same false-
confidence trap as the ApposCommaPN/OpenPN2 story earlier this project's
history; not fixed here, out of scope for this module.) Consequently
this module never builds a possessive (UD "nmod:poss") -- doing so needs
a grammar/Metonymy.gf addition first (a CN-producing base function), not
just a tree-builder change.

Also deliberately not built here, each for its own reason (see the
plan file / docs/contextual-tower.md for the full writeup):
- A copula clause ("Waterloo is a county") is UD-structured with a NOUN
  (not VERB/AUX) as its own root, which annotate_dependency_hints.py's
  classify_word never classifies as "direct-argument" (its
  GOVERNING_UPOS check requires VERB/AUX) -- so resolve_action itself
  never resolves an action for it, and the whole pipeline never reaches
  this module for such a sentence in the first place. Fixing this needs
  a new dep_status/resolve_action branch, not a tree-builder change.
- A verb-level oblique PP adjunct ("announces X in Y", the "in Y" part)
  has no VP-level attachment point in grammar/Metonymy.gf at all --
  ModifyNP only attaches a PP to a specific NP, not to a VP. Folding it
  into the object NP anyway ("announces (X in Y)") would silently
  reinterpret which constituent the PP modifies -- exactly the "wrong
  but type-correct" failure mode this module exists to avoid, so it
  isn't attempted. The one narrow exception: a *fronted* date/time PP at
  the very start of a sentence (OnFrontedS/InFrontedS/FromFrontedS)
  *is* built (below) -- those constructors take the PP's own NP
  directly and hardcode the preposition, so there is no attachment
  ambiguity to resolve.
- Coordination (UD "conj"/"cc") is deferred pending a closer read of
  how compile_gf_constraints's first_node (a depth-first search for the
  first Compl/PassCompl) would attribute constraints when a tree has
  more than one -- a real subtlety a rushed implementation could get
  wrong silently, so it waits for its own dedicated round.
- Nested UD nmod (an NP modified by another NP/PP, "the museum in
  Kent") stays out of reach here for a different reason than the above:
  a target sitting inside one is rejected by resolve_action itself
  (dep_status == "nested-modifier") *before* this module would ever
  run, the same "Deliberately left unresolved" gap
  annotate_dependency_hints.py's own module docstring already names.

Every accept path tracks the set of word ids it has legitimately
consumed; if any word in the sentence is left over at the end (besides
punctuation, always silently ignored), the whole build declines
(returns None) rather than silently drop or misrepresent content -- the
same "only build when confident, otherwise fall back" contract Phase
1's original narrower version already used.

A real corpus evaluation run of Phase 1 (round 3 of this session's own
plan) measured *zero* successful uses of this module across 300 real
WiMCor/ConMeC rows (tree_source_counts: 100% "gf-parser") -- every
single row that reached tree-building fell all the way through to the
legacy path. To find out why without guessing, every ``_Bail`` here now
carries a closed-vocabulary reason code (see each raise site's own
comment), exposed via ``build_gf_tree_decline_reason`` -- a second,
diagnostics-only entry point run_automatic_contextual_pipeline.py calls
whenever ``build_gf_tree`` itself returns ``None``, purely to answer
that question with real data instead of another hypothesis.
"""

from __future__ import annotations

from typing import Any

_PRONOUN_CONSTRUCTORS = {
    "he": "HePN",
    "she": "ShePN",
    "it": "ItPN",
    "they": "TheyPN",
}

_PROPER_NOUN_CONSTRUCTORS = {1: "OpenPN", 2: "OpenPN2", 3: "OpenPN3"}

_INDEFINITE_DETERMINERS = {"a", "an"}
_DEFINITE_DETERMINERS = {"the"}

# grammar/MetonymyEng.gf's own fixed preposition words for the fronted
# date/time clause constructors -- the one exception to this module's
# "no verb-level oblique PP" rule (see the module docstring for why).
_FRONTED_DATE_CONSTRUCTORS = {
    "on": "OnFrontedS",
    "in": "InFrontedS",
    "from": "FromFrontedS",
}


class _Bail(Exception):
    """Internal control-flow only: this narrow builder hit a UD shape it
    doesn't (yet, safely) model. Always caught at _build_gf_tree_inner's
    two callers (build_gf_tree/build_gf_tree_decline_reason) -- never
    leaks. Carries a closed-vocabulary ``reason`` code (see each raise
    site's own comment for what it means and why it's safe to aggregate
    -- always one of a small, fixed set of internal check names, never
    sentence text).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _quote(text: str) -> str:
    if '"' in text or "\\" in text:
        # Defensive only -- Stanza tokenizes a literal quote as its own
        # token, so a real word surface form realistically never
        # contains one.
        raise _Bail("unsafe-text")
    return f'"{text}"'


def _apply(constructor: str, *args: str) -> str:
    if not args:
        return constructor
    return f"({constructor} {' '.join(args)})"


def _strip_outer_parens(tree: str) -> str:
    """GF's own tree printer (and every hand-written tree elsewhere in
    this project) never parenthesizes the outermost expression, only
    nested ones -- _apply above parenthesizes unconditionally (simplest
    to get right when composing arbitrarily deep, always-nested
    subexpressions), so build_gf_tree strips exactly one such layer off
    its own final result before returning it.
    """
    if tree.startswith("(") and tree.endswith(")"):
        return tree[1:-1]
    return tree


def _children(words: list[dict[str, Any]], head_id: int) -> list[dict[str, Any]]:
    return [word for word in words if word["head"] == head_id]


def _children_with_deprel(
    words: list[dict[str, Any]], head_id: int, deprel: str
) -> list[dict[str, Any]]:
    return [word for word in _children(words, head_id) if word["deprel"] == deprel]


def _np_from_proper_noun(
    words: list[dict[str, Any]], head: dict[str, Any], accounted: set[int]
) -> str:
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
        # Either the compound chain is longer than OpenPN3's 3-token
        # limit, or (impossible in practice, since `head` is always
        # included) somehow empty.
        raise _Bail("proper-noun-chain-too-long")
    for word in chain:
        accounted.add(word["id"])
    return _apply(constructor, *(_quote(word["text"]) for word in chain))


def _np_from_common_noun(
    words: list[dict[str, Any]], noun: dict[str, Any], accounted: set[int]
) -> str:
    determiners = _children_with_deprel(words, noun["id"], "det")
    adjectives = _children_with_deprel(words, noun["id"], "amod")
    if len(determiners) != 1 or len(adjectives) > 1:
        # No determiner at all, or more than one of either -- not
        # confident enough to guess a shape (OpenIndefCN/OpenDefCN/
        # OpenAdjIndefCN/OpenAdjDefCN each take exactly one determiner-
        # implied article and at most one adjective).
        raise _Bail("common-noun-determiner-or-adjective-count")
    determiner = determiners[0]
    det_lemma = determiner["lemma"].casefold()
    if det_lemma in _DEFINITE_DETERMINERS:
        is_definite = True
    elif det_lemma in _INDEFINITE_DETERMINERS:
        is_definite = False
    else:
        raise _Bail("common-noun-unrecognized-determiner")
    accounted.add(determiner["id"])
    accounted.add(noun["id"])
    noun_text = _quote(noun["text"])
    if adjectives:
        accounted.add(adjectives[0]["id"])
        constructor = "OpenAdjDefCN" if is_definite else "OpenAdjIndefCN"
        adjective_text = _quote(adjectives[0]["text"])
        # OpenAdjDefCN/OpenAdjIndefCN's third argument (grammar/Metonymy.gf:
        # String -> String -> String -> NP, "plural") is never read by
        # its own linearization (only "singular" is used) nor by
        # compile_gf_constraints's _noun_lemma (only arguments[1]) -- see
        # each's own comment. Reusing the same surface text for it loses
        # nothing.
        return _apply(constructor, adjective_text, noun_text, noun_text)
    constructor = "OpenDefCN" if is_definite else "OpenIndefCN"
    return _apply(constructor, noun_text, noun_text)


def _np_base(
    words: list[dict[str, Any]],
    head: dict[str, Any],
    accounted: set[int],
) -> str:
    """The base NP shape for one head word (proper noun / pronoun /
    common noun), with no relative-clause attachment -- factored out of
    _np so a caller that already knows what to do with an attached
    "acl:relcl" itself (see _implicit_subject_relative_clause_np) can
    still reuse this same per-UPOS dispatch without _np's own automatic
    ModifyRelVP wrapping kicking in a second time.
    """
    if head["upos"] == "PROPN":
        return _np_from_proper_noun(words, head, accounted)
    if head["upos"] == "PRON":
        constructor = _PRONOUN_CONSTRUCTORS.get(head["lemma"].casefold())
        if constructor is None:
            raise _Bail("pronoun-unrecognized")
        accounted.add(head["id"])
        return _apply(constructor)
    if head["upos"] == "NOUN":
        return _np_from_common_noun(words, head, accounted)
    # Anything else this module doesn't build an NP from at all -- NUM,
    # ADJ used substantively, a bare DET, etc.
    raise _Bail("np-unsupported-upos")


def _np(
    words: list[dict[str, Any]],
    head: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """Build one NP, including an attached relative clause if present.

    Dispatches on the head word's own UPOS for the base NP shape via
    _np_base, then separately checks for a UD "acl:relcl" child of the
    *same* head -- relative clauses can modify any of those three NP
    shapes, so this check lives above the per-UPOS dispatch, not inside
    any one branch of it.
    """
    base = _np_base(words, head, accounted)
    relative_clauses = _children_with_deprel(words, head["id"], "acl:relcl")
    if not relative_clauses:
        return base
    if len(relative_clauses) != 1:
        raise _Bail("relative-clause-count")
    embedded_vp = _relative_clause_vp(
        words, relative_clauses[0], accounted, gf_function_by_lemma
    )
    return _apply("ModifyRelVP", base, embedded_vp)


def _object_np(
    words: list[dict[str, Any]],
    verb_id: int,
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    objects = _children_with_deprel(words, verb_id, "obj") + _children_with_deprel(
        words, verb_id, "iobj"
    )
    if len(objects) != 1:
        # grammar/Metonymy.gf has no intransitive VP (Compl/PassCompl
        # both require an object NP) -- an object-less clause is out of
        # scope for the whole grammar today, not just this module.
        raise _Bail("object-count")
    return _np(words, objects[0], accounted, gf_function_by_lemma)


def _relative_clause_vp(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """The VP for a relative clause's own embedded verb.

    UD's "acl:relcl" attaches the embedded verb directly to the noun it
    modifies; the relativized noun itself fills the embedded clause's
    subject slot implicitly (no separate "nsubj" word for it), so this
    only ever looks for the embedded verb's own object -- and, unlike
    the main clause, does not need a caller-resolved lemma: it looks
    itself up by the embedded verb's own UD lemma directly, since it is
    a genuinely different predicate from the main action (a faithful
    structural mapping, not a semantic reinterpretation -- see the
    module docstring for why that distinction is what rules out a
    general oblique-PP attachment but not this).
    """
    if verb["upos"] not in {"VERB", "AUX"}:
        raise _Bail("relative-clause-verb-not-verb")
    if _children_with_deprel(words, verb["id"], "nsubj") or _children_with_deprel(
        words, verb["id"], "nsubj:pass"
    ):
        # A relative clause with its own separate subject isn't "which
        # VERB OBJECT" (ModifyRelVP's only shape) -- out of scope.
        raise _Bail("relative-clause-has-own-subject")
    gf_function = gf_function_by_lemma.get(verb["lemma"].casefold())
    if gf_function is None:
        raise _Bail("relative-clause-verb-not-in-lexicon")
    object_np = _object_np(words, verb["id"], accounted, gf_function_by_lemma)
    accounted.add(verb["id"])
    return _apply("Compl", gf_function, object_np)


def _fronted_date_clause(
    words: list[dict[str, Any]], root: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    """(oblique_word, case_word, constructor) for a fronted date/time
    oblique on the root verb, or None if there isn't one.

    Narrow by construction: the case word's own text must be exactly
    one of the three fixed prepositions grammar/MetonymyEng.gf's
    OnFrontedS/InFrontedS/FromFrontedS actually hardcode, and the whole
    oblique phrase must sit before the subject (a real fronted
    position), not merely exist somewhere in the sentence.
    """
    obliques = _children_with_deprel(words, root["id"], "obl")
    if len(obliques) != 1:
        return None
    oblique = obliques[0]
    case_children = _children_with_deprel(words, oblique["id"], "case")
    if len(case_children) != 1:
        return None
    case_word = case_children[0]
    constructor = _FRONTED_DATE_CONSTRUCTORS.get(case_word["text"].casefold())
    if constructor is None:
        return None
    subjects = _children_with_deprel(words, root["id"], "nsubj")
    if len(subjects) != 1 or oblique["start_char"] >= subjects[0]["start_char"]:
        return None
    return oblique, case_word, constructor


# grammar/MetonymyEng.gf's own fixed subordinating conjunctions -- each
# maps to a (fronted_constructor, trailing_constructor) pair
# ("Because EMBEDDED, MAIN" vs "MAIN, because EMBEDDED").
_SUBORDINATE_CLAUSE_CONSTRUCTORS = {
    "because": ("BecauseS", "SBecauseS"),
    "if": ("IfS", "SIfS"),
    "when": ("WhenS", "SWhenS"),
    "although": ("AlthoughS", "SAlthoughS"),
}


def _clause(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """"SubjectNP (Compl/PassCompl V2 ObjectNP)" for any verb -- shared
    by the main action clause and any embedded clause (relative,
    fronted/trailing subordinate) this module builds, since each is
    structurally the same shape, just with a different governing verb.
    """
    gf_function = gf_function_by_lemma.get(verb["lemma"].casefold())
    if gf_function is None:
        raise _Bail("verb-not-in-lexicon")

    passive_subjects = _children_with_deprel(words, verb["id"], "nsubj:pass")
    if passive_subjects:
        aux_pass = _children_with_deprel(words, verb["id"], "aux:pass")
        if len(aux_pass) != 1:
            raise _Bail("passive-aux-count")
        agents = [
            oblique
            for oblique in _children_with_deprel(words, verb["id"], "obl")
            if any(
                case["text"].casefold() == "by"
                for case in _children_with_deprel(words, oblique["id"], "case")
            )
        ]
        if len(agents) != 1:
            # grammar/Metonymy.gf's PassCompl always needs an agent NP
            # (V2 -> NP -> VP, no bare-passive alternative) -- a passive
            # without a "by"-agent is out of scope for the whole grammar
            # today, not just this module.
            raise _Bail("passive-agent-count")
        agent_np = _np(words, agents[0], accounted, gf_function_by_lemma)
        subject_np = _np(words, passive_subjects[0], accounted, gf_function_by_lemma)
        accounted.add(aux_pass[0]["id"])
        for case in _children_with_deprel(words, agents[0]["id"], "case"):
            accounted.add(case["id"])
        accounted.add(verb["id"])
        return _apply("Pred", subject_np, _apply("PassCompl", gf_function, agent_np))

    subjects = _children_with_deprel(words, verb["id"], "nsubj")
    if len(subjects) != 1:
        raise _Bail("subject-count")
    subject_np = _np(words, subjects[0], accounted, gf_function_by_lemma)
    object_np = _object_np(words, verb["id"], accounted, gf_function_by_lemma)
    accounted.add(verb["id"])
    return _apply("Pred", subject_np, _apply("Compl", gf_function, object_np))


def _word_by_governing_start(
    words: list[dict[str, Any]], governing_start: int
) -> dict[str, Any] | None:
    """The ud_words entry annotate_dependency_hints.py's classify_word
    actually pointed resolve_action at, given its own "governing_start"
    hint field -- not always a direct start_char match: for a passive
    clause, classify_word's own _passive_verb_span anchors
    governing_start to min(content_verb.start, aux_pass.start), which in
    real English is almost always the auxiliary's own start_char ("was
    announced" -- "was" starts first), never the content verb _clause
    actually needs to build a clause around. Resolves through exactly
    that one hop -- an "aux:pass" word is never itself the governing verb,
    only ever a modifier of one. (No such hop is needed for the other
    multi-word case, an obl+case phrasal verb like "listen to": there,
    governing_start is min(verb.start, preposition.start), and in real
    English the preposition always follows the verb, so that minimum is
    already the verb's own start_char -- the same word-order guarantee
    resolve_action's own obl-fallback fix already relies on.)

    Returns None on zero or more-than-one start_char match (the latter
    possible if two sub-words share a parent multi-word token's span) --
    either way, the caller degrades to declining, never guessing.
    """
    candidates = [word for word in words if word["start_char"] == governing_start]
    if len(candidates) != 1:
        return None
    candidate = candidates[0]
    if candidate["deprel"] == "aux:pass":
        heads = [word for word in words if word["id"] == candidate["head"]]
        return heads[0] if len(heads) == 1 else None
    return candidate


def _subtree_ids(words: list[dict[str, Any]], root_id: int) -> set[int]:
    """root_id plus every word transitively dependent on it (walking
    "head" pointers via the existing _children helper) -- scopes the
    embedded-governing-verb branch's own "did we account for everything"
    check to just the local clause it actually represents, the same
    "represent everything faithfully or decline" discipline
    _build_gf_tree_inner's whole-sentence version already applies to the
    root-anchored branch, just scoped down to this one clause.
    """
    ids = {root_id}
    frontier = [root_id]
    while frontier:
        current = frontier.pop()
        for child in _children(words, current):
            if child["id"] not in ids:
                ids.add(child["id"])
                frontier.append(child["id"])
    return ids


def _implicit_subject_relative_clause_np(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
) -> str | None:
    """The subject NP for a governing verb that is itself a UD
    "acl:relcl" with no own "nsubj"/"nsubj:pass" -- the relativized noun
    implicitly fills its subject role ("the county which governs
    Prussia"; contrast _relative_clause_vp, which already handles this
    exact shape, but only when SOME OTHER clause's object attaches it as
    a ModifyRelVP modifier -- this handles the case where the metonymy
    target itself is the argument this verb governs).

    Returns None when ``verb`` isn't this shape at all (a different verb
    entirely -- a real root-anchored clause, or an embedded verb with its
    own explicit subject), so the caller can fall through to its own
    ordinary _clause handling. Deliberately does NOT reuse _np on the
    head noun (that would also re-attach ``verb`` a second time, as a
    ModifyRelVP wrapper around the very subject this function is
    building) -- uses _np_base instead, after confirming the head noun
    has no *other* relative clause attached that would otherwise be
    silently dropped.

    A real corpus evaluation run found this dominates the new
    "subject-count" bucket the governing_start branch introduced --
    35/92 WiMCor and 43/122 ConMeC root-lemma-mismatch declines
    redistributed almost entirely into other, more specific reasons once
    root-lemma-mismatch itself was fixed, "subject-count" being the
    single largest of them (12/150, 13/150).
    """
    if verb["deprel"] != "acl:relcl":
        return None
    if _children_with_deprel(words, verb["id"], "nsubj") or _children_with_deprel(
        words, verb["id"], "nsubj:pass"
    ):
        return None
    heads = [word for word in words if word["id"] == verb["head"]]
    if len(heads) != 1:
        raise _Bail("governing-relcl-head-not-found")
    head_noun = heads[0]
    other_relative_clauses = [
        word
        for word in _children_with_deprel(words, head_noun["id"], "acl:relcl")
        if word["id"] != verb["id"]
    ]
    if other_relative_clauses:
        raise _Bail("governing-relcl-head-has-other-relative-clause")
    subject_np = _np_base(words, head_noun, accounted)
    accounted.add(head_noun["id"])
    return subject_np


def _main_clause(
    words: list[dict[str, Any]],
    root: dict[str, Any],
    lemma: str,
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """The S built around the resolved action's own root verb -- active
    or passive, matching whichever UD shape is actually present.
    """
    if root["lemma"].casefold() != lemma.casefold():
        # The resolved action's own lemma must be this same root verb's
        # lemma -- guards against two distinct real causes: (a)
        # resolve_action's positional fallback (used whenever
        # dependency_hint's dep_status isn't "direct-argument") having
        # matched an entirely different word than UD's own root; (b),
        # confirmed as the more likely dominant real-corpus cause by
        # re-reading annotate_dependency_hints.py's own classify_word --
        # even on the "direct-argument" path, the target's *governing*
        # verb (whatever word it's syntactically attached to) is not
        # required to be the *sentence's own* root at all, e.g. a target
        # embedded inside a relative/subordinate clause of a more
        # complex real sentence. Either way, building a tree around the
        # wrong clause must never happen silently.
        raise _Bail("root-lemma-mismatch")
    return _clause(words, root, accounted, gf_function_by_lemma)


def _subordinate_clause(
    words: list[dict[str, Any]], root: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str, str] | None:
    """(embedded_verb, mark_word, fronted_constructor, trailing_constructor)
    for a UD "advcl"+"mark" subordinate clause attached to the root verb,
    or None if there isn't exactly one recognizable one.

    UD attaches the embedded clause's own verb to the main verb via
    "advcl", with the subordinating word itself ("because"/"if"/"when"/
    "although") as that embedded verb's own "mark" child -- whichever of
    grammar/MetonymyEng.gf's four fixed subordinators it actually is.
    """
    advcls = _children_with_deprel(words, root["id"], "advcl")
    if len(advcls) != 1:
        return None
    embedded_verb = advcls[0]
    if embedded_verb["upos"] not in {"VERB", "AUX"}:
        return None
    marks = _children_with_deprel(words, embedded_verb["id"], "mark")
    if len(marks) != 1:
        return None
    mark = marks[0]
    pair = _SUBORDINATE_CLAUSE_CONSTRUCTORS.get(mark["text"].casefold())
    if pair is None:
        return None
    return embedded_verb, mark, pair[0], pair[1]


def _build_gf_tree_inner(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str:
    """The single implementation build_gf_tree and
    build_gf_tree_decline_reason both delegate to -- returns tree text
    (parens-stripped) on success, always raises _Bail (never returns
    None) on any unhandled UD shape, so a caller can choose whether it
    wants the resulting tree or the reason for its absence.

    ``governing_start`` is annotate_dependency_hints.py's own
    dependency_hint field of the same name -- the char offset of the
    word resolve_action actually resolved the target's role against.
    When it names a word other than the sentence's own UD root (a real
    corpus run found this dominates real-world failures: the target's
    governing verb is very often embedded in a relative/subordinate/
    complement clause of a more complex sentence, not the sentence's own
    root), this builds ONLY that local clause -- reusing the exact same
    _clause/_np/_object_np/_relative_clause_vp machinery the root-
    anchored path below already uses, since it is structurally the same
    shape, just a different governing verb -- and deliberately does not
    attempt to represent whatever wraps it (no fronted-date/subordinate-
    clause enrichment, no attaching it as a relative-clause modifier of
    some outer NP). This is safe, not merely convenient: compile_gf_
    constraints's own tree-walkers (first_node's depth-first Compl/
    PassCompl search, and walk's separate OpenAdjDefCN/OpenAdjIndefCN
    scan for FrameModifier/FrameComposition) only ever derive constraints
    from whatever tree they are actually given -- never anything "outside"
    it -- so omitting the wrapper can only under-generate constraints,
    never derive a wrong one, the same risk class already accepted for
    this module's other deliberately-unbuilt shapes (see the module
    docstring's verb-level-oblique-PP paragraph). When ``governing_start``
    is None (the caller has no such hint -- resolve_action fell back to
    its own positional heuristic) or it resolves to the sentence's own
    root, this is byte-for-byte today's existing root-anchored behavior.
    """
    roots = [word for word in words if word["deprel"] == "root"]
    if len(roots) != 1:
        raise _Bail("root-count")
    root = roots[0]
    if root["upos"] not in {"VERB", "AUX"}:
        raise _Bail("root-not-verb")

    if governing_start is not None:
        governing_word = _word_by_governing_start(words, governing_start)
        if governing_word is None:
            raise _Bail("governing-start-not-found")
        if governing_word["upos"] not in {"VERB", "AUX"}:
            raise _Bail("governing-word-not-verb")
        if governing_word["id"] != root["id"]:
            if governing_word["lemma"].casefold() != lemma.casefold():
                raise _Bail("governing-lemma-mismatch")
            accounted = set()
            implicit_subject_np = _implicit_subject_relative_clause_np(
                words, governing_word, accounted
            )
            if implicit_subject_np is not None:
                # The governing verb is itself a subject-relative
                # acl:relcl ("the county which governs Prussia") -- the
                # relativized head noun fills its subject role implicitly,
                # the same shape _relative_clause_vp already supports for
                # a relative clause attached elsewhere as a modifier, just
                # reused here since the metonymy target is the argument
                # THIS verb itself governs. A real corpus run found this
                # dominates "subject-count" (the single largest new
                # decline reason the governing_start branch introduced --
                # a bare _clause call has no notion of an implicit subject
                # at all, only ever looks for a literal "nsubj" child).
                gf_function = gf_function_by_lemma.get(lemma.casefold())
                if gf_function is None:
                    raise _Bail("verb-not-in-lexicon")
                object_np = _object_np(
                    words, governing_word["id"], accounted, gf_function_by_lemma
                )
                accounted.add(governing_word["id"])
                tree = _apply(
                    "Pred", implicit_subject_np, _apply("Compl", gf_function, object_np)
                )
            else:
                tree = _clause(words, governing_word, accounted, gf_function_by_lemma)
            for mark_word in _children_with_deprel(words, governing_word["id"], "mark"):
                # Wrapper information (the word that signals this clause
                # is itself embedded, e.g. "because") -- not local-clause
                # content, so it is explicitly excluded from the
                # completeness check below rather than left to trip
                # "embedded-leftover-words", the same technique the
                # existing subordinate-clause branch already uses for its
                # own "mark" word once it picks a Because/If/When/
                # Although constructor to account for it; here there is
                # no such wrapper constructor, so this is the only place
                # that ever accounts for it.
                accounted.add(mark_word["id"])
            subtree_ids = _subtree_ids(words, governing_word["id"])
            leftover = {
                word["id"]
                for word in words
                if word["id"] in subtree_ids and word["deprel"] != "punct"
            } - accounted
            if leftover:
                raise _Bail("embedded-leftover-words")
            return _strip_outer_parens(tree)

    accounted: set[int] = set()
    fronted_date = _fronted_date_clause(words, root)
    subordinate = _subordinate_clause(words, root) if fronted_date is None else None
    if fronted_date is not None:
        oblique, case_word, constructor = fronted_date
        date_np = _np(words, oblique, accounted, gf_function_by_lemma)
        accounted.add(case_word["id"])
        main = _main_clause(words, root, lemma, accounted, gf_function_by_lemma)
        tree = _apply(constructor, date_np, main)
    elif subordinate is not None:
        embedded_verb, mark, fronted_name, trailing_name = subordinate
        main_subjects = _children_with_deprel(words, root["id"], "nsubj")
        if len(main_subjects) != 1:
            raise _Bail("subject-count")
        is_fronted = embedded_verb["start_char"] < main_subjects[0]["start_char"]
        embedded = _clause(words, embedded_verb, accounted, gf_function_by_lemma)
        accounted.add(mark["id"])
        main = _main_clause(words, root, lemma, accounted, gf_function_by_lemma)
        tree = (
            _apply(fronted_name, embedded, main)
            if is_fronted
            else _apply(trailing_name, main, embedded)
        )
    else:
        tree = _main_clause(words, root, lemma, accounted, gf_function_by_lemma)
    leftover = {word["id"] for word in words if word["deprel"] != "punct"} - accounted
    if leftover:
        raise _Bail("leftover-words")
    return _strip_outer_parens(tree)


def build_gf_tree(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str | None:
    """Build GF tree text for one sentence, or None if it can't (yet).

    ``words`` is a flat list of UD word dicts -- the same shape
    annotate_dependency_hints.py's "ud_words" hint field carries --
    each with "id", "head" (0 for the root), "deprel", "upos", "lemma",
    "text", "start_char", "end_char". ``lemma`` is the already-resolved
    action lemma (resolve_action/propose_contextual_scenario.py's
    "action" field) -- reused as-is, never recomputed here; this module
    only places it into a tree. ``gf_function_by_lemma`` is a
    lemma -> "CTX_<hash>" reverse lookup built from
    data/contextual-gf-actions.json (see load_gf_function_by_lemma).
    ``governing_start`` is optional -- see _build_gf_tree_inner's own
    docstring for what it does when given; omitting it (the default)
    is byte-for-byte today's pre-existing root-anchored-only behavior.
    """
    try:
        return _build_gf_tree_inner(
            words, lemma, gf_function_by_lemma, governing_start
        )
    except _Bail:
        return None


def build_gf_tree_decline_reason(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str:
    """Empty string if build_gf_tree would succeed on the same input,
    else a closed-vocabulary reason code for why it declines (see each
    _Bail call site's own comment for the full vocabulary and what each
    one means) -- diagnostics only, reruns the exact same logic rather
    than being called from inside build_gf_tree, so the normal success
    path never pays for it. Every reason code names one of this
    module's own internal structural checks, never sentence text.
    """
    try:
        _build_gf_tree_inner(words, lemma, gf_function_by_lemma, governing_start)
        return ""
    except _Bail as bail:
        return bail.reason


def _np_from_llm_description(np: Any) -> str:
    """One NP from an LLM-proposed clause structure (see
    scripts/llm_propose_clause_structure.py's own docstring for the
    full JSON schema this consumes) -- reuses the exact same rendering
    primitives (_apply/_quote/_PROPER_NOUN_CONSTRUCTORS/
    _PRONOUN_CONSTRUCTORS) as the UD-tree-derived _np above, since both
    ultimately build the same three NP shapes; only how the shape is
    identified differs (UD upos/deprel vs. the LLM's own classification).
    Every failure mode raises _Bail with an "llm-"-prefixed reason code,
    distinct from the UD path's own vocabulary, so
    decline_reason_counts can tell which tier actually produced a given
    decline.
    """
    if not isinstance(np, dict):
        raise _Bail("llm-np-not-a-dict")
    kind = np.get("kind")
    if kind == "proper_noun":
        tokens = np.get("tokens")
        if not isinstance(tokens, list) or not tokens or not all(
            isinstance(token, str) and token for token in tokens
        ):
            raise _Bail("llm-proper-noun-tokens-invalid")
        constructor = _PROPER_NOUN_CONSTRUCTORS.get(len(tokens))
        if constructor is None:
            raise _Bail("llm-proper-noun-chain-too-long")
        return _apply(constructor, *(_quote(token) for token in tokens))
    if kind == "pronoun":
        pronoun = np.get("pronoun")
        constructor = _PRONOUN_CONSTRUCTORS.get(
            pronoun.casefold() if isinstance(pronoun, str) else ""
        )
        if constructor is None:
            raise _Bail("llm-pronoun-unrecognized")
        return _apply(constructor)
    if kind == "common_noun":
        noun = np.get("noun")
        if not isinstance(noun, str) or not noun:
            raise _Bail("llm-common-noun-missing-noun")
        determiner = np.get("determiner")
        if determiner == "the":
            is_definite = True
        elif determiner in _INDEFINITE_DETERMINERS:
            is_definite = False
        else:
            raise _Bail("llm-common-noun-unrecognized-determiner")
        noun_text = _quote(noun)
        adjective = np.get("adjective")
        if adjective is not None:
            if not isinstance(adjective, str) or not adjective:
                raise _Bail("llm-common-noun-invalid-adjective")
            constructor = "OpenAdjDefCN" if is_definite else "OpenAdjIndefCN"
            adjective_text = _quote(adjective)
            return _apply(constructor, adjective_text, noun_text, noun_text)
        constructor = "OpenDefCN" if is_definite else "OpenIndefCN"
        return _apply(constructor, noun_text, noun_text)
    raise _Bail("llm-np-unrecognized-kind")


def _build_gf_tree_from_llm_structure_inner(
    structure: Any,
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str:
    """The single implementation build_gf_tree_from_llm_structure and
    build_gf_tree_from_llm_structure_decline_reason both delegate to --
    mirrors _build_gf_tree_inner's own contract (always raises _Bail,
    never returns None, on any unhandled/invalid structure).
    """
    if not isinstance(structure, dict):
        raise _Bail("llm-structure-not-a-dict")
    gf_function = gf_function_by_lemma.get(lemma)
    if gf_function is None:
        # Same reason code the UD path's own _clause already uses for
        # this exact condition -- one shared vocabulary entry for "this
        # lemma has no compiled GF action", regardless of which tier
        # found that out.
        raise _Bail("verb-not-in-lexicon")
    voice = structure.get("voice")
    if voice == "passive":
        subject_description = structure.get("subject")
        agent_description = structure.get("agent")
        if subject_description is None or agent_description is None:
            raise _Bail("llm-passive-missing-np")
        subject_np = _np_from_llm_description(subject_description)
        agent_np = _np_from_llm_description(agent_description)
        return _apply("Pred", subject_np, _apply("PassCompl", gf_function, agent_np))
    if voice == "active":
        subject_description = structure.get("subject")
        object_description = structure.get("object")
        if subject_description is None or object_description is None:
            raise _Bail("llm-active-missing-np")
        subject_np = _np_from_llm_description(subject_description)
        object_np = _np_from_llm_description(object_description)
        return _apply("Pred", subject_np, _apply("Compl", gf_function, object_np))
    raise _Bail("llm-voice-unrecognized")


def build_gf_tree_from_llm_structure(
    structure: Any,
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str | None:
    """Build GF tree text from an LLM-proposed clause structure (the
    dict scripts/llm_propose_clause_structure.py's propose_clause_structure
    returns), or None if the structure is missing, malformed, or
    describes something this narrow first schema doesn't cover. Mirrors
    build_gf_tree's own contract exactly, just for a different (LLM-
    derived rather than UD-derived) structured input -- same lemma/
    gf_function_by_lemma reuse, same "never guess, only build when
    confident" discipline.
    """
    try:
        return _strip_outer_parens(
            _build_gf_tree_from_llm_structure_inner(structure, lemma, gf_function_by_lemma)
        )
    except _Bail:
        return None


def build_gf_tree_from_llm_structure_decline_reason(
    structure: Any,
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str:
    """Empty string if build_gf_tree_from_llm_structure would succeed on
    the same input, else a closed-vocabulary reason code -- mirrors
    build_gf_tree_decline_reason exactly, for the LLM-structure path.
    """
    try:
        _build_gf_tree_from_llm_structure_inner(structure, lemma, gf_function_by_lemma)
        return ""
    except _Bail as bail:
        return bail.reason


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
