# Metonymy-decoding pilot (2 examples)

Two real sentences from WiMCor v1.1 (Mathews et al., CC BY-SA 3.0), reproduced
here under that license's quotation/attribution terms, testing a different
and more specific claim than `evaluation/pilot-curated-wimcor/`: not "is this
metonymic" (binary detection) but **"decode the metonymy"** -- given the
literal place a name denotes, does the formal tower's graph search recover
the *specific real institution* the sentence actually means, and does Agda
accept that derivation?

| id | sentence source (surface) | source QID (the place, literal referent) | gold decode target (the institution actually meant) |
|---|---|---|---|
| wimcor-decode:pomona | "He attended Pomona." | Q486868 (Pomona, California -- the city) | Q7227384 (Pomona College) |
| wimcor-decode:leicester | "He attended Leicester." | Q83065 (Leicester -- the city) | Q1333399 (University of Leicester) |

Both bridges are real, independently confirmed Wikidata claims (not
fabricated for this test): `Q7227384 --P131--> Q486868` (Pomona College is
located in the city of Pomona) and `Q1333399 --P276--> Q83065` (University of
Leicester's location is the city of Leicester) -- verified directly against
the live Wikidata API before building this fixture (see
`docs/contextual-tower.md`).

`wikidata-snapshot/aliases.jsonl` is pruned to exactly one alias entry each
for the literal strings "Pomona" and "Leicester" (the city QID). The first
CI run found the raw materialized snapshot carried other real Wikidata
entities sharing that surface text too -- a train station (Pomona North,
Q7227377), a football club (Leicester City F.C., Q19481), a historical
parliamentary constituency (Q60576080), a near-duplicate administrative-unit
entity for the same city (City of Leicester, Q21683242), and even the gold
answer itself (Pomona College's own label includes "Pomona" as an alias,
Q7227384) -- and the engine correctly refused to guess among them
(`"status": "source-disambiguation-ambiguous"`), rather than silently picking
one. Removing the extra entries is curation of which real alias is *active*
for this small fixture, not fabrication of a link that doesn't exist.

**Important methodological note, learned from an earlier mistake in this same
investigation**: the *source* QID here is deliberately the literal place, not
the institution -- linking "Pomona" straight to Pomona College would make the
test vacuous (source already equals the answer, no bridging tested at all).
The point of this fixture is to test whether the tower's graph search
actually *finds* the institution starting only from the place, constrained by
what the verb ("attend") requires of its argument.

A third candidate (Houghton -> Houghton University) was investigated and
dropped: Wikidata's own P131 claim for Houghton University resolves only to
the state of New York (Q1384), not the specific place (Q3462000) -- the
bridge isn't recoverable from Wikidata's own graph as currently populated, a
genuine data-completeness gap, not a system fault.

`wikidata-snapshot/` is a small, purpose-built graph snapshot (source place +
gold institution QIDs both seeded explicitly, depth 1) -- enough to test
whether `contextualFiber`'s graph walk, constrained by the real VerbNet
selectional preference for "attend," actually reaches the gold QID, and
whether Agda's `runtimeCheck` accepts that specific derivation.

Scored with `scripts/evaluation/score_qid_fibers.py` (exact QID-in-fiber
matching), the same tool the checked-in `evaluation/contextual-multidomain/`
silver/audited fixtures use -- not the weaker metonymic-vs-literal detection
`evaluation/pilot-curated-wimcor/` uses, because this fixture's whole point is
to test the *specific* decoded answer, not just a binary judgment.
