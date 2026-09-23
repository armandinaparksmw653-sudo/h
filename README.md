# Cubical type theory for proof-carrying metonymy

Research prototype positioning metonymy (predicate transfer) as an
application of **Cubical Agda**: a metonymic reading is a *quotient* of a
context-indexed fiber of candidate referents by a contextual compatibility
relation, and the transfer itself is a proof-carrying path/equivalence,
not a heuristic rewrite. The system combines:

- Grammatical Framework (GF), used narrowly as a hand-curated, type-checked
  front end for a bounded set of English constructions — not a broad-coverage
  parser;
- a Haskell engine (the **contextual tower**: `Metonymy.Contextual`/
  `ContextualChecked`/`ContextSpec`) that stacks context-derived constraints
  as successive layers, each independently re-verified;
- Cubical Agda for the higher-inductive quotient (`formal/Metonymy/
  FilteredContext.agda`'s `CoarseFiber`), the metonymic path constructor,
  and the compiled `contextLayerCheck` that is the sole authorization
  boundary — nothing Haskell proposes is trusted until Agda accepts it.

**Scope, stated plainly**: this project does not claim state-of-the-art
metonymy detection (for that, use an LLM). It demonstrates that predicate
transfer for *referential/encyclopedic* metonymy (a place standing for an
institution located there, a company for its headquarters, etc.) can be
given a computable, machine-checked semantics, on a small number of
deeply-verified real examples plus the formal apparatus to combine several
independent contextual signals — not on large-corpus recall.

```text
He attended Valparaiso and received a degree.
  → He attended Valparaiso University.
  (two stacked constraints — "attended" and "degree" — narrow the fiber
   over the place "Valparaiso" to the one candidate that is both an
   Organization and a University)

Cupertino signed the commercial agreement.
  → Apple Inc. signed the commercial agreement.
  (a real, live-Wikidata-verified example: Cupertino → Apple, Inc.,
   BusinessOrganization)
```

See [docs/contextual-tower.md](docs/contextual-tower.md) for the full
worked history of these and the other curated examples (Haifa, Pisa, UCLA,
Berklee, Padgate, Winchester, Phoenix, Loughborough, and the synthetic
multi-domain tower fixtures), including the ones that were searched for and
honestly rejected (a competing institution named in the same sentence, a
Wikidata data gap, etc.).

## Architecture

```text
English text
  → GF abstract syntax
  → typed predicate requirement
  → proof-producing ontology query
  → admissible semantic fiber
  → expansion or safe contraction
  → checked certificate
  → GF linearization
  → English text
```

The runtime distinguishes two notions:

- `BridgePath x y` is a directed ontological relation such as
  `Authored`, `Contains`, or `GovernedBy`;
- a cubical path connects the implicit and explicit grammatical
  derivations after an admissibility certificate has been constructed.

The Haskell `Certificate` mirrors the Agda `Admissible` type. Search and
ranking may be heuristic, while certificate verification rechecks every
relation and selectional requirement.

See [docs/architecture.md](docs/architecture.md) for module boundaries and
the trust model.

## Prerequisites

- GHC 9.4 or newer;
- GF 3.12;
- GF Resource Grammar Library tag `20260403`;
- Agda 2.6.3;
- `agda/cubical` v0.5.

The checked-in Cursor environment installs compatible versions. On Ubuntu
24.04, `./scripts/bootstrap.sh` clones the pinned Cubical and GF Resource
Grammar libraries, compiles the English GF grammar, checks the Agda
development, builds the Haskell executables, and runs all tests.

```bash
./scripts/bootstrap.sh
```

After bootstrapping:

```bash
./scripts/check.sh
```

If Cubical is installed in a custom location:

```bash
CUBICAL_LIB=/path/to/cubical ./scripts/check.sh
```

The English RGL location can likewise be overridden:

```bash
RGL_LIB=/path/to/compiled-rgl ./scripts/check.sh
```

## Running the tower

Run a hand-built scenario (the Waterloo fixture, `data/contextual-scenarios.tsv`)
directly through the compiled Agda checker:

```bash
./build/metonymy contextual-fiber waterloo
./build/metonymy contextual-contract waterloo Q1049470
```

Run a real sentence end to end (GF tree → constraints → tower → Agda), the
same pipeline the curated examples in `evaluation/pilot-decode-wimcor/` and
`evaluation/contextual-multidomain/` are verified with:

```bash
python3 scripts/run_automatic_contextual_pipeline.py \
  --engine build/metonymy \
  --snapshot data/wikidata-openalex-snapshot \
  --sentence "Cupertino signed the commercial agreement" \
  --source Cupertino
```

`./build/metonymy parse`/`linearize` remain available as GF-only diagnostic
commands (no engine/Agda involvement) — see `docs/contextual-tower.md`.

**Legacy pipelines**: two earlier, independent engines (a flat
`open-evaluate`/`open-batch` positional-heuristic frontend, and a separate
"Automatic" `expand`/`contract`/`list` demo engine with its own hand-written
knowledge base) have been moved to [`trash/`](trash/) — not deleted, kept
for reference, but no longer built, tested, or run in CI. See
`docs/contextual-tower.md`'s cleanup section for exactly what moved and why.

## Knowledge data

The tower resolves entities against a small, hash-verified Wikidata-style
snapshot (`data/wikidata-qid-snapshot/`, `data/wikidata-openalex-snapshot/`,
or the fully fictional `data/synthetic-towers-snapshot/` used only for
engine-level mechanism tests) — 5 files each (`entities.jsonl`,
`aliases.jsonl`, `claims.jsonl`, `rules.json`, `manifest.json`), verified by
`extract_wikidata_snapshot.py verify` before every use. It also loads:

```text
data/predicates.tsv            hand-audited argument types for a small verb set
data/verbnet-predicates.tsv    imported VerbNet selectional preferences
data/verbnet-actions.tsv       sense-preserving VerbNet action identities
data/verbnet-action-roles.tsv  structured Action×Role requirements
data/contextual-context-triggers.json  (lemma, tree-relation) → constraint
data/contextual-language-rules.json    morphology, composition, frame rules
data/wordnet-context-rules.json        lexical/adjective sort mappings
```

Adding a manually audited verb is a data operation: add its GF expression
and argument types to `data/predicates.tsv`, then run `make grammar`. The
open frontend also indexes every executable subject/object realization in
the pinned VerbNet Action×Role snapshot. Multiple senses are preserved and
searched rather than collapsed to one lemma-level row.

Refresh the pinned VerbNet snapshot:

```bash
./scripts/import_verbnet.py
make grammar
```

VerbNet restrictions are tendencies rather than logical impossibility
claims. Imported rows are therefore explicitly marked
`SelectionalPreference`, while manually audited entries may use
`HardRequirement`. Nested AND/OR and negative restrictions are preserved;
negative requirements use closed-world checking against the frozen local
ontology. See [data/SOURCES.md](data/SOURCES.md) for provenance,
licensing, and extraction policy.

## Formal model

`formal/Metonymy/Core.agda` defines:

```text
BridgePath     directed semantic transitions
Admissible     bridge evidence × contextual requirement
Fine           explicit meanings in one admissible fiber
Coarse         a higher-inductive quotient of that fiber
contract       Fine → Coarse
Expansion      the homotopy fiber of contract
Derivation     implicit and explicit grammatical derivations
metonymy       a path from the implicit to an explicit derivation
```

`formal/Metonymy/Soundness.agda` checks:

- admissible fine meanings have the same compressed image;
- the original fine meaning remains an expansion after contraction;
- metonymic paths are preserved by grammatical contexts.

`formal/Metonymy/Checker.agda` is the executable trusted kernel. It
independently checks:

```text
non-empty and connected bridge paths
existence of every ontology edge
predicate identity, argument sort, strength, and provenance
target typing through the imported subsort tree
```

The checker is compiled through MAlonzo and called through a generated,
stable project facade; numbered MAlonzo identifiers do not escape that
adapter. Candidates rejected by Agda are never emitted.
`RuntimeBridge.agda` proves:

```text
runtimeCheck KB beforeGF afterGF certificate = true
  → RuntimeAdmissible
  → HardCell
  → Path in Completion
  → equality in independent quotient semantics
```

Haskell search is therefore outside the trusted computing base: it proposes
certificates but cannot authorize one.

The strengthened publication-oriented development—raw grammar, directed
bridges, coherent 2-cells, witnessed compression, semantic factorization,
checker reflection, preference promotion, conservativity, and
non-collapse—is indexed in `formal/Metonymy/PublicationTheorems.agda`.
See [docs/mathematics.md](docs/mathematics.md) for the exact theorem-to-file
map and assumptions, and [docs/main-theorem.md](docs/main-theorem.md) for a
concise statement of the main theorem (contextual homotopy fiber, filtered
family, proof-carrying paths, decidable lifting, safe contraction) with its
scope explicitly bounded.

The self-contained formal source directory is
[`formal/Metonymy`](formal/Metonymy). Its publication-facing theorem index is
[`formal/Metonymy/THEOREMS.md`](formal/Metonymy/THEOREMS.md); verify all source
hashes and safe Agda checks with:

```bash
make formal-artifact
```

## Publication artifact

On the pinned Ubuntu 24.04 toolchain, reproduce theorem checking, GF
generation, the stable MAlonzo adapter, Haskell integration tests, and the
independent evaluation tests with:

```bash
make reproduce
```

CI runs the same command. Exact commits and artifact hashes are recorded in
[`toolchain.lock.json`](toolchain.lock.json); third-party terms are listed
in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The paper-facing
claim map is [`docs/claims.md`](docs/claims.md).

## Current scope

This is a formally checked, narrow-coverage semantics for referential
metonymy, not a general semantic parser and not a metonymy detector. The
GF grammar covers a bounded set of English constructions (SVO, adjective+
noun composition, a closed set of prepositions, relative clauses); a
sentence outside that coverage is declined, not guessed at. Every
constraint that reaches the tower — whether from `data/predicates.tsv`,
imported VerbNet preferences, or `data/contextual-context-triggers.json`'s
(lemma, construction) dictionary — is `Requires` or `Prefers` labeled with
honest, per-entry provenance (real corpus + live Wikidata verification
where done, explicitly marked synthetic where not); only `Requires`
constraints ever eliminate fiber candidates. No external source bypasses
the compiled Agda `contextLayerCheck`.

Candidate ranking is deterministic; there is no statistical or LLM scorer
establishing formal admissibility anywhere in the trusted path (an LLM can
propose a *tree structure* as a third, untrusted GF-tree-source tier — see
`scripts/llm_propose_clause_structure.py` — but never a constraint or a
certificate).

## Waterloo fixture walkthrough

`data/contextual-scenarios.tsv`'s one hand-written scenario illustrates the
tower's stage-by-stage narrowing end to end:

```bash
./build/metonymy contextual-fiber waterloo
./build/metonymy contextual-contract waterloo Q1049470
```

The second command is rejected on the Waterloo fixture: the physics layer
contains both `Q1049470` (University of Waterloo) and `Q2004561` (Perimeter
Institute), so unique-fiber contraction is unsafe. Waterloo City Council
receives a `MissingRelation` obstruction and is dropped at the `announce`
layer. A later constraint that leaves a singleton licenses the reverse path
from that unique survivor back to the source QID — exactly what happens for
the curated real examples (Valparaiso, Cupertino, etc.) once a second,
independent constraint is added.

For the independent scorer, five ablations, and dataset licensing policy
for the curated example sets, see [evaluation/README.md](evaluation/README.md)
and [docs/evaluation.md](docs/evaluation.md).
