#!/usr/bin/env python3
"""LLM tier: propose a clause structure for build_gf_tree_from_llm_structure.

Third tier of run_automatic_contextual_pipeline.py's tree-source chain
(Stanza-UD build_gf_tree -> this -> legacy `engine parse` on raw text).
An UNTRUSTED proposer, architecturally identical in status to the other
two: `engine linearize` (grammar/Metonymy.gf's own real type checker)
validates whatever tree scripts.build_gf_tree_from_dependencies.
build_gf_tree_from_llm_structure builds from this module's output before
it is ever trusted, and nothing this module or that renderer produces
reaches the Haskell/Agda formal core directly -- only the constraints
compile_gf_constraints later derives from a tree already do (see
run_automatic_contextual_pipeline.py's own module docstring). See
docs/contextual-tower.md's "Phase 1.5: LLM as a third tree-source tier"
for the full epistemic framing (the same one already used for the LLM
promotion-evidence pilot: Agda checks the *form* of what is proposed,
never the truth of a natural-language understanding claim).

Talks to a local Ollama server via scripts/propose_promotion_evidence.py's
own query_ollama -- no API key, no per-call cost, nothing to add as a
repository secret. Reused directly rather than duplicated.

This tier's own advantage over the UD-based one: it never needs to find
"the governing verb" independently -- the caller already knows which
verb (by lemma) resolve_action resolved, so the prompt just asks the
model for that verb's own subject/object directly. This sidesteps the
exact structural gap Phase 1 round 5 found in the UD-based tier (a
target's governing verb need not be the sentence's own UD root).
"""

from __future__ import annotations

from typing import Any, Callable

from propose_promotion_evidence import (  # noqa: F401 (DEFAULT_* re-exported)
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    query_ollama,
)

PROMPT_TEMPLATE = """You are extracting the grammatical structure of one English sentence for a formal semantics pipeline. You are given the sentence and the lemma of its main verb. Identify ONLY that verb's own subject and object (or object and "by"-agent, if the verb is passive) as literal noun phrases copied from the sentence -- never paraphrase, never invent words not in the sentence.

Sentence: {sentence}
Verb lemma: {lemma}

Respond with strict JSON only, no other text, matching exactly this schema:
{{"voice": "active" or "passive",
  "subject": NP or null,
  "object": NP or null,
  "agent": NP or null}}

"object" is used only when voice is "active"; "agent" (the "by X" phrase) only when voice is "passive" -- the other of the two is always null.

An NP is exactly one of:
- {{"kind": "proper_noun", "tokens": [...]}} -- 1 to 3 exact tokens copied from the sentence, in order, for a proper name (person/place/organization)
- {{"kind": "pronoun", "pronoun": "he" or "she" or "it" or "they"}}
- {{"kind": "common_noun", "determiner": "a" or "the", "noun": "...", "adjective": "..." or null}} -- "noun" is a single singular-form word, "adjective" is a single word or null

If you are not confident about ANY part of this -- the verb's subject/object isn't one of these three simple shapes, there's a modifier or coordination you can't represent this way, the sentence doesn't actually contain this verb as its own main clause -- respond with {{"voice": null, "subject": null, "object": null, "agent": null}} instead. Never guess."""


def build_prompt(sentence: str, lemma: str) -> str:
    return PROMPT_TEMPLATE.format(sentence=sentence, lemma=lemma)


def propose_clause_structure(
    sentence: str, lemma: str, query: Callable[[str], dict]
) -> dict[str, Any] | None:
    """The parsed structure dict, or None on any failure or explicit
    "not confident" response.

    Any failure at all -- network error, non-JSON response, missing
    keys, or the model's own "voice": null abstention -- degrades to
    None here, uniformly; build_gf_tree_from_llm_structure_decline_reason
    is what a caller uses to tell those apart afterward (via
    run_automatic_contextual_pipeline.py's own "no-response" vs. a
    build_gf_tree_from_llm_structure-derived reason), not this function,
    which never raises.
    """
    prompt = build_prompt(sentence, lemma)
    try:
        response = query(prompt)
    except Exception:  # noqa: BLE001 - any failure -> safe None
        return None
    if not isinstance(response, dict) or response.get("voice") is None:
        return None
    return response
