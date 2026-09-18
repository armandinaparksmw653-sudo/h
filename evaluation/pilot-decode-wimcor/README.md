# Metonymy-decoding pilot (9 examples)

Nine real sentences from WiMCor v1.1 (Mathews et al., CC BY-SA 3.0), reproduced
here under that license's quotation/attribution terms, testing a different
and more specific claim than `evaluation/pilot-curated-wimcor/`: not "is this
metonymic" (binary detection) but **"decode the metonymy"** -- given the
literal place a name denotes, does the formal tower's graph search recover
the *specific real institution* the sentence actually means, and does Agda
accept that derivation?

All nine follow the same real, frequent WiMCor pattern -- a place name used
metonymically for an institution located there, via "attended"/"studied at"
("Everett Sharp ... attended Pomona.") -- found by a targeted text search
over the full 41,200-row WiMCor test split (549 candidates matched this
pattern alone; these nine were the first batch verified against real
Wikidata data, not cherry-picked for a particular outcome).

| id | sentence source (surface) | source QID (the place, literal referent) | gold decode target (the institution actually meant) |
|---|---|---|---|
| wimcor-decode:pomona | "He attended Pomona." | Q486868 (Pomona, California) | Q7227384 (Pomona College) |
| wimcor-decode:leicester | "He attended Leicester." | Q83065 (Leicester, the city) | Q1333399 (University of Leicester) |
| wimcor-decode:elon | "She then attended Elon." | Q2030224 (Elon, North Carolina) | Q4568893 (Elon University) |
| wimcor-decode:amherst | "Bix ... attended Amherst." | Q49164 (Amherst, Massachusetts) | Q49165 (Amherst College) |
| wimcor-decode:tartu | "Joachim Cronman attended Tartu." | Q13972 (Tartu, the city) | Q204181 (University of Tartu) |
| wimcor-decode:stirling | "She attended Stirling in Scotland." | Q182923 (Stirling, the city) | Q963530 (University of Stirling) |
| wimcor-decode:valparaiso | "He attended Valparaiso ..." | Q868888 (Valparaiso, Indiana) | Q186047 (Valparaiso University) |
| wimcor-decode:haifa | "Ya'alon studied at Haifa ..." | Q41621 (Haifa, the city) | Q591115 (University of Haifa) |
| wimcor-decode:princeton | "He attended Princeton ..." | Q138518 (Princeton, New Jersey) | Q21578 (Princeton University) |

Every bridge is a real, independently confirmed Wikidata claim (not
fabricated for this test) -- each institution's own P131/P159/P276 claim
verified directly against the live Wikidata API before being added here (see
`docs/contextual-tower.md`). Two candidates found by the same text search were
investigated and **dropped** because Wikidata's own graph doesn't record the
specific place -> institution link:
- **Houghton -> Houghton University**: the university's P131 claim resolves
  only to the state of New York (Q1384), not the specific census-designated
  place (Q3462000).
- **Lehigh -> Lehigh University**: the university's P131/P159 claims resolve
  to Bethlehem, Pennsylvania (Q164380) -- the city it's actually in -- not to
  any place literally named "Lehigh" (the name derives from the county/valley/
  river, not a place Wikidata records the university as located in).

Both are genuine data-completeness gaps in Wikidata as currently populated,
not a fault of this project's formal machinery -- recorded here so a later
attempt doesn't have to re-discover the same dead end.

`wikidata-snapshot/aliases.jsonl` is pruned to exactly one alias entry per
surface string (the intended city/town QID). The first CI run of the
2-example version of this fixture found the raw materialized snapshot carried
other real Wikidata entities sharing the same surface text too -- a train
station (Pomona North, Q7227377), a football club (Leicester City F.C.,
Q19481), a historical parliamentary constituency (Q60576080), a
near-duplicate administrative-unit entity for the same city (City of
Leicester, Q21683242), and even the gold answer itself (Pomona College's own
label includes "Pomona" as an alias, Q7227384) -- and the engine correctly
refused to guess among them (`"status": "source-disambiguation-ambiguous"`)
rather than silently picking one. The same pruning was applied to all nine
surfaces here from the start. Removing the extra alias entries is curation of
which real alias is *active* for this small fixture, not fabrication of a
link that doesn't exist.

**Important methodological note, learned from an earlier mistake in this same
investigation**: every source QID here is deliberately the literal place, not
the institution -- linking "Pomona" straight to Pomona College would make the
test vacuous (source already equals the answer, no bridging tested at all).
The point of this fixture is to test whether the tower's graph search
actually *finds* the institution starting only from the place, constrained by
what the verb ("attend"/"study") requires of its argument.

`wikidata-snapshot/` is a small, purpose-built graph snapshot (every source
place and every gold institution QID seeded explicitly, depth 1) -- enough to
test whether `contextualFiber`'s graph walk, constrained by the real VerbNet
selectional preference for "attend"/"study," actually reaches each gold QID,
and whether Agda's `runtimeCheck` accepts that specific derivation.

Scored with `scripts/evaluation/score_qid_fibers.py` (exact QID-in-fiber
matching), the same tool the checked-in `evaluation/contextual-multidomain/`
silver/audited fixtures use -- not the weaker metonymic-vs-literal detection
`evaluation/pilot-curated-wimcor/` uses, because this fixture's whole point is
to test the *specific* decoded answer, not just a binary judgment.

**Result from the first 2-example run (Pomona, Leicester), for context**: the
gold QID was present in the fiber for both (recall 2/2), but the fiber wasn't
narrowed to a single candidate for either (exact match 0/2, 77 and 289
surviving candidates respectively) -- the only constraint available,
`Prefers (HasSort Entity)@attend`, eliminated nothing (`Entity` is the
universal top sort). This 9-example run exists to see whether that pattern
holds at a larger (if still small) scale, not to fix it -- narrowing further
would require either a sharper linguistic constraint than VerbNet's
selectional preference for "attend"/"study" currently supplies, or additional
context words in the sentence contributing their own constraints (as the
already-checked-in `evaluation/contextual-multidomain/silver-inputs.jsonl`
"commercial agreement" vs. "political agreement" pair demonstrates on
synthetic data).
