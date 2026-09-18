# Hand-curated WiMCor pilot (4 examples)

Four real sentences drawn from WiMCor v1.1 (Mathews et al., CC BY-SA 3.0),
reproduced here under that license's quotation/attribution terms for formal
verification purposes -- not the full corpus, not redistributed in bulk.

Selected specifically because their metonymy target is a proper noun that
resolves cleanly to one real Wikidata entity (a named institution/place),
unlike most WiMCor/ConMeC targets, which are common nouns with no single
canonical Wikidata referent (see `docs/contextual-tower.md`'s "hand-curated
real-sentence pilot" section for why that distinction matters and why this
fixture is scoped to only these four).

| id | source mention | resolves to | gold |
|---|---|---|---|
| wimcor:test:36249 | Houghton | Q4500472 (Houghton University) | metonymic |
| wimcor:test:22279 | Santiago | Q117040 (Santiago de Cuba) | literal |
| wimcor:test:12905 | Pomona | Q7227384 (Pomona College) | metonymic |
| wimcor:test:5595 | Leicester | Q1333399 (University of Leicester) | metonymic |

`wikidata-snapshot/` is a small (~60KB), purpose-built graph snapshot
(`scripts/build_wikidata_api_index.py` + `scripts/build_wikidata_runtime_index.py
materialize`, depth 1, seeded directly with the four QIDs above -- resolved by
hand via a direct Wikidata search, not the bare-word `wbsearchentities` lookup
that misfires on common-noun targets) -- enough graph context to test whether
the contextual tower's real formal machinery (constraint derivation, layered
`ContextConstraint` filtering, Agda-checked `runtimeCheck`) accepts or rejects
each of these four sentences, without needing the full live-API scan or the
1.5-2 hour `contextual-tower-evaluation.yml` run.

Run via `.github/workflows/pilot-curated-evaluation.yml` (workflow_dispatch).
