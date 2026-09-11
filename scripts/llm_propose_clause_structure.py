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
- {{"kind": "common_noun", "determiner": "a", "an", or "the", "noun": "...", "adjective": "..." or null}} -- "noun" is a single singular-form word, "adjective" is a single word or null

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
    None here, uniformly. See propose_clause_structure_with_reason for
    a version that tells these apart, using the same single query()
    call this function makes.
    """
    structure, _reason = propose_clause_structure_with_reason(sentence, lemma, query)
    return structure


def propose_clause_structure_with_reason(
    sentence: str, lemma: str, query: Callable[[str], dict]
) -> tuple[dict[str, Any] | None, str]:
    """(structure, decline_reason) from exactly one query() call --
    decline_reason is "" whenever structure is not None.

    A real corpus evaluation run showed propose_clause_structure's own
    None outcome dominating (52/92 Stanza-declined WiMCor rows, 91/108
    ConMeC ones) with no way to tell whether that was the model
    correctly and conservatively abstaining (working as intended -- the
    whole point of its explicit "not confident, don't guess"
    instruction) or a technical failure worth investigating
    (network/timeout, or the model not following the JSON schema at
    all). This distinguishes four reasons, closed-vocabulary and safe
    (no sentence text, no model output text):
    - "query-exception": query() itself raised (network error, timeout,
      HTTP error, or query_ollama's own JSON-decoding of the model's
      raw text response failing).
    - "non-dict-response": query() returned, but not a JSON object at
      all -- the model's raw output didn't even parse as the expected
      shape.
    - "missing-voice-key": a JSON object, but without a "voice" key at
      all -- schema non-compliance, distinct from an explicit null.
    - "voice-null-abstention": a well-formed response where the model
      explicitly followed the prompt's "not confident -> voice: null"
      instruction -- this one specifically is *not* a failure, it is
      the tier working as designed.

    Deliberately does NOT re-call query() to get this detail (unlike
    build_gf_tree_decline_reason's safe re-run of the same deterministic
    Python logic) -- a second call here would hit the model itself
    again, which is neither free nor guaranteed to reproduce the first
    call's answer.
    """
    prompt = build_prompt(sentence, lemma)
    try:
        response = query(prompt)
    except Exception:  # noqa: BLE001 - any failure -> a closed reason code
        return None, "query-exception"
    if not isinstance(response, dict):
        return None, "non-dict-response"
    if "voice" not in response:
        return None, "missing-voice-key"
    if response["voice"] is None:
        return None, "voice-null-abstention"
    return response, ""
