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

**Result from the 9-example run through the full automatic frontend, and why
`pilot-scenarios.tsv` exists**: running all 9 through `pilot-inputs.jsonl` (the
full pipeline -- Stanza dependency parsing, then GF tree construction, then
legacy-GF-parser fallback) found only 2 of 9 (Pomona, Leicester) built a tree
via Stanza cleanly; 4 (Elon, Valparaiso, Haifa, Princeton) failed to build any
tree at all on real WiMCor sentence complexity; and 3 (Amherst, Tartu,
Stirling) fell back to the legacy GF-parser, which for Amherst produced a
**structurally nonsensical** tree (`ModifyNP (OpenPN3 "Bix" "was" "born") ...`
-- misparsing an unrelated clause as part of a proper-noun chain) that still
happened to surface the correct answer in its fiber, purely because the
target word remained a lexical anchor regardless of the surrounding
nonsense. That is a coincidence, not evidence of correct reasoning, and it
conflates two genuinely separate questions: can the frontend turn a real
sentence into a well-typed representation at all (a large, separately
documented, still-open problem), versus given a *trusted* representation,
does the formal machinery correctly resolve the metonymy.

`pilot-scenarios.tsv` isolates the second question only. It is a hand-built
scenario file in the exact low-level TSV format `Metonymy.ContextSpec` reads
directly (the same format the checked-in `evaluation/contextual-multidomain/`
silver/audited fixtures ultimately compile down to) -- one row per example,
with the *real* VerbNet-derived constraint for each (computed locally via
`contextual_rule_compiler.resolve_action`, not invented: `attend`'s object
role is `Prefers HasSort Entity` for 8 of the 9; `study`'s is a **hard**
`Requires HasSort Readable` for Haifa specifically, VerbNet having matched a
different sense of "study" than the institution-attendance one -- left as-is
rather than hand-corrected, since that mismatch is itself a real, honest
finding about selectional-preference granularity for polysemous verbs, not a
bug to paper over). Run directly via `build/metonymy --snapshot
wikidata-snapshot --scenarios pilot-scenarios.tsv contextual-fiber <name>`
(`.github/workflows/pilot-decode-direct-evaluation.yml`) -- no Stanza, no GF
parsing, no dependency-hint frontend at all, so nothing about the frontend's
own reliability can contaminate the result.

**Result from the 9-scenario direct run**: 8/9 had the gold QID in the final
fiber, 0/9 narrowed to a single candidate (fiber sizes 15-289), and Haifa's
empty fiber was explained (the `study` sense mismatch above). Every single
stage on every scenario showed `agda-layer-check=true`. Investigated *why*
none narrowed: `attend`'s own constraint, `Prefers HasSort Entity`, can never
eliminate anything -- `Entity` is this project's universal top sort, so every
candidate already satisfies it, and a `Prefers` constraint only annotates a
`preferred` subset without shrinking `survivors` regardless (confirmed
directly in the stage output: `preferred` was always identical to
`survivors`). Real narrowing needs a **second**, genuinely selective
constraint (a `Requires`, which does remove non-matching candidates from
`survivors` -- this is exactly how the already-checked-in
`evaluation/contextual-multidomain/silver-inputs.jsonl` "commercial agreement"
vs. "political agreement" pair narrows on synthetic data) -- but these nine
sentences are minimal ("He attended Pomona.") and carry no second piece of
information near the target for the compiler to have derived one from.

`amherst-with-degree-context`/`valparaiso-with-degree-context`/
`haifa-with-degree-context` add exactly that, using real text already present
in the corresponding full sentences, not fabricated: Amherst's full sentence
says "graduated from Amherst **with a degree in mechanical engineering**",
Valparaiso's says "received his **bachelor's degree**", Haifa's says
"**obtaining a BA** in Political Science" -- in all three, the subject
explicitly earned an academic degree *there*, which is real evidence the
referent is specifically an institution that grants degrees (Wikidata class
Q3918, "university" -- confirmed present in this snapshot's own `rules.json`
type projections, `subsortRules` chains `University -> Organization ->
Agent`). Each of these three scenarios keeps `attend`'s original weak
constraint as stage 1 and adds a second, **hard** `Requires HasSort
University` constraint as stage 2 (`requires`, not `prefers`, since only
`requires` actually removes candidates) -- a real second layer, derived from
real sentence content, the same "context accumulates as constraints, fiber
narrows" mechanism this whole investigation set out to test. Haifa
specifically uses `attend`'s constraint here instead of `study`'s, to isolate
the effect of adding context from the separate, already-diagnosed
wrong-verb-sense problem.

**First run of the three degree-context scenarios found the constraint
eliminated the correct answer itself, not just the wrong ones** -- a second
genuine finding, diagnosed and fixed rather than papered over. `HasSort
University` is derived by this project's `reachesType` (walking the
snapshot's own `P279`/subclass-of claims from an entity's `P31` target up to
Wikidata's `Q3918`, `engine/src/Metonymy/Snapshot.hs`). Checking each real
institution's actual `P31` value against live Wikidata showed none of the
three had `P31` pointing *directly* at `Q3918` -- Amherst College's is
`Q1377182` ("liberal arts college"), Valparaiso University's is `Q902104`
("private university"), University of Haifa's is `Q62078547` ("public
research university") -- and the snapshot, materialized at depth 1 from only
the 18 seed QIDs (each place + each gold institution), had captured **zero**
`P279` claims anywhere: expanding one hop from a seed captures that seed's
*own* class (`P31` target), but not that class's *own* superclass chain,
since the class QIDs themselves were never separately seeded. Tracing the
real chains directly against live Wikidata found:
- **Valparaiso**: `Q902104` ("private university") --P279--> `Q3918`
  ("university") directly -- a genuine, existing 2-hop chain.
- **Haifa**: `Q62078547` --P279--> `Q875538`/`Q15936437` --P279--> `Q3918`
  -- a genuine, existing 3-hop chain.
- **Amherst**: `Q1377182` ("liberal arts college") --P279--> `Q189004`
  ("college") --P279--> `{Q38723, Q2385804, Q123349660}`, none of which is
  or further chains to `Q3918`. Amherst's *other* `P31` value, `Q23002054`
  ("private not-for-profit educational institution"), also dead-ends without
  reaching `Q3918`. **This is not a snapshot gap -- Wikidata's own class
  graph genuinely does not link "liberal arts college" to "university" as a
  subclass**, reflecting the real English-language distinction between US
  "college" and "university" institution names, even though Amherst College
  grants bona fide bachelor's degrees.

All 20 real `P279` edges found while tracing these three chains (the full
local closure, not just the ones that happen to reach `Q3918` -- adding only
the successful edges would have been cherry-picking) were added to
`wikidata-snapshot/claims.jsonl`, and `manifest.json`'s `graph_sha256`
recomputed over the exact bytes Git will actually store (`core.autocrlf`
normalizes this repository's checkout to CRLF on Windows but commits LF --
recomputed and independently verified against the *staged* blob content, not
the Windows working-tree bytes, to avoid the same class of mismatch this
project's `graph_sha256` procedure is designed to catch). **Confirmed by a real CI run after this fix** (`pilot-decode-direct-evaluation.yml`,
`graph_sha256=adf50ed9...`): exactly as predicted.
- **`valparaiso-with-degree-context`**: stage 2 narrows 58 survivors down to
  `survivors=[Q186047]` -- the single, correct gold QID (Valparaiso
  University), both stages `agda-layer-check=true`.
- **`haifa-with-degree-context`**: stage 2 narrows roughly 400 survivors down
  to `survivors=[Q591115]` -- the single, correct gold QID (University of
  Haifa), both stages `agda-layer-check=true`.
- **`amherst-with-degree-context`**: stage 2 still gives `survivors=[]`, with
  `Q49165` (Amherst College) still listed under `obstruction=MissingRequirement`
  -- confirmed, not a bug: a genuine Wikidata-ontology limit (see above), left
  as an honest negative result rather than patched with a fabricated `P279`
  edge.

This is the first case in this whole investigation where two genuine
constraints, both derived from real sentence content (the verb "attend" and
a real "degree" mention), narrow the graph search on real Wikidata data down
to a single, correct candidate -- fully Agda-verified at every step. Earlier
attempts either failed to narrow at all (`Prefers HasSort Entity` alone) or
narrowed incorrectly (the pre-fix snapshot gap above); this is the first
clean demonstration of the "context accumulates as constraints, fiber
narrows to the truth" mechanism this fixture was built to test.
