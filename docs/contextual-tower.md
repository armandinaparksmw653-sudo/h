# Lexicalized contextual fiber tower

The contextual pipeline computes every snapshot-witnessed interpretation rather
than selecting a top-1 endpoint:

```text
local Wikidata dump
  → deterministic QID snapshot + graph_sha256
  → lexicalized GF application tree
  → ordered ContextConstraint tower
  → survivors and structured obstructions at every stage
  → compiled Agda contextualRuntimeCheck
  → cubical path for every accepted stage certificate
```

Concrete entities are QIDs loaded from `data/wikidata-qid-snapshot`. The
fixed code contains only the ontology vocabulary and the generic algorithms.
Property projections, type mappings, queries, and lexical constraints are
versioned data in `rules.json` and `data/contextual-scenarios.tsv`.

## Reproduce the Waterloo slice

```bash
./build/metonymy contextual-fiber waterloo

python3 scripts/evaluation/extract_qid_fibers.py \
  --dataset evaluation/qid-fiber/waterloo-dataset.jsonl \
  --engine build/metonymy \
  --output build/evaluation/waterloo-contextual-inference.jsonl

python3 scripts/evaluation/score_qid_fibers.py \
  --inference build/evaluation/waterloo-contextual-inference.jsonl \
  --gold evaluation/qid-fiber/waterloo-gold.jsonl \
  --output build/evaluation/waterloo-contextual-report.json
```

The final Waterloo layer contains `Q1049470` and `Q2004561`. `Q7974219`
is removed by a `MissingRelation Conducts Q413` obstruction. The two survivors
remain distinct unless an explicit compatibility witness is supplied.

Unique-fiber contraction of `Q1049470` is therefore rejected: the reverse
path exists for each survivor, but `UniqueEntity` fails. The CLI
`contextual-contract` authorizes contraction only when the explicit target is
the unique final survivor or a `GenericReading`.

## Formal witnesses

`Metonymy.ContextualTower` provides:

- `elaborationBindsLexemes`;
- `fiberRestriction`;
- `extensionSound` and `extensionComplete`;
- `obstructionSound`, `extensionOrObstruction`, and
  `obstructionTerminatesPath`;
- `stagePath`;
- `towerPathStability`;
- `compatibleCandidatesGlue`;
- `emptyFiberNoRewrite`.
- `FilteredContext.UniqueEntity`, `safeContraction`, and
  `uniqueEntityStrengthens`.

Path stability requires explicit equality of the underlying checked runtime
cell. It does not claim that arbitrary discourse extension preserves a
metonymic license.

## Scope

All results are relative to the finite snapshot hash and supplied lexicalized
GF tree. Parsing coverage, Wikidata completeness, intended-reference
uniqueness, and factual correctness of external data are not proved. A missing
snapshot witness is an obstruction for that run, not impossibility in natural
language.

## Full dump runtime index

For a full local Wikidata dump, build the offline SQLite index once. The
current entity dump is over 100 GB compressed, so it is deliberately an
explicit operation, outside CI and the Cloud Agent install:

```bash
./scripts/download_wikidata_dump.sh \
  https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2 \
  ~/.cache/metonymy/wikidata/latest-all.json.bz2

python3 scripts/build_wikidata_runtime_index.py build \
  --dump ~/.cache/metonymy/wikidata/latest-all.json.bz2 \
  --database ~/.cache/metonymy/wikidata/runtime.sqlite
```

The index retains English labels/aliases and the projected relation/type
properties, along with the exact dump SHA-256. Resolve a textual mention using
only the frozen index:

```bash
python3 scripts/build_wikidata_runtime_index.py lookup \
  --database ~/.cache/metonymy/wikidata/runtime.sqlite \
  --alias "Waterloo"
```

### Live-API runtime index (no dump download)

For entity linking at the scale of one corpus's distinct mention surfaces
(not the whole graph), `scripts/build_wikidata_api_index.py` populates the
same SQLite schema directly from Wikidata's live API, so the dump download
above can be skipped entirely:

```bash
python3 scripts/build_wikidata_api_index.py \
  --database build/wikidata-api-runtime.sqlite \
  --dataset evaluation/contextual-multidomain/audited-inputs.jsonl \
  --dataset-field source \
  --depth 1 --max-entities 5000
```

The resulting `.sqlite` file is a drop-in replacement for the dump-built
index above: `lookup`, `build_wikidata_linker_cache.py`, and `materialize`
(both shown next) all work against it unchanged. It only ever knows about
entities reachable within `--depth` hops of the corpus's own mention
surfaces, so it is deliberately narrower than a full-dump index; see
data/SOURCES.md for the reproducibility caveat that comes with sourcing it
live instead of from a pinned dump file.

Build a batch linker cache from unlabelled inference inputs; ambiguous aliases
are recorded as ambiguity rather than guessed:

```bash
python3 scripts/build_wikidata_linker_cache.py \
  --database ~/.cache/metonymy/wikidata/runtime.sqlite \
  --inputs evaluation/contextual-multidomain/audited-inputs.jsonl \
  --output build/evaluation/wikidata-linker-cache.json
```

Then materialize a bounded, hash-bound snapshot for one or more resolved QIDs:

```bash
python3 scripts/build_wikidata_runtime_index.py materialize \
  --database ~/.cache/metonymy/wikidata/runtime.sqlite \
  --source-qid Q639408 --source-qid Q649 --depth 2 \
  --rules data/wikidata-runtime-rules.json \
  --output build/wikidata-qid-snapshot
```

The SQLite index is an untrusted offline retrieval structure. The materialized
finite snapshot—not the mutable index—is the runtime KB passed to the checker
and bound into certificates through `graph_sha256`. Its manifest records both
the bounded materialization parameters and the immutable source-index hash.

## Automatic language-database pipeline

The automatic proposer combines:

- GF-compatible lexical anchors and spans;
- hard action roles from `data/predicates.tsv` and all compiled Action×Role
  projections from `data/verbnet-action-roles.tsv`;
- 5,001 lexical projections generated from Princeton WordNet;
- QID aliases and graph claims from the frozen Wikidata snapshot;
- optional OpenAlex institution-topic evidence in
  `data/wikidata-openalex-snapshot/evidence.jsonl`.

Action senses that share a lemma and hole are alternatives, so their distinct
requirements are compiled into one disjunction rather than intersected as
separate layers. Audited hard requirements take precedence; otherwise the
layer is represented by `Prefers`/`PrefersSome`/`PrefersRelation`. A
preference records its matching subset and misses but does not remove
candidates from the hard fiber. Agda independently verifies both partitions.
Bridge relations are selected by a global requirement-sort schema and then
intersected with the active snapshot's `rules.json`, rather than being listed
per action or scenario. `data/contextual-language-rules.json` now retains only
irregular morphology overrides and sort-level bridge, composition, and
construction schemas.

### Passive voice

`Metonymy.gf`/`MetonymyEng.gf` add `PassCompl : V2 -> NP -> VP`, linearized
via the RGL's `PassAgentVPSlash (SlashV2a verb) agent` -- `PassAgentVPSlash`
from `Extend`/`ExtendEng`, `SlashV2a` from `Verb`/`VerbEng` (a genuinely
separate module: `Extend`'s own abstract definition only extends `Cat`,
not `Verb`, so it does not re-export `Verb`'s functions; the first CI run
of this change confirmed `SlashV2a` was unreachable with only `SyntaxEng`/
`ExtendEng` opened, and `VerbEng` had to be added explicitly) -- and
predicated with the existing `Pred : NP -> VP -> S` -- the passive
clause's grammatical subject (semantically the patient) fills the same
slot an active subject does; no new `S`-level rule was needed.
`scripts/annotate_dependency_hints.py` reports a passive subject
(`nsubj:pass`) as `hole_role="Object"` (it is the patient, not the agent)
and the "by"-agent phrase (`obl` + `case="by"` on a verb with an
`aux:pass` child) as `hole_role="Subject"`, both with a `voice="passive"`
field and a governing span covering the auxiliary too ("was captured",
not just "captured"). `resolve_action` uses that to substitute a full
present-passive form ("is captured") rather than the active third-person
form, always assuming a singular subject -- the same implicit convention
the existing active-voice substitution already relies on (a genuine
plural/collective subject is out of scope here; see below).

This is the one part of this session's changes that cannot be verified
locally: there is no GF toolchain on this development machine, so the
grammar edit and the RGL function names (confirmed against the pinned
`gf-rgl` commit's actual source, not guessed) are unverified until
`make test`/`make formal-artifact` run in CI or the `.cursor` container.
The Python-side dependency-hint classification, `resolve_action`'s
`gf_form` selection, and `compile_gf_constraints`' handling of a
`PassCompl` tree node are all covered by local unit tests against
hand-built inputs (`tests/evaluation/test_compile_gf_constraints_passive.py`
and the passive cases in `test_annotate_dependency_hints.py`/
`test_resolve_action_dependency_hint.py`), independent of whether the
grammar itself compiles.

Deliberately out of scope for this pass: plural/collective subjects
(a "the players" bridge onto one collective entity, staying inside the
accepted one-entity-per-hole boundary), tense/aspect beyond present, and
further PP/modifier stacking beyond what the existing recursive
`ModifyNP` walker already handles structurally.

### Coordination and arbitrary prepositions

`Metonymy.gf`'s abstract syntax previously had exactly one clause-level
category and no cross-sentence or coordination structure at all -- a
handful of `Pred`/`Compl`/`PassCompl`-style constructions and four
hardcoded prepositions (`InPP`/`AboutPP`/`WithPP`/`ForPP`). Locally
reproducing the real contextual-tower-evaluation.yml sample (see the
"Source-mention disambiguation" section above) confirmed this was the
dominant remaining bottleneck once the source-disambiguation and
gf_sentence-scoping fixes landed: `gf-parse-empty` accounted for the
large majority of both corpora's failures once other, earlier stages
stopped masking it, and it kept the pool constant even after scoping
gf_sentence down to a single sentence -- i.e. the failures were real
single-sentence construction/vocabulary gaps, not a paragraph-scoping
artifact.

Added `AndS`/`OrS : S -> S -> S`, `AndNP`/`OrNP : NP -> NP -> NP`, and
eight new fixed prepositions -- `OnPP`/`AtPP`/`FromPP`/`ByPP`/`OverPP`/
`UnderPP`/`DuringPP`/`NearPP : NP -> PP`, alongside the original
`InPP`/`AboutPP`/`WithPP`/`ForPP`. All linearize through RGL functions
already reachable via the existing `open SyntaxEng` (no new `open`
needed -- confirmed against the pinned gf-rgl commit's actual source:
`Syntax`'s own interface is `Constructors, Cat, Structural, Combinators`,
and `Constructors.gf` already carries the binary-coordination overloads
`mkS : Conj -> S -> S -> S` and `mkNP : Conj -> NP -> NP -> NP`, while
`and_Conj`/`or_Conj` live in `Structural.gf`): `AndS s1 s2 = mkS and_Conj
s1 s2`, `AndNP np1 np2 = mkNP and_Conj np1 np2`, `NearPP np = SyntaxEng.mkAdv
(mkPrep "near") np` (and so on for the other seven, exactly like the
original four already did). Because `lincat NP = NP`/`S = S` throughout,
an `AndNP`/`OrNP` result composes everywhere a plain `NP` already could
(as a `Compl` object, a `Pred` subject, ...) with no special-casing
elsewhere, and gets RGL's own plural-agreement handling for free --
unlike the hand-rolled `Open*` family, which fakes agreement via manual
string concatenation.

**A first attempt used one open-ended `PrepPP : String -> NP -> PP`**
instead of eight fixed ones, parsed the same open-vocabulary way
`OpenPN`/`EveryCN` already are -- reverted after the first real CI run
against it. GF's `String` category parses as "match any single token",
and combined with the grammar's own already-open `OpenPN`/`Open*`
family, this created a genuine new parse ambiguity: "the political
agreement" gained a spurious *second* reading as `OpenPN "the"` modified
by `PrepPP "political" (OpenPN "agreement")` (i.e. "the", reinterpreted
as an open proper noun, followed by "political" reinterpreted as an
open preposition governing "agreement") alongside its intended reading
as an adjective-modified definite NP -- and since `engine parse` returns
every alternative tree GF finds, `trees[0]` was no longer reliably the
intended one, breaking three existing tests
(`test_qid_fiber.py`'s `test_automatic_multi_source_pipelines`,
`test_unique_and_ambiguous_contextual_contraction`,
`test_unknown_gf_semantic_composition_fails_closed`) whose fixtures
depended on that specific sentence parsing unambiguously. A closed,
named preposition per function has no such ambiguity -- each only ever
matches its own fixed word, exactly like the original four already did;
this is why the list above is eight separate functions rather than one
parameterized one.

`scripts/contextual_rule_compiler.py`'s `compile_gf_constraints` tree
walker required no structural changes for coordination: `first_node`'s
recursion already walks into any constructor's arguments generically, so
it finds a `Compl` node nested inside an `AndS` exactly as it would
anywhere else, and `_noun_lemma`/`_proper_lemma` already degrade to a
safe no-op (no constraint, no crash) for a constructor shape they do not
recognize -- the same protection a bare-proper-noun object already
relied on -- which is what an `AndNP`/`OrNP` object gets today. The
eight new prepositions slot directly into the existing
`ModifyNP`+fixed-preposition composition-matrix table
(`InPP`/`AboutPP`/`WithPP`/`ForPP`'s hardcoded lookup) the same way the
original four already do; no `context_templates` data has entries keyed
by any of the eight yet, so none of them contribute an extra
`FrameModifier` constraint today, but the wiring is in place for when
such data is authored.

As with the passive-voice addition, the grammar edit and RGL function
names are verified against the pinned `gf-rgl` commit's actual source
but not locally compilable (no GF toolchain on this machine) --
`tests/evaluation/test_compile_gf_constraints_coordination.py` covers
the Python-side tree-walker contract against hand-built tree strings,
independent of whether the grammar itself compiles; that only happens
in CI/`.cursor`.

**Measured effect: zero.** A real `contextual-tower-evaluation.yml` run
against this exact commit produced byte-identical `literal_prediction_reasons`
counts before and after -- `AndS`/`OrS`/`AndNP`/`OrNP` plus the eight new
prepositions changed nothing on the real 150+150 sample. Locally
reproducing that sample (pure Python, `propose_contextual_scenario.py`
needs no GF toolchain) explained why: `AndS`/`OrS` only join two *full*
clauses, each with its own subject *repeated* in the surface text ("X did
A and X did B") -- but real "and" in corpus text is overwhelmingly VP
coordination with a *shared* subject ("X did A and did B", subject not
repeated), a different RGL construction entirely (see "VP coordination"
below). And 199/281 (70%) of that sample's sentences contain a comma
somewhere -- not for listing, but for appositives ("his sister, Katherine,
and father..."), fronted adverbials ("Compared to other English cities,
Sheffield has..."), and, most commonly, a participial phrase *before* the
subject ("Born in Eisenach, the daughter of a Saxe-Weimar official, Luise
von G. was...") -- something the grammar has no rule for at all, which
breaks the parse regardless of whether "and" or these eight prepositions
appear anywhere in the same sentence. See the plan file's "Расширение
GF-грамматики: закрытие оставшихся пробелов парсинга" section for the
full phased plan this finding produced.

### VP coordination with a shared subject

Added `PredConjVP`/`PredOrConjVP : NP -> VP -> VP -> S` -- "NP did VP1 and
VP2" with one subject, the shape real "and"/"or" coordination
overwhelmingly takes (unlike `AndS`/`OrS`, see above). Verified against
the pinned gf-rgl commit's actual source: `Extra.gf` declares
`cat VPS ; [VPS]{2}` and `fun MkVPS : Temp -> Pol -> VP -> VPS`,
`ConjVPS : Conj -> [VPS] -> VPS`, `PredVPS : NP -> VPS -> S` -- a separate
category specifically for VP-level coordination, distinct from `S`-level
`ConjS`. `Temp`/`Pol` values come from `Constructors.gf` convenience
constants already reachable via the existing `open SyntaxEng`
(`presentTense : Tense`, `simultaneousAnt : Ant`, `positivePol : Pol`,
`mkTemp : Tense -> Ant -> Temp = TTAnt`) -- only `MkVPS`/`ConjVPS`/
`PredVPS`/`BaseVPS` themselves needed a new `open ExtraEng`.

**Opening `ExtraEng` took two real CI rounds to get right, because it
silently made two pre-existing unqualified calls ambiguous rather than
raising a hard error.** `Extra.gf` independently redeclares its own
`PassAgentVPSlash : VPSlash -> NP -> VP` (identical signature to the one
`PassCompl` already used from `Extend`/`ExtendEng` for the passive-voice
work) and its own `which_RP` local oper in `ExtraEng.gf` (colliding with
`ConstructorsEng.which_RP`, already used unqualified by `ModifyRel`/
`ModifyRelCN`). The first CI round qualified only the first collision
(`ExtendEng.PassAgentVPSlash`) and still failed -- the grammar compiled
without a hard error either way, but a real existing test broke
(`test_qid_fiber.py`'s `test_wordnet_cn_relative_clause_parses_in_gf`,
"Anna examines an institution that conducts physics" stopped parsing
entirely, "The parser failed at token 5: \"that\""), even though that
sentence never touches `PassCompl`. The actual second collision was
sitting in the *same* failing run's own compiler output the whole time
(`grammar/MetonymyEng.gf:59-60: ... conflict ExtraEng.which_RP,
ConstructorsEng.which_RP`) -- found by reading the full warning text
instead of only the file:line references, not by a third guess. Both
calls are now qualified (`ExtendEng.PassAgentVPSlash`,
`SyntaxEng.which_RP`), and `PredConjVP`/`PredOrConjVP`'s own
`MkVPS`/`ConjVPS`/`PredVPS`/`BaseVPS` calls are qualified as `ExtraEng.X`
too, matching this file's own existing idiom (`SyntaxEng.mkAdv` was
already used qualified elsewhere here) -- **any further RGL module this
grammar opens should be checked against its own compiler warnings for
"conflict" lines the same way, not assumed clean just because
compilation succeeds without a hard error.**

`compile_gf_constraints` needed no changes: `first_node`'s generic
recursion already reaches into `PredConjVP`'s VP arguments the same way
it reaches into any other constructor's arguments -- it stops at the
*first* `Compl`/`PassCompl` node found by depth-first order (subject,
then VP1, then VP2), so a `PredConjVP` with a recognizable object in VP1
resolves from VP1, exactly as a plain `Compl` would.
`tests/evaluation/test_compile_gf_constraints_vp_coordination.py` covers
the arity and this tree-walker contract; as with every other grammar
change here, the RGL wiring itself is unverified until CI compiles it.

**Measured effect: zero, again.** A real `contextual-tower-evaluation.yml`
run against this exact commit produced byte-identical
`literal_prediction_reasons` counts to the run before VP coordination
landed. Local diagnosis of the same reproduced sample explained why: of
157 sentences containing "and"/"or", 124 (79%) *also* contain a comma
marking some other, still-unaddressed construction -- grammar gaps
overlap heavily within the same sentences, so a single-construction fix
essentially never flips a sentence from unparseable to parseable on its
own. This motivated batching several more verified, low-risk
constructions together instead of measuring after each one individually
-- see the plan file's "Пакетное расширение грамматики" section.

### Copula, generalized relative clauses, and the genitive

Three more constructors, added together after the VP-coordination
finding above, all verified against the pinned gf-rgl commit's actual
source and all reachable via modules already open (no new collision
surface -- `ExtraEng`'s only two collisions, found the hard way above,
are the complete list from its own compiler warnings):

- **`PredCopNP : NP -> NP -> S`** -- copula predication ("Henry County is
  a county in Alabama"). `Compl`/`PassCompl` were the *only* VP-building
  rules before this, both requiring a `V2`, so a bare "NP is NP2"
  sentence -- extremely common in the biographical/geographic register
  WiMCor and ConMeC draw from -- had no derivation at all. Via
  `Constructors.gf`'s `mkCl : NP -> NP -> Cl`.
- **`ModifyRelVP`/`ModifyRelCNVP : NP/CN -> VP -> NP/CN`** -- generalizes
  `ModifyRel`/`ModifyRelCN` (hardcoded to a `V2`+object pair) to an
  arbitrary `VP`. `mkRCl : RP -> VP -> RCl` is itself the general
  overload `ModifyRel` already routes through internally (via
  `mkRCl SyntaxEng.which_RP (mkVP verb object)`) -- only our own
  abstract signature was artificially narrower than what RGL already
  supports. Lets a relative clause use `Compl`, `PassCompl`, or any
  future VP-building rule uniformly ("which signed X", "which was
  signed by X", ...), instead of only active-transitive ones.
  `scripts/contextual_rule_compiler.py`'s `lexical_head` -- which already
  transparently unwraps `ModifyRel`/`ModifyRelCN` while searching for a
  modified NP's head noun -- now unwraps `ModifyRelVP`/`ModifyRelCNVP`
  the same way, so "the general who signed the treaty" still resolves
  its head noun ("general") through the wrapper exactly as the original,
  narrower constructors already did.
- **`PossNP : NP -> CN -> NP`** -- possessive/genitive ("Tolstoy's
  works" as a live construction, not only the one hand-written example
  NP already in this grammar). Via `Extra.gf`'s `GenNP : NP -> Quant`
  combined with the already-confirmed `mkNP : Quant -> CN -> NP`.

`tests/evaluation/test_compile_gf_constraints_copula_relative_genitive.py`
covers all three: a pure-copula tree (no `Compl`/`PassCompl` at all) is a
safe no-op rather than a crash, `ModifyRelVP`/`ModifyRelCNVP` correctly
resolve their head noun through the new `lexical_head` unwrapping, and a
`PossNP` object degrades safely (not yet a recognized shape for
`_noun_lemma`, the same class of safe degradation `AndNP` already gets).

Adjective–noun semantics are compiled bottom-up from the actual GF subtree.
WordNet now projects `political`, `commercial`, `educational`, and
`scientific` as modifier sorts. The composition matrix covers agreement,
programme, organization, and institution heads; unknown pairs still fail
closed. The same tree walker recognizes `in/about/with/for` PP modifiers and
WordNet-generated common nouns inside relative clauses. Programme heads still
derive hard `Conducts(_, topic-QID)`; institution/organization locatives and
partner PPs are preferences.

### The real root cause of three zero-effect grammar rounds: `OpenPN` only matches one token

Three consecutive rounds of grammar expansion above (S-level coordination
plus 8 prepositions, then VP coordination, then the copula/relative-clause/
genitive batch) each compiled cleanly in CI and each measured *exactly zero
effect* on `literal_prediction_reasons` for the real `contextual-tower-evaluation.yml`
corpus sample -- byte-identical counts before and after, every time. That
workflow deliberately never uploads raw sentence text as a CI artifact (only
the aggregate, text-free score report), so no amount of rewriting it could
narrow this down further; isolating the true cause needed a fundamentally
different diagnostic.

`tests/evaluation/test_gf_parse_diagnostic_matrix.py` is that diagnostic: a
small set of hand-written sentences (never corpus text, so safe to print in
full in a CI log), run through `build/metonymy parse` directly in the fast,
cheap `ci.yml` instead of the slow, opaque `contextual-tower-evaluation.yml`.
Its first real CI run was decisive: the single-word baseline
("Waterloo announces a programme") and the single-word-subject copula test
both passed; all four multi-word tests ("Henry County announces a
programme", "Waterloo announces Henry County", "Shipley School announces a
programme", "Henry County is a programme") failed, each at exactly the
second token (`"The parser failed at token 2: \"County\""`).

The cause: `OpenPN : String -> NP`'s single `String` slot matches exactly
one token when GF parses -- not an arbitrary-length span. A multi-word
proper noun never completes a derivation via `OpenPN` alone: "Henry" parses
as the whole NP, and nothing in the grammar can then account for "County"
immediately following it in subject position. Most real WiMCor/ConMeC
source mentions (place, institution, and person names) are two or three
words, so this was silently blocking GF-parsing for a large fraction of
sentences regardless of what sentence-level construction existed elsewhere
-- explaining why coordination, the copula, relative clauses, and the
genitive each measured zero effect: none of them can matter if the
subject/object NP itself never parses.

**Fix**: `OpenPN2 : String -> String -> NP` and
`OpenPN3 : String -> String -> String -> NP`, added as additional
NP-building alternatives (not replacements -- `OpenPN` is still tried for
the one-token case), linearized by concatenating two or three token strings
respectively. `scripts/contextual_rule_compiler.py`'s `_proper_lemma` --
used by `ModifyNP`'s PP-modifier composition-matrix path to resolve a
target's alias -- recognizes both new constructors and returns their
space-joined lemma, the same multi-word name GF actually saw.
`tests/evaluation/test_open_pn_multi_word.py` covers the arity table and
`_proper_lemma` in pure Python; `test_gf_parse_diagnostic_matrix.py` gained
two more cases (`OpenPN3` at both ends of a sentence) and now serves as the
regression check that this fix actually closes the gap it found.

This is the first grammar addition this session with a plausible mechanism
to produce a genuinely non-zero measured effect on the real corpus sample,
since it removes a structural blocker that sat *underneath* every prior
addition rather than adding another sentence-level construction next to
them. The natural follow-up -- the same one-token-only limitation almost
certainly also affects `OpenIndefCN`/`OpenDefCN` for multi-word common nouns
("census-designated place", "research institute") -- is deliberately out of
scope here, to keep this fix focused on the one root cause that has direct,
decisive evidence.

**Real corpus measurement after the fix**: recall stayed 0.0 on both
corpora, but the effect was not uniformly zero this time -- the first
non-zero shift after four rounds. WiMCor's `literal_prediction_reasons`
came back byte-identical to the pre-fix baseline; ConMeC's `gf-parse-empty`
count dropped from 92 to 86, with those 6 rows moving on to
`semantic-composition-failed` (2), a reached-but-empty fiber (3), and one
row that ran all the way through to a (gold-incorrect) metonymic
prediction. So the fix does something real on ConMeC and nothing
measurable on WiMCor -- and, since the corpus sample's raw sentence text
is never uploaded, there was no way to ask *why* without another guess.

### A structural, text-free diagnostic for the remaining `gf-parse-empty` rows

To answer that without guessing a fifth time, `score_contextual_detection.py`
now derives two content-free structural signals from each surviving
exit-7 row's own already-printed `gf_sentence` field (never uploading the
field itself, the same discipline `exit2_candidate_bucket` already
established for exit 2):

- **`exit7_max_capitalized_run`/`exit7_gf_sentence_bucket`** -- the longest
  run of consecutive capitalized tokens in `gf_sentence`, a proxy for how
  many tokens long the proper-noun span GF was actually asked to parse is.
  `literal_reason` now tags exit-7 rows `failed:exit7:run-1`/`run-2`/
  `run-3`/`run-4-or-more`/`run-0`/`unrecognized` instead of the old flat
  `failed:exit7`. A dominant `run-4-or-more` bucket among the remaining
  failures would directly confirm the same one-token-per-`Open*`-slot gap
  extends past what `OpenPN2`/`OpenPN3` cover (motivating an `OpenPN4`, or
  a proper list-based `String* -> NP` construction instead of hand-rolling
  a fixed arity per length); a dominant `run-1`/`run-2`/`run-3` bucket
  would instead mean the remaining failures are a *different* cause
  entirely, since the grammar already has a matching alternative for
  spans that short.
- **`exit7_gf_sentence_signals`/`exit7_signal_counts`** -- three more
  content-free booleans (`has_comma`, `has_digit`, `has_apostrophe`) from
  the same `gf_sentence`, aggregated as corpus-wide counts (never per-row)
  in `score()`'s new `exit7_signal_counts` output field, alongside
  `exit7_rows_seen` for the denominator. Tests this session's other
  standing hypotheses -- appositives/fronted clauses (comma), numerals,
  possessive `'s` -- against the real corpus, independently of the
  capitalized-run bucket above.

`tests/evaluation/test_score_contextual_detection.py` covers all of the
above in pure Python (bucket boundaries, the four-signal detector, safe
degradation on unparseable input, and that aggregate counts never leak the
underlying `gf_sentence` text). The next `contextual-tower-evaluation.yml`
run's Job Summary will report an exact breakdown of the remaining
`gf-parse-empty` failures by capitalized-run length and by comma/digit/
apostrophe presence -- a direct, decisive answer instead of another guess.

**The real breakdown, from the actual next run**: `run-1`/`run-2`/`run-3`
(already covered by `OpenPN`/`OpenPN2`/`OpenPN3`) made up 76% of WiMCor's
and 97% of ConMeC's remaining `exit7` rows -- `run-4-or-more`, the case
that would justify an `OpenPN4`, was only 24%/3%. `has_comma` dominated
instead: 87% (WiMCor) and 67% (ConMeC). So proper-noun length was never
the bulk of what was left; a comma somewhere in the sentence -- an
appositive, a fronted subordinate clause -- was.

### Fronted/trailing subordinate clauses and short comma appositives

Directly targeting that finding, not another guess. Two additions, both
verified against the pinned gf-rgl commit's actual source before writing
any grammar code, and both deliberately scoped to what GF can do safely:

- **`BecauseS`/`IfS`/`WhenS`/`AlthoughS : S -> S -> S`** (fronted: "Because
  EMBEDDED, main") and **`SBecauseS`/`SIfS`/`SWhenS`/`SAlthoughS`**
  (trailing: "main, because EMBEDDED"). Both `S` arguments are built from
  this grammar's own existing `Pred`/`Compl`/`PredCopNP` -- no open-ended
  `String` parameter anywhere in this construct, so none of the
  `PrepPP`-class ambiguity risk. Final linearizations are the plain,
  literal idiom used everywhere else in this file (`BecauseS embedded
  main = lin S {s = "Because" ++ embedded.s ++ "," ++ main.s}`) -- no
  BIND, no SOFT_BIND, no `open Predef`. See below for why: the real fix
  was never in the grammar.
- **`ApposCommaPN1`/`ApposCommaPN2 : String -> ... -> NP`** -- a short
  (1- or 2-word) comma-delimited appositive ("Waterloo, Ontario,
  announces a programme"), via the exact same hand-rolled
  string-concatenation idiom `OpenPN`/`OpenPN2`/`OpenPN3` already use, a
  literal comma spliced into the NP's own string so it plugs directly
  into the existing `Pred`/`Compl`/`PredCopNP` with no new S-level
  machinery and no RGL `NP`-internals touched. `Noun.gf`'s real
  `ApposCN : CN -> NP -> CN` was checked and rejected for this: its
  English linearization (`NounEng.gf`) does not insert a comma, and it
  takes a `CN`, not the `NP` this grammar's `OpenPN` family already
  produces.

#### Six rounds to the real fix -- and finally getting a local GF to stop guessing

Every round below was confirmed by a real run, not guessed -- first CI,
then (rounds 5-6) a GF toolchain installed directly on the development
machine, which is why the guessing finally stopped:

1. `SentenceEng.ExtAdvS`/`SSubjS` (RGL's own comma-inserting combinators,
   `frontComma = SOFT_BIND ++ ","`) -- compiled cleanly (`SentenceEng`
   was a new `open`, cross-checked against every already-open module's
   exports first; the only name in common, `PredVP`, turned out to be
   `ExtendEng`'s own internal reference via its own `open GrammarEng`,
   not an independent redeclaration) but did not *parse*.
2. Dropped `SentenceEng`, used RGL's closed `Subj` vocabulary through
   `SyntaxEng.mkAdv`'s `Subj -> S -> Adv` overload with a hand-rolled
   comma -- **failed identically to round 1**. Suspected
   `because_Subj = ss "because"` (`StructuralEng.gf`) -- hardcoded
   lowercase, no capitalized variant anywhere in RGL, and every fronted
   test sentence used natural sentence-initial capitalization.
3. Dropped `SyntaxEng.mkAdv`/`Subj` entirely, hand-rolled all eight
   functions with plain literal words, correct capitalization this time
   -- **still failed identically**, a third time, even on a
   freshly-migrated repository (ruling out anything CI-environment-
   specific). Three rounds converging on the exact same failure, despite
   each changing something different, meant the bug was in neither of
   the things any round had actually changed.
4. Added a diagnostic-only `linearize` command to the engine
   (`engine/app/Main.hs`'s `runLinearize`, wired to the already-existing
   `linearize` function in `Metonymy.GF`) and asked it directly what
   `BecauseS`'s own tree produces: `"Because Napoleon announces a
   programme , Waterloo announces a programme"` -- a space before the
   comma. A round-trip test (that exact string fed back into `parse`)
   succeeded, proving the *rule* was sound and only the spacing was
   wrong. Brought back `SOFT_BIND` for the comma, combined with round
   3's capitalization fix.
5. That push hit a genuine *compile* error instead of a parse mismatch:
   `"constant not found: SOFT_BIND"`. `SOFT_BIND` isn't a bare-word GF
   builtin -- it's from GF's own compiler-hardcoded `Predef` resource
   (`gf-rgl`'s `src/prelude/Predef.gf`), which needs its own
   `open Predef`. Added it, cross-checked first as always (`BIND` in
   `ExtendEng`, `nonExist` in `ExtraEng` both confirmed to be only
   internal references, the same false-positive shape `PredVP` was
   earlier) -- **still failed identically to rounds 1-3** once it
   compiled. Six sentences, three grammar rewrites, and now a compile
   error too, all circling the same symptom, was the point CI-round
   guessing stopped being worth it.
6. Installed GF directly on the development machine instead: the
   official Windows release (`gf-3.12-windows.zip`, from the same
   GitHub release `ci.yml` already downloads its Ubuntu `.deb` from) plus
   a plain `git clone` of this project's own pinned `gf-rgl` commit
   (`e825d9223305ad3066e1ac5b276bcdedd2fcd15a`) -- no Cabal/GHC build
   step needed, since `gf -make` compiles `.gf` source directly given a
   `-path` pointing at the RGL source tree's own subdirectories. This
   reproduced the CI failure exactly, then let every hypothesis below be
   tested in seconds instead of a 10+ minute CI round: `l -bind` showed
   `SOFT_BIND` genuinely does not collapse the space in `gf --run`'s
   default renderer (`BIND` shows as a literal `&+` marker instead); `+`
   (GF's morphology-gluing operator, distinct from `++`) can't glue a
   runtime string variable at all (`"one of the arguments... is a bound
   variable... non-exhaustive"` -- it needs compile-time-known cases).
   The real finding: `help p` / `help ps` reveal GF's parser uses a
   **whitespace-only tokenizer by default** (`-words`, "tokens separated
   by spaces") -- "programme," with no preceding space is *one
   indivisible token*, and no grammar-level device, BIND-family included,
   can retroactively split an already-tokenized input string at parse
   time; BIND/SOFT_BIND only ever affected *linearization* display, never
   what the parser's tokenizer does to raw input text. Confirmed the
   fix directly: `ps -lextext "..." | p` (GF's own text-lexer,
   piped into parse) succeeds; feeding the *identical* sentence with a
   manually-inserted space before the comma also succeeds, using a plain
   `","` literal with no BIND anywhere. That also explained why
   `ApposCommaPN1`/`ApposCommaPN2` had appeared to work in every prior CI
   run: they never actually matched at all -- `OpenPN2` (matching *any*
   two whitespace-delimited tokens) was silently absorbing the
   comma-fused tokens themselves (`OpenPN2 "Waterloo," "Ontario,"`,
   comma included in the string) as an accidental two-word proper name,
   producing a real parse tree with the *wrong* semantics that happened
   to satisfy `assert_parses`.

**The actual fix lives in the engine, not the grammar.**
`engine/src/Metonymy/GF.hs`'s `parseEnglish` now runs `spaceBeforeCommas`
on the sentence before handing it to GF: inserts a space before any
comma that doesn't already have one immediately preceding it, a no-op
for every sentence that doesn't reach a comma-using construct (which,
before this session's comma-based grammar additions, was every sentence
this engine had ever parsed). With that in place, `grammar/Metonymy.gf`/
`MetonymyEng.gf` went back to the plain `","` idiom for all ten
comma-using functions (`BecauseS`-family, `SBecauseS`-family,
`ApposCommaPN1`/`ApposCommaPN2`) -- no BIND, no SOFT_BIND, no
`open Predef`. Verified locally against all thirteen relevant sentences
at once (every prior working case plus every comma-using one) both
before and after the engine change: zero regressions, and
`ApposCommaPN1`/`ApposCommaPN2` now genuinely match (confirmed by
inspecting the returned tree, not just that *some* tree came back).

This machine now has a working local GF (`gf.exe` at
`C:\Users\Administrator\gf-local\gf.exe`, RGL source cloned at the pinned
commit under `C:\Users\Administrator\gf-local\gf-rgl-src`) for any future
grammar work: compile with `gf -path="<rgl>/src/english:<rgl>/src/abstract:<rgl>/src/api:<rgl>/src/prelude:<rgl>/src/common"
-make grammar/MetonymyEng.gf`, then `gf --run Metonymy.pgf` for an
interactive `p`/`l` session -- no more spending a CI round on something
testable in seconds. The compiled `.gfo`/`.pgf` artifacts are already
gitignored (`*.gfo`, `*.pgf`), so nothing from this needs cleanup before
committing grammar changes.

**Deliberately deferred, with reasoning, not just noted:**

- **Appositives/parenthetical asides of arbitrary length.** GF's `String`
  category matches exactly one token during parsing (the same limit that
  motivated `OpenPN2`/`OpenPN3`). A real appositive is often longer than
  two words ("a county in the U.S. state of Alabama"), and no fixed
  arity scales to cover that combinatorially. The only GF-native path to
  unbounded length is a recursive comma-bracketed "list of words"
  category -- a materially different, higher-ambiguity-risk mechanism
  than anything in this grammar so far, the same class of risk that made
  the original `PrepPP` experiment fail. Asked the user explicitly before
  scoping this batch; the answer was to defer it, not attempt it blind --
  this is now testable locally (see above) if it's revisited, rather than
  needing another multi-CI-round investigation.
- **Numerals** (the `has_digit` signal: 49%/28%). Weaker, less isolated
  evidence than `has_comma` -- the two signals are not mutually
  exclusive, so a comma-caused failure can just as easily also contain an
  incidental digit. Needs its own narrower diagnostic (e.g. `has_digit`
  among rows *without* `has_comma`) before designing a construct for it,
  rather than guessing what grammatical role the number plays (a date? a
  count?) without that.

`tests/evaluation/test_compile_gf_constraints_subordinate_clauses.py`
covers the tree-walker contract for both families in pure Python (arity,
that `first_node` recurses into the wrapped clauses the same way it
already does for `AndS`/`OrS`, that a short appositive subject degrades
safely). `tests/evaluation/test_gf_parse_diagnostic_matrix.py`'s real
compiled-grammar cases (a representative fronted clause, a second
fronted conjunction, a trailing clause, both appositive arities, plus a
`linearize` smoke test) are the decisive regression coverage --
confirmed passing against the real engine, `spaceBeforeCommas` included,
not just compiling. `engine/test/Main.hs` covers `spaceBeforeCommas`
itself directly (a pure function, no GF/PGF dependency): inserts exactly
one space before a bare comma, is a no-op when one is already there or
there's no comma at all, handles multiple commas in one sentence, and
handles a comma as the very first character safely.

### Batch 2: a real resolve_action bug, plus a second grammar batch found by reading actual failures

The real `contextual-tower-evaluation.yml` run after the tokenizer fix
above showed recall still at 0.0, WiMCor's `literal_prediction_reasons`
byte-identical to the pre-fix baseline, and ConMeC one row *worse*
(`ok:empty-fiber` 3 to 2). Confirmed this wasn't a stale build (the run's
`head_sha` matched the fix commit exactly). So the fix was real and
correct -- the constructs it targeted (`BecauseS`-family fronted/trailing
clauses, `ApposCommaPN1`/`ApposCommaPN2`) just aren't the shape most real
WiMCor/ConMeC comma sentences actually take.

**Local reproduction, this time reading the actual sentences.** Using
this session's already-established local-reproduction recipe (download
real WiMCor v1.1 + ConMeC, `prepare_wimcor.py`/`prepare_conmec.py`,
`adapt_metonymy_corpus_for_tower.py --sample-size 150 --seed 0`, matching
`contextual-tower-evaluation.yml` exactly) combined with the local GF
toolchain from the section above, every `gf_sentence` in the 150+150
sample was reconstructed (`resolve_action` + `sentence_span_containing`
are pure Python, no Wikidata snapshot needed for this) and parsed against
a locally compiled `GeneratedMetonymy.pgf` with the engine's
`spaceBeforeCommas` preprocessing applied -- the actual failures could be
read directly instead of inferred from aggregate signals.

**Finding 1: two real bugs in `resolve_action`'s no-hint fallback path.**
`run_contextual_corpus.py`'s own dependency-hint precompute fails in this
project's actual CI too (confirmed from a real CI log:
`ModuleNotFoundError: No module named 'stanza'`), so the no-hint fallback
in `scripts/contextual_rule_compiler.py`'s `resolve_action` is not a rare
corner case -- it's what every real evaluation row goes through. Reading
real failures surfaced two distinct bugs there, both producing outright
nonsense text, not just missing grammar:
- A word *inside* the target's own mention span could itself match an
  unrelated VerbNet lemma's inflected form -- the source "High Point"
  contains "Point", also a verb -- and since it sits at distance ~0 from
  the target's own start, it could outrank the real governing verb
  elsewhere in the sentence purely on proximity: `"Barrino was raised in
  High Point"` became `"...raised in High points"`, the source's own
  second word verb-conjugated in place. Fixed by excluding any candidate
  phrase that overlaps the target's own span from consideration.
- Without a dependency hint, voice was always assumed active, silently
  replacing an already-correct passive surface ("is based") with a
  freshly reconjugated active one ("is bases"). Fixed with a cheap, local
  heuristic: if the matched surface text is exactly the participle form
  used for passive (not the bare lemma) and is immediately preceded by a
  form of "be" already in the unedited text, the sentence was already
  passive -- no dependency parse needed to see that. (The first version
  of this fix prepended a fresh "is " unconditionally, producing "is is
  based" double auxiliaries -- caught locally before it ever reached CI,
  by testing against the same real sample.)

**Finding 2: the remaining grammar gaps are a long tail, not one
dominant cause.** Categorizing real (non-garbled) failures by shape found
nested PP chains ("in the Benslow area of Hitchin in Hertfordshire"),
parenthetical acronyms ("(CEO)", "(HOLA)"), fronted date/time adverbials
("On 18 May 2010, ...", "In 1805, ..."), pronoun subjects/objects ("he",
"his" -- previously *zero* pronoun support existed at all), long
appositive lists (3+ items), and general embedded/relative clauses --
no single fix closes more than a handful of sentences. Added what was
verifiable as safe and testable locally in one pass:
- **`OfPP : NP -> PP`** -- the missing thirteenth preposition. "of" is
  one of the most common in English NP-modification ("President of X",
  "part of Y", "University of Z") and was simply absent from the
  original twelve.
- **PP chaining** ("a general in Hitchin of Hertfordshire") needed *no*
  new code at all -- `ModifyNP : NP -> PP -> NP` already recurses on its
  own output type, confirmed to parse correctly once tested directly.
- **`OnFrontedS`/`InFrontedS`/`FromFrontedS : NP -> S -> S`** -- fronted
  date/time adverbials, the same hand-rolled capitalized-literal idiom
  `BecauseS`/`IfS`/`WhenS`/`AlthoughS` already use, for the identical
  reason: `OnPP`/`InPP`/`FromPP`'s own preposition words are hardcoded
  lowercase, with no capitalized variant, and this is the first time any
  of them needs to be sentence-initial.
- **`ParenNP : NP -> String -> NP`** -- a parenthetical acronym/gloss
  right after an NP. Needed the *exact* same fix `ApposCommaPN1`/
  `ApposCommaPN2` needed: without spacing, `"(HOLA)"` is one indivisible
  token that an unrelated existing rule (`OpenPN3`) silently absorbed
  instead of `ParenNP` ever matching -- confirmed directly, not assumed,
  by testing both spaced and unspaced input locally. Fixed the same way:
  a new `spaceAroundParens` in `engine/src/Metonymy/GF.hs`, composed with
  `spaceBeforeCommas` in `parseEnglish`, inserting a space on whichever
  side of `(`/`)` would otherwise glue to an adjacent non-space
  character.
- **`HePN`/`ShePN`/`ItPN`/`TheyPN : NP`** -- plain pronoun subjects and
  objects, via RGL's own closed `Pron` vocabulary (`Structural.gf`,
  already reachable through the open `Syntax` interface) and `mkNP`'s own
  `Pron -> NP` overload. No new `open`, no open-ended `String` parameter.
  Previously entirely unsupported: every NP-building rule before this
  needed a proper noun, a common noun, or a coordination of those --
  "he"/"his" were among the single most frequent tokens real failures
  still stopped on.

**Deliberately still deferred**, the same class of higher-risk or
higher-effort items as before: appositive/coordination lists of 3+ items,
general embedded/relative clauses beyond `ModifyRelVP`'s existing single-
VP coverage, and arbitrary nested subordinate structure. Each would need
either the still-deferred comma-bracketed "list of words" category (real
ambiguity risk, not attempted) or substantially more grammar machinery
than a single batch can safely verify.

**Verification methodology**: every construct in this batch was compiled
and parsed against a real local `gf.exe` build *before* being written
into a test file, the same discipline the tokenizer-bug investigation
established -- not another round of CI-guessing. Re-running the full
150+150 local reproduction before and after this batch (both fixes and
all five new constructs) moved successful local parses from 11/150 to
14/150 (WiMCor) and 28/150 to 30/150 (ConMeC) -- modest, but real and
individually attributable, not a guess. `tests/evaluation/test_resolve_action_positional_fixes.py`
covers both `resolve_action` fixes directly; `tests/evaluation/test_compile_gf_constraints_batch2.py`
covers the tree-walker contract for all five new grammar constructs;
`tests/evaluation/test_gf_parse_diagnostic_matrix.py` gained eight new
real-sentence regression cases, one per construct, each independently
verified against the real compiled grammar first.

### Cumulative constituent layers

Supported positive constituents are elaborated in their semantic composition
order rather than as a flat token list:

```text
verb
verb + object head
verb + composed adjective/object
verb + object modifier
```

The lexical anchor of each constraint spans the cumulative surface phrase, so
the CLI exposes labels such as `declare`, `declare programme`, and
`declare programme in physics`. VerbNet supplies action roles, its pinned
FrameNet links supply frame identities, and WordNet supplies argument sorts.

`RequiresSome relation requirement` is the executable existential fragment:
it holds for candidate `x` exactly when the frozen snapshot contains some
`relation(x, y)` and `y` satisfies `requirement`. Both Haskell and the
independently compiled Agda checker evaluate this witness at every prefix.
Frame/argument combinations without an audited entity-level capability
projection still receive a compatibility layer, but that layer cannot claim
or invent a capability fact. Capability projections are global,
sort-and-frame-level rules, not sentence scenarios.
After every cumulative constraint prefix, Haskell calls compiled Agda
`contextLayerCheck` for every survivor and every obstruction before advancing
to the next stage.

Run the complete proposal-to-tower path without writing a scenario manually:

```bash
python3 scripts/run_automatic_contextual_pipeline.py \
  --engine build/metonymy \
  --snapshot data/wikidata-openalex-snapshot \
  --sentence "Waterloo announced a programme in physics" \
  --source Waterloo

python3 scripts/run_automatic_contextual_pipeline.py \
  --engine build/metonymy \
  --snapshot data/wikidata-openalex-snapshot \
  --sentence "John reads Masnavi" \
  --source Rumi \
  --contract-target Masnavi
```

WordNet and OpenAlex adapters operate on local/versioned artifacts:

```bash
python3 scripts/import_wordnet_context.py \
  --wordnet-dir /usr/share/wordnet \
  --output data/wordnet-context-rules.json

python3 scripts/import_openalex_context.py \
  --snapshot data/wikidata-multidomain-snapshot \
  --source-qids Q1049470,Q2004561 \
  --output build/openalex-context-evidence.jsonl
```

The complete FrameNet XML adapter imports frame definitions, FEs, lexical
units, and FE/GF/PT valence patterns from a user-supplied 1.7 distribution:

```bash
python3 scripts/import_framenet_context.py \
  --framenet-dir /path/to/fndata-1.7 \
  --output build/framenet-context
```

Pass `--framenet-snapshot build/framenet-context` to the automatic pipeline.
When the licensed XML is absent, pinned VerbNet FrameNet links remain a
metadata fallback. The 32 evidence-ranked role-capability projections in
`data/framenet-role-capabilities.json` are generated reproducibly and remain
preferences.

External evidence is merged by `merge_context_evidence.py`, which recomputes
`graph_sha256`. It cannot silently mutate an already certified snapshot.

## Running WiMCor/ConMeC through the tower

`run_contextual_corpus.py` expects `{id, sentence, source, family}` rows, not
the flat pipeline's `{id, source, text, target, gold, gold_bridge, ...}` shape
(`scripts/evaluation/prepare_wimcor.py`/`prepare_conmec.py`).
`scripts/evaluation/adapt_metonymy_corpus_for_tower.py` converts one into the
other:

```bash
python3 scripts/evaluation/prepare_wimcor.py \
  --archive /path/to/wimcor-v1.1.tar.gz --split test \
  --output build/evaluation/wimcor-test.inputs.jsonl

python3 scripts/evaluation/adapt_metonymy_corpus_for_tower.py \
  --dataset build/evaluation/wimcor-test.inputs.jsonl \
  --sentences-output build/evaluation/wimcor-test.tower-sentences.jsonl \
  --gold-output build/evaluation/wimcor-test.tower-gold.jsonl

python3 scripts/evaluation/run_contextual_corpus.py \
  --dataset build/evaluation/wimcor-test.tower-sentences.jsonl \
  --engine build/metonymy \
  --snapshot data/wikidata-openalex-snapshot \
  --output build/evaluation/wimcor-test.tower-inference.jsonl

python3 scripts/evaluation/score_contextual_detection.py \
  --inference build/evaluation/wimcor-test.tower-inference.jsonl \
  --gold build/evaluation/wimcor-test.tower-gold.jsonl \
  --output build/evaluation/wimcor-test.tower-report.json
```

**The adapter is lossy by construction, not by oversight**: WiMCor and
ConMeC only ever annotate metonymic-vs-literal plus a bridge-family type
(e.g. `location-for-institution`); neither names a specific correct
Wikidata entity. `score_qid_fibers.py`'s exact-QID-in-fiber metric --
the one the `contextual-multidomain` audited/silver fixtures above use --
cannot be computed for these corpora at all, since there is no
`gold_qids` to compare against. `score_contextual_detection.py` scores
the weaker claim these corpora actually support instead: for a
gold-metonymic mention, did the tower run successfully and end with a
non-empty final fiber (some bridged reading survived every stage); for a
gold-literal mention, did it correctly end with none. This mapping ("ok
+ non-empty fiber" = predicted metonymic) is a design choice documented
in that script's own docstring, not something the engine reports as a
native flag -- read it before citing precision/recall/F1 from this path.

**Coverage caveat**: the frozen `data/wikidata-openalex-snapshot` and the
current `composition_matrix`/`context_templates` coverage are both still
narrow (a handful of adjective×noun sorts, a curated multi-domain entity
set). Running the full WiMCor/ConMeC corpora through this path today will
mostly abstain (`gf-parse-failed`/`semantic-composition-failed`/
`source-qid-unresolved`) rather than produce a large, representative
sample of genuine tower-verified endpoints -- `literal_prediction_reasons`
in the score report shows exactly which. Scaling this up further is
Items 2-4's job (`scripts/build_wikidata_api_index.py` run at real
corpus scale, more `composition_matrix`/`context_templates` coverage,
more GF grammar constructions), not this adapter's.

### Source-mention disambiguation via the tower itself

An exact-alias match against a corpus-scale snapshot (see
`data/SOURCES.md`'s "Wikidata live-API runtime index" section) very often
yields more than one QID for one surface -- ordinary place names are the
worst offender: a live-API snapshot built from a 300-sentence WiMCor/
ConMeC sample resolved `"Liverpool"` to 12 distinct QIDs, `"Boston"` to
10, `"Santiago"` to 17, almost all of them identically-named minor US
census-designated places/unincorporated communities rather than the
entity the sentence actually means. `propose_contextual_scenario.py` does
not try to pick one: it hands the full candidate list to
`run_automatic_contextual_pipeline.py`, which runs the (candidate-
independent) action/GF-parse/constraint-compilation stages exactly once
and then the tower's own existing per-layer narrowing -- unmodified,
still `contextLayerCheck`/`runtimeCheck`-verified -- once per candidate
QID. A candidate is confirmed only if its own run ends with a non-empty
final fiber, i.e. something reachable from *that* QID actually satisfies
every constraint the sentence's words imposed; a same-named township with
no matching institution nearby simply dead-ends. Exactly one confirmed
candidate is the answer; zero is a legitimate literal prediction (no
candidate identity supports a metonymic reading); two or more is reported
as `source-disambiguation-ambiguous` (`SystemExit(6)`) rather than guessed
-- the same exact-match-or-abstain policy the entity linker itself already
follows. This only touches the untrusted proposer side of the trust
boundary (`docs/architecture.md`: "Hard search results are untrusted
until `runtimeCheck` succeeds"); no formal theorem changed. `--contract-target`
keeps the older, stricter single-candidate requirement, since a
contraction can be *correctly* rejected by the formal checker and that
must not be confused with a disambiguation failure.

### Sub-bucketing the three new dominant abstain reasons

After the batch-2 grammar additions (fronted/trailing subordinate clauses,
short comma appositives, `OfPP`, fronted dates, `ParenNP`, pronouns) and
the two real `resolve_action` bug fixes above, a real corpus evaluation
run showed `exit7` (`gf-parse-empty`, the GF-parsing bottleneck this
session spent most of its time on) had moved only slightly, and three
*different* failure categories now dominate instead:
`unsupported-action-role` (missing VerbNet-action vocabulary for the
sentence's governing verb), `nested-modifier-unsupported` (the metonymy
target sits inside a nested NP modifier -- a possessive, a relative
clause, an adjective -- that `resolve_action` deliberately refuses to
guess a role for), and `exit4` `semantic-composition-failed` (a handful
of distinct, already-enumerated failure modes inside
`compile_gf_constraints`'s own tree walk).

One correction found while planning this instrumentation: unlike `ci.yml`
(confirmed by reading its own workflow file -- it never installs Stanza,
so every local reproduction on this session's dev machine, which lacks a
working Stanza install for unrelated Windows/PyTorch DLL reasons, went
through `resolve_action`'s no-hint positional fallback), the real
`contextual-tower-evaluation.yml` workflow *does* install Stanza via
`scripts/bootstrap_dependency_frontend.sh`. That means most real
evaluation rows actually go through `resolve_action`'s
`dependency_hint`-driven `direct-argument`/`nested-modifier` path, not
the no-hint fallback -- so diagnosing these three categories needed safe,
text-free instrumentation added to the real pipeline and measured by a
real CI run, the same discipline already used for `exit1`/`exit2`/`exit7`
earlier in this document, rather than another local no-Stanza
reproduction.

**What was added, all content-free by construction (see each function's
own docstring for exactly what makes it safe):**

- `scripts/annotate_dependency_hints.py`'s `ClassifyResult` gained a
  seventh field, `nested_modifier_deprel` -- the specific UD relation
  (one of the eight in `NESTED_MODIFIER_DEPRELS`) that made a target
  count as a nested modifier in the first place, previously computed and
  then discarded before reaching `resolve_action`.
- `contextual_rule_compiler.resolve_action` now raises
  `f"nested-modifier-unsupported:{deprel}"` when a hint carries that
  field, and `f"unsupported-action-role:{governing_lemma}"` on the
  `direct-argument` path when the hint's own `governing_lemma` is known
  (the no-hint positional fallback still raises the bare string -- there
  is no single "the lemma that should have matched" when the search ran
  over every window in the sentence at once). Both suffixes reuse a risk
  class this project already treats as safe to aggregate: a closed-
  vocabulary UD relation label, or one common English verb lemma (or a
  `"<verb> <preposition>"` phrasal reconstruction) -- never sentence text.
- `scripts/evaluation/score_contextual_detection.py`'s `literal_reason`
  now recovers that suffix (`exit1_suffixed_token`) so
  `literal_prediction_reasons` reports e.g.
  `failed:exit1:nested-modifier-unsupported:nmod:poss` or
  `failed:exit1:unsupported-action-role:announce` as a natural histogram,
  instead of one undifferentiated count per category.
- A new `exit4_reason_bucket` sub-buckets exit 4 the same way
  `exit2_candidate_bucket`/`exit7_gf_sentence_bucket` already sub-bucket
  their own exit codes: `run_automatic_contextual_pipeline.py`'s exit-4
  branch JSON-wraps the failure as `{"status":
  "semantic-composition-failed", "gf_tree": ..., "detail": str(error)}`;
  `exit4_reason_bucket` reads only `"detail"` (never `"gf_tree"`, which
  does echo real sentence content -- the GF tree's own string leaves) and
  matches it against `EXIT4_KNOWN_FAILURE_TOKENS`, the complete, already-
  enumerated set of fixed messages `compile_gf_constraints`/`_origin`/
  `_cumulative_origin` can raise (`"malformed GF tree near "`, `"GF
  lexical token is absent from source: "`, `"ambiguous noun sort for GF
  composition: "`, `" has no role rule for "`, and five others), the same
  finite-message-set approach `KNOWN_FAILURE_TOKENS` already uses for
  exit 1. Falls back to `"unrecognized"` on anything unparseable or
  unmatched, same degrade-gracefully policy as its siblings.

Covered by `tests/evaluation/test_annotate_dependency_hints.py` (25
tests, including one confirming the deprel survives all the way through
`annotate()`'s own output dict),
`tests/evaluation/test_resolve_action_diagnostic_suffixes.py` (6 tests
on both new suffixes, including the backward-compatible bare-string
fallback), and new cases in
`tests/evaluation/test_score_contextual_detection.py` (the suffix
recovery, every `EXIT4_KNOWN_FAILURE_TOKENS` entry, and an explicit
never-leaks-the-gf-tree-or-interpolated-content check).

**Bug found by the first real run, fixed before drawing any conclusions
from it**: the real breakdown's `nested-modifier-unsupported`/
`unsupported-action-role` entries all carried a stray trailing `\"`
(e.g. `nested-modifier-unsupported:appos\"`). `exit1_suffixed_token`'s
first version assumed `failure_text` was a raw Python traceback and
captured everything up to the next newline -- but the only real origin
of these two suffixed tokens (`resolve_action`, called exclusively from
`propose_contextual_scenario.py`, which does `raise
SystemExit(str(error))`) is always JSON-wrapped by
`run_automatic_contextual_pipeline.py`'s "propose-scenario-failed"
exit-1 branch into `{"status": ..., "sentence": ..., "detail": <bare
message>}`, printed with `json.dumps(..., indent=2)`. The naive raw-text
regex captured the JSON string value's own closing quote as part of the
suffix. Fixed by parsing `failure_text` as JSON first and reading only
its `"detail"` field (falling back to the raw text, with quote
characters excluded from the capture as a second line of defense, for
any failure text that genuinely isn't JSON-wrapped) -- the same
JSON-first pattern `exit2_candidate_bucket`/`exit4_reason_bucket`/
`exit7_gf_sentence_bucket` already use. Covered by two new regression
tests reproducing the exact real shape.

**Real breakdown, first read (corrected data)**:

- `nested-modifier-unsupported` is overwhelmingly `nmod` (45/50 WiMCor
  rows, 6/11 ConMeC rows) -- a plain nominal modifier, not the
  possessive/relative-clause/adjective shapes also in
  `NESTED_MODIFIER_DEPRELS`, which barely register (`compound` 4+3,
  `appos` 1+1, `nmod:poss` only 1 in ConMeC).
- `unsupported-action-role` in WiMCor is, without a single exception,
  a `"<verb> <preposition>"` phrasal reconstruction (41 distinct pairs,
  each appearing 1-6 times) -- never a bare verb. Checked, not guessed:
  `data/predicates.tsv` and `data/verbnet-action-roles.tsv` (the only
  two sources `load_action_roles` reads) contain zero lemma entries with
  a space in either file. `annotate_dependency_hints.py`'s `obl`+`case`
  handling (`lemma = f"{head.lemma} {case_word.text.lower()}"`) always
  constructs a two-word governing_lemma for this deprel shape, but
  `resolve_action`'s `by_form` index -- built from `action_forms(role.lemma)`
  over those same two single-word-only files -- can structurally never
  contain a two-word key. This makes the WiMCor `obl`-path lookup fail
  unconditionally, independent of whether the bare verb (e.g. "arrive",
  "hold", "raise") already has real ActionRole coverage under its own
  single-word lemma -- a lookup-format bug, not a vocabulary gap, and
  the likely single dominant cause behind most of WiMCor's
  `unsupported-action-role` count. ConMeC shows a mixed picture: 8 of its
  ~24 rows are the same phrasal shape, but the rest are bare single-word
  lemmas (`advocate`/`breed`/`consume`/`overpower`/`print`/`process`/
  `publish`/`do`, plus a couple of likely-unlemmatized surface forms
  like `condem`/`drank`) -- genuine vocabulary or lemmatization gaps,
  not the same structural bug.
- `exit4` is dominated in ConMeC by `"malformed or incomplete GF tree"`
  (23/25 rows) -- `parse_gf_tree` leaves tokens unconsumed, most likely
  because some GF constructor `trees[0]` uses is missing (or has the
  wrong number) from `ARITIES` (`ARITIES.get(token, 0)` silently treats
  an unlisted constructor as 0-ary). WiMCor barely reaches `exit4` at all
  (2 rows total) since more of its rows fail earlier, at `exit1`/`exit7`.

### Phase 2, round 1: the phrasal-lookup fix and the exit4 constructor diagnostic

Two of the three leads above turned into concrete fixes, landed together
(the third -- whether `nmod`-dominant nested-modifier is worth a
`PositiveGFTree`/`Elaborator.hs` widening -- is deliberately deferred,
since that touches Haskell/Agda and its own real effect still needs its
own measurement first, the same "one risky thing at a time" discipline
used throughout this document):

- **`resolve_action`'s `obl` bare-verb fallback.** When the phrasal
  `"<verb> <preposition>"` key misses `by_form` (the confirmed-structural
  cause of essentially all of WiMCor's `unsupported-action-role` count
  above), retry with just the bare verb -- the first word of
  `governing_lemma`. The retry narrows the matched span to the verb's
  own token, found via a simple, well-justified heuristic (the first
  word-token inside `[governing_start:governing_end]`): English always
  places an `obl`'s governing verb before its case-marking preposition,
  with or without an intervening adverb ("argued strongly against" ->
  "argued"). This matters because `propose_contextual_scenario.py`
  replaces exactly `sentence[action["start"]:action["end"]]` with
  `action["gf_form"]` -- reusing the full phrasal span for a bare-verb
  replacement would have deleted the preposition from the sentence
  entirely (e.g. "...is based in Hertfordshire..." ->
  "...is bases Hertfordshire..."). An exact phrasal match, if the
  vocabulary ever gains one, still wins outright and skips the fallback
  -- confirmed by a dedicated test using the full phrasal span. If the
  bare verb also has no coverage, the raised message still names the
  full original phrase (`unsupported-action-role:base in`, not just
  `:base`) -- more informative for whatever comes after this round.
  Covered by `tests/evaluation/test_resolve_action_obl_phrasal_fallback.py`
  (6 tests).

- **`parse_gf_tree`'s unrecognized-constructor diagnostic.** When a tree
  is left unconsumed (`"malformed or incomplete GF tree"`), scan its own
  tokens for anything shaped like a GF constructor (this grammar's own
  PascalCase `fun` naming convention) that ARITIES doesn't know about --
  excluding the confirmed-0-ary pronoun constants (`HePN`/`ShePN`/`ItPN`/
  `TheyPN`), which are legitimately absent from ARITIES rather than
  missing entries. When found, the raised message grows a
  `"; unrecognized constructor(s): <Name>,<Name>"` suffix -- still a
  prefix match for every existing `"malformed or incomplete GF tree"`
  consumer, so this only adds information, never changes existing
  behavior. A constructor name is grammar/Metonymy.gf's own closed
  vocabulary, never sentence text, the same safety class as
  `EXIT4_KNOWN_FAILURE_TOKENS` itself.
  `scripts/evaluation/score_contextual_detection.py`'s `exit4_reason_bucket`
  now recovers this suffix via `exit4_suffixed_token`, so
  `literal_prediction_reasons` can report e.g.
  `failed:exit4:malformed or incomplete GF tree:SomeConstructor` instead
  of the bare bucket. Covered by
  `tests/evaluation/test_parse_gf_tree_unrecognized_constructor.py` (5
  tests) and new cases in `test_score_contextual_detection.py`.

Full local suite after both fixes: 304 tests, same pre-existing 2
failures/13 errors/8 skipped baseline (Windows `python3`-alias), no
regressions.

**Next step**: re-run `contextual-tower-evaluation.yml` once more. The
`unsupported-action-role` histogram should shrink sharply in WiMCor if
the bare-verb-fallback hypothesis is right; any rows still failing after
it name genuine vocabulary gaps, not lookup-format ones. ConMeC's
`exit4` breakdown should now name the actual missing constructor(s), if
any single one dominates -- the concrete, evidenced basis for deciding
whether that specific GF construction is worth adding next, and whether
the `nmod`-dominant nested-modifier gap deserves the deferred
`PositiveGFTree`/`Elaborator.hs` work.

## Phase 1: building the GF tree from a UD parse instead of asking GF to parse raw text

Hand-growing `grammar/Metonymy.gf` one construction at a time (every
section above) runs into the same wall computational-semantics research
already hit and moved past decades ago: natural language's combinatorial
diversity against a closed, hand-curated grammar. The established
alternative -- broad-coverage dependency/CCG parse -> typed semantic
construction -> formal checker (the C&C/Boxer line of work, and modern
AMR-based pipelines) -- is a better fit, and this project already has
the first half of it: Stanza, so far only used for one narrow purpose
(`resolve_action`'s `dependency_hint`, classifying a single target
word). This phase generalizes that: build the *whole* GF tree from
Stanza's UD parse, and only ask GF's own parser to read raw text when
that isn't possible.

**Why this is safe to attempt at all**: confirmed by reading the code,
not assumed -- in the contextual tower path, a GF tree
(`run_automatic_contextual_pipeline.py`'s `trees[0]`) is consumed
*entirely in Python*. `compile_gf_constraints`
(`scripts/contextual_rule_compiler.py`) parses it with its own,
GF-independent `parse_gf_tree`/`ARITIES` walker, and only the
*constraints derived from it* (never the tree text itself) get
TSV-encoded and handed to the compiled Haskell engine
(`run_engine`'s row: `scenario/source_qid/action/role/max_depth/
bridge_relations/encoded_constraints`). So changing *how* the tree is
produced -- GF's own chart parser, or Python code assembling the same
tree syntax from a UD graph -- requires zero Haskell/Agda changes,
exactly the same guarantee that already let `dependency_hint` ship
without touching a single Agda theorem. The one thing that mechanism
gave up-front (a parser can't emit an ill-typed tree by construction) has
to be re-added explicitly: a hand-built tree is validated by running it
through `metonymy linearize` (the same diagnostic command added earlier
this session for the comma-tokenizer investigation) before it's trusted.

**What's implemented (Phase 1's own deliberately narrow first slice --
see this session's plan file for the full phase breakdown; every UD
shape past this one is explicitly deferred, added incrementally, one
real measurement at a time)**:

- `scripts/build_gf_tree_from_dependencies.py`'s `build_gf_tree(words,
  lemma, gf_function_by_lemma)` covers only the simplest possible
  transitive clause: one root VERB/AUX with exactly one `nsubj` and one
  `obj`/`iobj`, each either a proper noun (1-3 token `compound` chain,
  via the already-existing `OpenPN`/`OpenPN2`/`OpenPN3`) or a personal
  pronoun (`he`/`she`/`it`/`they` -> `HePN`/`ShePN`/`ItPN`/`TheyPN`).
  Every UD word in the sentence must have one of a small allowed-deprel
  set (`root`/`nsubj`/`obj`/`iobj`/`compound`/`punct`) or the whole
  sentence is declined (returns `None`) -- a passive, a PP modifier, a
  determiner, coordination, a relative clause, anything this narrow
  slice doesn't model bails out rather than risk silently dropping or
  misrepresenting content. The verb's own GF function name comes from
  `data/contextual-gf-actions.json` (`load_gf_function_by_lemma`, the
  same source `compile_gf_constraints` already reads as `gf_actions`,
  just inverted) -- the tree-builder never has to "discover" which V2
  matches the way GF's own parser would; `resolve_action` already
  resolved that.
- `scripts/annotate_dependency_hints.py`'s hint schema gained a new
  `"ud_words"` field (`serialize_sentence_words`/`find_sentence_ud_words`)
  -- a flat, JSON-safe dump of *every* word in the target's sentence
  (id/head/deprel/upos/lemma/text/character-span), not just the one
  target word `find_governing_structure`'s existing fields classify.
  Threading it through required no new plumbing in
  `scripts/evaluation/run_contextual_corpus.py`: the whole hint dict,
  whatever keys it carries, was already forwarded verbatim as one
  `--dependency-hint` JSON blob.
- `run_automatic_contextual_pipeline.py`: before asking `engine parse`
  to read `proposal["gf_sentence"]`, tries `build_gf_tree` on
  `--dependency-hint`'s `ud_words`; if it returns a tree, validates it
  via `engine linearize`; only on both successes does it skip `engine
  parse` entirely and use the built tree directly. Any decline at any
  step (no `ud_words`, `build_gf_tree` returns `None`, or `linearize`
  fails) falls through to the exact `engine parse`-on-raw-text path that
  already existed -- so this can only ever be an *additional* source of
  success, never a new source of failure. Verified directly (not just by
  code inspection): five hand-built trees round-tripped through the
  local `gf.exe`/pinned `gf-rgl` toolchain's own `l -lang=MetonymyEng`
  linearizer and produced exactly the expected English.

Tests: `tests/evaluation/test_build_gf_tree_from_dependencies.py` (17,
covering every accept/decline case above), new cases in
`tests/evaluation/test_annotate_dependency_hints.py` (the `ud_words`
field, `serialize_sentence_words`, `find_sentence_ud_words` -- 29 tests
total now), and `tests/evaluation/test_run_automatic_contextual_pipeline.py`'s
new `StanzaTreeFirstTests` (4 tests, using the real on-disk
`data/contextual-gf-actions.json` -- only `subprocess.run` is mocked --
confirming the skip-`engine-parse`-entirely path, and three distinct
ways of falling back to the legacy path unchanged). Full local suite:
329 tests, same pre-existing baseline, no regressions.

**Deliberately deferred** (see the plan file's own phase table): `obl`+
`case` (the 13 closed prepositions), coordination, passive, copula,
`nmod:poss`, `amod` (needs the common-noun `data/contextual-gf-nouns.json`
lexicon, the first place this narrow "only proper nouns/pronouns" scope
gets lifted), `acl:relcl`, fronted subordinate clauses, fronted PP-
adverbials -- each its own commit, its own tests, its own real
`contextual-tower-evaluation.yml` measurement, same discipline as every
other phase in this document. Comma-appositives of unbounded length and
parenthetical acronyms stay hybrid (punctuation-based, not pure UD deprel)
even after this transition completes.

**Next step**: commit, push, `ci.yml`, then a real
`contextual-tower-evaluation.yml` run. Phase 1 alone is not expected to
move recall much (it covers only the simplest clause shape), but should
show some `exit7` `run-1`/`run-2`/`run-3` rows (simple proper-noun-only
clauses previously failing GF's own parser) now succeeding via the
Stanza-built path instead -- confirming the mechanism end-to-end before
investing in the wider UD-shape coverage above.

## Phase 1, round 2: widening the tree-builder -- and a cheaper way to verify it

The plan's own next-phase list, above, assumed each UD shape would need
its own CI round to verify. It doesn't have to: `compile_gf_constraints`
only ever consumes tree *text*, never calls GF at all (confirmed in
Phase 1's own section above), and the local GF toolchain
(`C:\Users\Administrator\gf-local`) can `l -lang=MetonymyEng` any
hand-built tree in seconds. That closes almost the entire risk gap this
plan's per-phase CI rounds existed to manage -- the only thing that
genuinely needs a real corpus run is whether real WiMCor/ConMeC text
actually contains the UD shapes each addition targets, not whether the
code is correct. So this round adds six of the plan's remaining items at
once, each verified two ways before being trusted: a pure-Python unit
test per accept/decline case, and the actual generated tree text
round-tripped through the local GF toolchain's own linearizer to
confirm it is real, well-typed grammar/Metonymy.gf syntax -- not just
text this module's own code happens to produce.

**Added, each mapping a UD shape directly onto an existing grammar
construction (no semantic reinterpretation, only structural mapping)**:

- Common-noun NPs with a determiner (`a`/`an`/`the` only -- anything
  else declines) and an optional single adjective ->
  `OpenIndefCN`/`OpenDefCN`/`OpenAdjIndefCN`/`OpenAdjDefCN`. Foundational
  for the rest: it's what lets a copula-free sentence like "Waterloo
  announces a programme" build at all, and what a passive's own agent or
  a relative clause's own object can now be, not just a proper noun or
  pronoun.
- Passive (`nsubj:pass` + `aux:pass` + a "by"-agent `obl`) ->
  `PassCompl`. Declines without a "by" agent -- confirmed directly
  against the grammar: `PassCompl : V2 -> NP -> VP` always needs an
  agent argument, so a bare passive has no representation in
  grammar/Metonymy.gf today regardless of who builds the tree.
- Relative clause (`acl:relcl`, object position only) -> `ModifyRelVP`.
  Declines when the embedded clause has its own separate subject
  (`ModifyRelVP`'s "NP which VP" shape has no room for one -- the
  relativized noun fills the subject role implicitly).
- Fronted subordinate clause (`advcl`+`mark`, one of because/if/when/
  although) -> `BecauseS`/`IfS`/`WhenS`/`AlthoughS` (fronted) or
  `SBecauseS`/`SIfS`/`SWhenS`/`SAlthoughS` (trailing), chosen by
  comparing the embedded clause's own position against the main
  clause's subject.
- Fronted date/time oblique (`obl`+`case`, restricted to exactly "on"/
  "in"/"from" and positioned before the subject) ->
  `OnFrontedS`/`InFrontedS`/`FromFrontedS`.

A `_clause` helper builds "SubjectNP (Compl/PassCompl V2 ObjectNP)"
generically for any verb, shared by the main action clause, a relative
clause's own embedded verb, and a subordinate clause's own embedded
verb -- each of those verbs is looked up in `gf_function_by_lemma` by
its *own* UD lemma, not the caller-resolved one; only the main action's
own root verb is cross-checked against `resolve_action`'s resolved
lemma (a real safety fix found while designing this: `resolve_action`'s
positional fallback -- used whenever `dependency_hint`'s `dep_status`
isn't `"direct-argument"` -- can match a *different* word than UD's own
root, which the original Phase 1 code never guarded against; it now
declines instead of silently building a tree around the wrong clause).

**Found, not fixed, while verifying against the local GF toolchain --
each is why the corresponding item was dropped from this round rather
than attempted**:

- `PossNP`/`DefCN`/`IndefCN`/`ModifyRelCN`/`ModifyRelCNVP` cannot
  actually be constructed in grammar/Metonymy.gf today: it declares no
  function that *produces* a bare `CN` from scratch, only ones that
  *consume* one. Confirmed directly: `l -lang=MetonymyEng PossNP
  (OpenPN "Tolstoy") (OpenIndefCN "book" "books")` is rejected by GF's
  own type checker ("Couldn't match expected type CN against inferred
  type NP"). A handful of pre-existing pure-Python tests in
  `tests/evaluation/test_compile_gf_constraints_copula_relative_genitive.py`
  exercise exactly this ill-typed shape -- they test
  `compile_gf_constraints`'s tree-walking code against text no real GF
  parse could ever produce, the same false-confidence trap as the
  ApposCommaPN/OpenPN2 story earlier in this document. Not fixed here
  (out of scope for a tree-builder-only round); a possessive needs a
  grammar addition first, not just a mapping rule.
- Copula ("Waterloo is a county") is UD-structured with a NOUN as its
  own root, not a VERB/AUX -- `annotate_dependency_hints.py`'s
  `classify_word` never classifies that as `"direct-argument"` (its
  `GOVERNING_UPOS` check requires VERB/AUX), so `resolve_action` never
  resolves an action for it and the pipeline never reaches the tree-
  builder at all for such a sentence. Needs a new `dep_status`/
  `resolve_action` branch, not a tree-builder change.
- A verb-level oblique PP adjunct ("announces X in Y", the general
  case) has no VP-level attachment point in the grammar at all --
  `ModifyNP` only attaches a PP to a specific NP. Folding it into the
  object NP anyway ("announces (X in Y)") would silently reinterpret
  which constituent the PP modifies -- exactly the "wrong but type-
  correct" failure mode this whole approach exists to avoid, so it
  wasn't attempted (the fronted date/time case above is the one
  exception, safe because those constructors take the PP's own NP
  directly with no attachment ambiguity).
- Coordination (`conj`/`cc`) needs a closer read of how
  `compile_gf_constraints`'s `first_node` (a depth-first search for the
  *first* `Compl`/`PassCompl`) would attribute constraints when a tree
  ends up with more than one such node -- a real subtlety that could go
  wrong silently if rushed, so it waits for its own dedicated round.
- Nested UD `nmod` (an NP modified by another NP/PP, "the museum in
  Kent") stays unreachable for a different reason: a target sitting
  inside one is rejected by `resolve_action` itself
  (`dep_status == "nested-modifier"`) *before* the tree-builder would
  ever run -- the same "Deliberately left unresolved" gap
  `annotate_dependency_hints.py`'s own module docstring already names.

Tests: `tests/evaluation/test_build_gf_tree_from_dependencies.py` grew
from 17 to 35 (one fixture bug of its own caught along the way -- a
`mark` word's UD `head` must point at the embedded clause's own verb,
not its subject). All 13 distinct new tree shapes verified against the
local GF toolchain directly, not just against this module's own
expected strings -- listed inline in the commit, all linearizing to
plausible English ("Because Tolstoy announces Henry, Waterloo announces
Mary", "On 2010, Waterloo announces Henry", "Waterloo announces a large
county", ...). Full local suite: 347 tests, same pre-existing baseline,
no regressions.

**Next step**: same as before, just with more coverage behind it --
commit, push, `ci.yml`, then a real `contextual-tower-evaluation.yml`
run to see how much of `exit7` these six additions actually reach in
real WiMCor/ConMeC text.

## Phase 1, round 3: first real recall, the obl bare-verb fix confirmed, and a genuine new mystery

The first real `contextual-tower-evaluation.yml` run after round 2 gave
this session's first-ever non-zero recall: **WiMCor recall 0.0256,
precision 0.5, f1 0.049** (1 true positive, 1 false positive). Small in
absolute terms, but the first time any real sentence has made it all
the way through every layer of the tower this whole project.

**The `obl` bare-verb fallback (Phase 2 round 1, above) worked close to
as hypothesized**: WiMCor's `unsupported-action-role` histogram
collapsed from 41 distinct phrasal entries down to 6 (`donate to`,
`graduate from`, `headquarter in`, `locate in`, `locate near`,
`twin with`) -- these six are now genuine vocabulary gaps (the bare verb
itself has no `ActionRole` coverage either), not the lookup-format bug
that dominated before. ConMeC's own non-phrasal
`unsupported-action-role` list (`advocate`/`breed`/`condem`/`consume`/
`do`/`drank`/`overpower`/`print`/`process`/`publish`) is unchanged, as
expected -- that fix only ever targeted the phrasal-key mismatch, not
genuine vocabulary/lemmatization gaps.

**`exit7`/`exit4` row counts *rose*, not fell, in this same run -- the
expected shape of progress, not a regression.** Since `resolve_action`
now succeeds on far more rows, far more rows now reach the *later*
pipeline stages (GF parsing, semantic composition) that previously never
ran for them at all -- exactly the "blockers compound" pattern this
document has described since the very first grammar-coverage rounds.
Recall moving from 0 to a small positive number, while every later-stage
failure count grows, is what real forward progress against a multi-stage
AND-gated pipeline looks like; a flat or shrinking `exit7`/`exit4` with
recall still 0 would have been the concerning result.

**A genuine new mystery, found only because `exit4_reason_bucket`'s
suffix now exists at all**: several `"malformed or incomplete GF
tree"` rows this run named bare, *unquoted* capitalized words as
"unrecognized constructor(s)" -- `"A"`, `"The"`, `"I"`, `"It"`,
`"Albright"`, `"Giant"`, and comma-joined pairs like `"Do,Leno"`,
`"Let,Alabandus"`, `"Palace,Vaudeville"` (12 rows alone tagged
`"A,String"` in ConMeC). None of these match any real
`data/contextual-gf-actions.json`/`data/contextual-gf-nouns.json`
entry (checked directly, not assumed) -- and they don't look like this
project's own function-naming conventions (`CTX_<hash>`, `WN_<hash>`,
or the handful of readable demo names `Announce`/`Read`/`Drink`/`Sign`/
`Eat`/`Review`/`Study`/`Translate`/`Watch`/`Wear`/`ListenTo`/`VN_*`).
They read like fragments of real proper-noun surface text that ended up
*unquoted* in a tree somewhere -- which `build_gf_tree_from_dependencies.py`
should be structurally incapable of (it always quotes its own string
arguments via `_quote`, and any tree it builds is validated through
`engine linearize`'s own real type-checker before ever being trusted;
see that module's own docstring). That leaves the *pre-existing* legacy
`engine parse`-on-raw-text path as the more likely source, but this
was reasoned, not confirmed -- so rather than guess further, a third
option was added: **safely confirm which of the two tree sources
actually produced the row**, the same "measure, don't guess" discipline
already used for exit1/exit2/exit7.

`run_automatic_contextual_pipeline.py`'s exit-4 JSON payload now
carries a `"tree_source": "stanza" | "gf-parser"` field (set once,
before the `compile_gf_constraints` call, from whether
`stanza_built_tree` was non-`None`) -- content-free, just which of two
known code paths ran.
`scripts/evaluation/score_contextual_detection.py`'s new
`exit4_tree_source` reads it (falling back to `"unrecognized"` the same
way every sibling bucket function does), aggregated across all exit-4
rows into the score report's new `exit4_tree_source_counts` field
(mirroring `exit7_signal_counts`'s own aggregate-not-per-row pattern).
Tested directly: a Stanza-built tree that passes `engine linearize`'s
own validation but *still* later fails `compile_gf_constraints` on
unrelated semantic grounds (a nonsense adjective+noun pair absent from
the real, unmocked `data/wordnet-context-rules.json` -- a genuine,
reachable exit-4 trigger even through a well-formed tree) is correctly
tagged `"stanza"`; a malformed tree from the legacy `engine parse` path
is correctly tagged `"gf-parser"` (`tests/evaluation/
test_run_automatic_contextual_pipeline.py`'s new
`Exit4TreeSourceTaggingTests`, 2 tests, plus 4 new
`Exit4TreeSourceTests`/`ScoreTests` cases in
`test_score_contextual_detection.py`). Full local suite: 354 tests,
same pre-existing baseline, no regressions.

**Next step**: re-run `contextual-tower-evaluation.yml` once more. The
`exit4_tree_source_counts` field will say, for the first time, whether
this mystery is coming from the brand-new Stanza path (a real bug in
this session's own new code, needing a fix there) or the long-existing
`engine parse` path (a previously-invisible bug in code that predates
this session entirely) -- decisive either way, not another guess.

## Phase 1, round 4: tree_source for every outcome, not just exit4

Asked directly: how well does the Stanza path actually work on real
text? The honest answer at the time was "no idea" -- round 3's
`tree_source` tag only covered exit-4 *failures* (added specifically to
chase the "Albright" mystery), so there was no way to see how often the
Stanza path even ran, let alone succeeded, across the rest of the
corpus -- successes, exit 5, exit 6, and exit 3/7 all carried no tag at
all.

Generalized: `run_automatic_contextual_pipeline.py` now records
`tree_source` (`"stanza"` or `"gf-parser"`, computed once, right after
`stanza_built_tree` is decided) on *every* outcome that reaches tree-
building at all --
- exit 3 (`gf-parse-failed`) and exit 7 (`gf-parse-empty`): added to
  their own JSON payload (always `"gf-parser"` by construction -- the
  Stanza path structurally cannot reach either exit code, since a
  Stanza-built `trees[0]` is never empty and never starts with "The
  parser failed", but explicit beats a reader needing to know that
  invariant).
- Every outcome past a successful `compile_gf_constraints` call
  (success, exit 5, exit 6): a new, unconditional `"tree-source=..."`
  stdout line printed right next to the existing `"gf-tree=..."` one.
  `scripts/evaluation/run_contextual_corpus.py`'s own line-scan picks
  it up onto the result row directly (`result["tree_source"]`), the
  same way it already does for `"gf-tree="`/`"graph_sha256="`/etc.
- Exit 1/2 (before tree-building is even attempted) still carry no
  field at all -- correctly `"not-applicable"`, not a gap.

`scripts/evaluation/score_contextual_detection.py`'s new
`row_tree_source(inference_row)` unifies both representations (the
row's own top-level field for the first case, JSON-embedded for exit
3/4/7) into one lookup, aggregated across *every* row (not just literal
predictions) into the score report's new `tree_source_counts` field --
the first real answer to "what fraction of this corpus's rows actually
went through the Stanza path, and how many of those then failed
downstream vs. succeeded."

Tests: `tests/evaluation/test_run_contextual_corpus.py` (new file, 3
tests -- no prior test file existed for `run_one`'s line-scan at all,
scoped narrowly to the new field rather than retroactively covering
everything else in the same change), 2 new assertions in
`test_run_automatic_contextual_pipeline.py`'s existing Stanza-path
tests confirming the stdout line appears correctly for both sources,
and a new `RowTreeSourceTests` class (6 tests) plus one new `ScoreTests`
case in `test_score_contextual_detection.py`. Full local suite: 364
tests, same pre-existing baseline, no regressions.

**Next step**: re-run `contextual-tower-evaluation.yml` once more.
`tree_source_counts` will finally answer the question this round set
out to answer -- what fraction of real WiMCor/ConMeC rows the Stanza
path actually reaches and resolves, versus falling through to (or never
even reaching) the legacy `engine parse` path -- alongside whatever
`exit4_tree_source_counts` says about the "Albright" mystery from round
3.

## Phase 1, round 5: zero real Stanza successes, and why

Round 4's `tree_source_counts` gave a decisive, surprising answer:
**`{"gf-parser": 92, "not-applicable": 58}` in WiMCor, `{"gf-parser":
122, "not-applicable": 28}` in ConMeC -- zero "stanza" anywhere.** Not
"the coverage is narrow" (expected, and fine) but a hard zero across
every single real row that reached tree-building at all, on top of
Phase 1's own six covered UD shapes. That's suspicious enough to be a
bug, not just narrow coverage -- so, once again, measure before fixing.

**A precise hypothesis, found by re-reading the actual code rather than
guessing**: `build_gf_tree`'s `_main_clause` requires the sentence's UD
`root` word's own lemma to equal the resolved action's lemma
(`root["lemma"].casefold() != lemma.casefold(): raise _Bail(...)`).
But `annotate_dependency_hints.py`'s `classify_word` -- the source of
that resolved lemma whenever `dependency_hint`'s `dep_status ==
"direct-argument"` -- never requires the target's *governing* word
(whatever it's directly attached to in the UD graph) to be the
sentence's own overall syntactic root. A target embedded inside a
relative clause, a reporting/subordinate structure, or any other
multi-clause real sentence can have a governing verb that isn't the
root at all -- WiMCor/ConMeC rows are real excerpted sentences, not bare
"Subject Verb Object" examples, so this is very plausibly common. If
so, `build_gf_tree` would decline on `"root-lemma-mismatch"` for a large
share of real rows regardless of how many UD shapes it otherwise covers.

That said, this is one hypothesis among several plausible ones (real
sentences almost always carrying at least one modifier this narrow
phase doesn't yet model is at least as plausible a contributor) -- so
rather than commit to a large redesign on the strength of one reading,
`_Bail` now carries a closed-vocabulary reason code at every one of its
raise sites (`root-count`, `root-not-verb`, `root-lemma-mismatch`,
`verb-not-in-lexicon`, `subject-count`, `object-count`,
`np-unsupported-upos`, `pronoun-unrecognized`,
`proper-noun-chain-too-long`, `common-noun-determiner-or-adjective-count`,
`common-noun-unrecognized-determiner`, `passive-aux-count`,
`passive-agent-count`, `relative-clause-count`,
`relative-clause-verb-not-verb`, `relative-clause-has-own-subject`,
`relative-clause-verb-not-in-lexicon`, `leftover-words`,
`unsafe-text`), exposed via a new `build_gf_tree_decline_reason`
diagnostics-only entry point (reruns the same logic build_gf_tree does;
never called from inside it, so the normal success path pays nothing
extra). Each name is one of this module's own internal structural
checks -- never sentence text, the same safety class as every other
diagnostic in this document.

`run_automatic_contextual_pipeline.py` calls it whenever `build_gf_tree`
itself returns `None`, plus two of its own extra reasons for the gate
*around* the module (`"no-ud-words"` -- no UD parse to build from at
all -- and `"linearize-validation-failed"` -- build_gf_tree returned a
tree, but GF's own type checker rejected it), tagged on every outcome
the same way `tree_source` already is (JSON payload for exit 3/4/7, a
new unconditional `"decline-reason="` stdout line next to
`"tree-source="` for every other outcome).
`scripts/evaluation/score_contextual_detection.py`'s new
`row_decline_reason` unifies both representations, aggregated into a
new `decline_reason_counts` report field.

Tests: 19 new `BuildGfTreeDeclineReasonTests` cases in
`test_build_gf_tree_from_dependencies.py` (54 total now) -- one per
reason code, confirming the exact vocabulary a future real measurement
will actually report; 3 new assertions in
`test_run_automatic_contextual_pipeline.py`'s existing Stanza-path
tests; a new `RowDeclineReasonTests` class (6 tests) plus one new
`ScoreTests` case in `test_score_contextual_detection.py`; 2 new cases
in `test_run_contextual_corpus.py`. Full local suite: 392 tests, same
pre-existing baseline, no regressions.

**Next step**: re-run `contextual-tower-evaluation.yml` once more.
`decline_reason_counts` will say, with real data, whether
`root-lemma-mismatch` actually is the dominant cause (confirming the
hypothesis above and pointing at a real, scoped fix: build the tree
around whichever word `dependency_hint`'s own `governing_start` names,
not necessarily the sentence's UD root) or whether something else
entirely dominates (in which case the hypothesis was wrong, and the fix
needs to be something else) -- either way, decisive, not another guess.

## Phase 1.5: LLM as a third tree-source tier

Round 5's `tree_source_counts` came back before its own root-cause fix
could be measured: the user asked to add a *third*, wider-coverage
proposer instead of waiting on that one fix -- not to replace the
Stanza-UD tier or the legacy GF-parser fallback, but to extend the
existing fallback chain (Stanza &rarr; **LLM** &rarr; legacy GF-parser)
so real recall could move now, independent of when the UD-path root
cause gets fixed.

Two external, already-solved-seeming alternatives were checked and
rejected first. **PredPatt** (github.com/hltcoe/PredPatt), initially
recommended from general knowledge as a mature UD-to-predicate-argument
extractor, turned out on actual verification (not on paper) to be
unmaintained since 2021-02-24, not on PyPI, and built predominantly
around UD v1 deprel labels (`dobj`, `nsubjpass`, `aclrelcl`) that don't
match this project's UD v2 Stanza (`en_ewt`) output -- the recommendation
was walked back once checked. **Semgrex** (Stanza's own dependency-graph
query language) is actively maintained and guaranteed UD v2-compatible,
but only supplies a query language, not ready-made extraction rules --
useful for a future refactor of the pattern-matching internals, not a
drop-in replacement for this round.

**Epistemic framing, reused directly from the LLM promotion-evidence
pilot** (an already-existing plan section, not fully wired into CI):
Agda's checker verifies the *form* of what a proposer submits, never the
truth of a natural-language understanding claim it embodies. This LLM
tier is architecturally identical in status to the other two tree
sources -- an untrusted proposer, validated the same way, by `engine
linearize` and then by every downstream Agda-checked stage -- so this
addition needs zero new Agda theorems, exactly like the Stanza-UD tier
before it. The precision of whatever this tier contributes depends
entirely on the LLM's own judgment quality, not on anything the checker
proves; that is a property of this component, not a weakening of the
formal core.

**No API key, no network dependency beyond the CI runner itself**: this
tier talks to a local Ollama server via `scripts/propose_promotion_evidence.py`'s
existing `query_ollama` (stdlib `urllib.request`, `format: "json"`,
`DEFAULT_MODEL = "llama3.2:3b"`, `DEFAULT_ENDPOINT =
"http://localhost:11434/api/generate"`) -- a working precedent already
in the repo for the (separate, not-yet-CI-wired) promotion-evidence
pilot, reused directly rather than duplicated.

**This tier's structural advantage over the Stanza-UD one**: it never
needs to find "the governing verb" independently. The caller already
knows which verb (by lemma) `resolve_action` resolved, so the prompt
just asks the model for that verb's own subject/object directly. This
sidesteps round 5's exact structural gap (a target's governing verb need
not be the sentence's own UD root) rather than fixing it.

**Rendering** (`scripts/build_gf_tree_from_dependencies.py`): two new
functions, `build_gf_tree_from_llm_structure`/
`build_gf_tree_from_llm_structure_decline_reason`, mirroring
`build_gf_tree`/`build_gf_tree_decline_reason`'s own `_Bail`-with-reason
idiom exactly, and reusing all of that module's existing low-level
primitives (`_apply`/`_quote`/`_PROPER_NOUN_CONSTRUCTORS`/
`_PRONOUN_CONSTRUCTORS`/`_strip_outer_parens`) -- the LLM path just feeds
them a differently-shaped structure. First-round schema (same
"narrow slice first, measure, widen" discipline as Phase 1 itself):
active/passive voice, three NP forms (proper noun of 1-3 tokens /
pronoun / common noun with determiner and an optional single adjective).
No relative clauses, subordinate clauses, or PP modifiers yet. Every
tree shape (active proper-noun, 3-token proper noun, pronoun + adjective
common noun, definite/indefinite common noun, all four pronouns, passive
+ agent) was verified against the real local `gf.exe`/pinned `gf-rgl`
before being written into a test, the same discipline used throughout
this document.

**Proposer** (new `scripts/llm_propose_clause_structure.py`): a single
`PROMPT_TEMPLATE` asking for exactly one verb lemma's own
subject/object(/agent, if passive) as literal noun phrases copied from
the sentence -- never paraphrased, never invented -- in a fixed JSON
schema, with an explicit instruction to answer `{"voice": null, ...}`
(never guess) if any part doesn't fit. `propose_clause_structure(sentence,
lemma, query)` degrades to `None` on any failure at all: a query
exception, a non-dict response, a missing `"voice"` key, or the model's
own null-voice abstention -- uniformly, the same "unable is not an
error" policy already used throughout the pipeline's fallback chain.

**Wiring** (`scripts/run_automatic_contextual_pipeline.py`): two new CLI
flags, `--llm-proposer-model` (unset by default -- this tier is fully
inert unless a caller opts in) and `--llm-proposer-endpoint`. When the
Stanza-UD tier declines and `--llm-proposer-model` is set, this tier
tries next, before the legacy `engine parse` fallback: `query_ollama` is
asked for a clause structure, `build_gf_tree_from_llm_structure` renders
it, and the result is validated through the same `engine linearize` gate
every other tier already uses. `tree_source` becomes `"stanza"`,
`"llm"`, or `"gf-parser"` (previously only the latter two existed); a
new `llm_decline_reason` field (`"not-attempted"` when this tier never
ran at all -- Stanza already succeeded, or no model was configured; one
of `propose_clause_structure_with_reason`'s four reason codes --
`"query-exception"`, `"non-dict-response"`, `"missing-voice-key"`, or
`"voice-null-abstention"` -- when the proposer itself produced no usable
structure; a `build_gf_tree_from_llm_structure_decline_reason` code when
it did but the renderer declined; `""` when an LLM-built tree was
trusted) is tagged on every outcome the same
way `tree_source`/`decline_reason` already are.

**Plumbing through the rest of the chain**: `scripts/evaluation/run_contextual_corpus.py`
gained matching `--llm-proposer-model`/`--llm-proposer-endpoint` flags
(threaded into each `run_one` subprocess call only when set) and a new
`"llm-decline-reason="` line-scan branch.
`scripts/evaluation/score_contextual_detection.py` gained
`row_llm_decline_reason` (mirroring `row_decline_reason` exactly) and a
new `llm_decline_reason_counts` report field, aggregated across every
outcome the same way `tree_source_counts`/`decline_reason_counts`
already are. `.github/workflows/contextual-tower-evaluation.yml` gained
a `workflow_dispatch` input `llm_proposer_model` (default `llama3.2:3b`;
empty disables the tier and skips installing Ollama entirely --
identical behaviour to before this tier existed), a conditional
"Install and start Ollama" step, and passes `--llm-proposer-model`
through to `run_contextual_corpus.py`.

**Verification, same policy as Stanza throughout this whole document**:
there is no Ollama on the local development machine, and none will be
installed there without explicit permission -- everything above is
verified locally with pure Python and an injected fake `query` callable
(the same pattern `test_propose_promotion_evidence.py` already
established: business logic is tested this way, `query_ollama`'s own
HTTP layer is verified only by a real CI run). New tests: a
`BuildGfTreeFromLlmStructureTests` class (7 cases: each NP form, both
voices) plus a `BuildGfTreeFromLlmStructureDeclineReasonTests` class (14
cases, one per reason code) in `test_build_gf_tree_from_dependencies.py`
(75 tests total now); a new `test_llm_propose_clause_structure.py` (6
tests: prompt contents, well-formed passthrough, null-voice abstention,
query exception, non-dict response, missing-voice-key); a new
`LlmProposerTierTests` class (4 tests, mocking only `query_ollama`) in
`test_run_automatic_contextual_pipeline.py`; new tests for the
`"llm-decline-reason="` line-scan and CLI-flag threading in
`test_run_contextual_corpus.py`; a new `RowLlmDeclineReasonTests` class
plus one new `ScoreTests` case in `test_score_contextual_detection.py`.

Deliberately deferred to a later round: relative clauses, subordinate
clauses, and PP modifiers in the LLM schema -- cheaper to add here than
on the UD path (a new optional JSON field, not fifty lines of deprel
pattern-matching), but still its own round with its own measurement, the
same discipline as everywhere else in this document.

**Next step**: run the full local suite, commit, push, wait for `ci.yml`,
then re-run `contextual-tower-evaluation.yml` with `llm_proposer_model`
set -- `tree_source_counts` and `llm_decline_reason_counts` will give the
first real measurement of what this tier actually contributes on
WiMCor/ConMeC, independent of whether round 5's Stanza-UD root cause has
been fixed yet.

### First real run: two Ollama-integration bugs, neither in Python

Since none of this tier's Ollama-facing behavior can be checked without
a real Ollama install (deliberately never done on the local dev machine,
same policy as Stanza all session), the very first `contextual-tower-evaluation.yml`
run with `llm_proposer_model` set was also the first real test of the
"Install and start Ollama" step itself -- and it surfaced two bugs, both
in workflow/config, not in any Python this document already covers:

1. **`ollama serve &` raced the install script's own systemd service.**
   `install.sh` on Linux installs a systemd unit and starts it
   immediately -- confirmed directly from a real run's own log:
   `"Enabling and starting ollama service... The Ollama API is now
   available at 127.0.0.1:11434."` The workflow step then tried to start
   a *second* server on the same port, which always lost:
   `"Error: listen tcp 127.0.0.1:11434: bind: address already in use"`.
   Non-fatal on its own (the already-running systemd instance served the
   pull that followed regardless), but confusing and wasteful. Fixed by
   dropping the manual `ollama serve &` entirely and polling
   `http://127.0.0.1:11434/api/tags` until it answers instead of a blind
   `sleep 5`.
2. **`llama3.2:3b-instruct` is not a real Ollama tag.** This default
   (both the workflow's `llm_proposer_model` input and
   `propose_promotion_evidence.py`'s own `DEFAULT_MODEL`, reused by this
   tier) predates this round -- inherited from the LLM promotion-evidence
   pilot, whose own workflow-side integration had never actually run
   until this. The pull failed fast with `"Error: pull model manifest:
   file does not exist"` -- the signature of an unresolvable tag, not a
   network or reachability problem. Checked directly against Ollama's
   real model library (not assumed) before fixing: llama3.2's plain
   `3b`/`1b` tags *are* the instruct-tuned default Meta ships (a
   `-instruct-<quantization>` suffix only exists for specific
   quantized/precision variants, e.g. `3b-instruct-q4_K_M`, never a bare
   `3b-instruct`). Fixed by changing the default to `llama3.2:3b` in
   both places.

Same discipline as the PredPatt reversal earlier in this document:
verify a claim about an external tool/artifact against its real, current
source before shipping a fix for it, rather than trusting a
plausible-looking name that was never actually exercised.

### Second real run: no-response was mostly noise, missing-np is the real wall

With both Ollama bugs and the "an" determiner fix in place, a second
real `contextual-tower-evaluation.yml` run gave a much cleaner signal.
`tree_source_counts`' `"llm"` count roughly tripled (WiMCor 8&rarr;25,
ConMeC 10&rarr;39), and WiMCor's detection numbers moved for the first
time all session in a way attributable to this tier specifically
(recall 0.026&rarr;0.077, F1 0.049&rarr;0.130, true positives 1&rarr;3).

The new `llm_decline_reason_counts` breakdown (from the previous
round's `propose_clause_structure_with_reason` split) answered the open
question directly: `"query-exception"` came back at 1 (WiMCor) and 7
(ConMeC) out of over a hundred attempts each -- the old flat
`"no-response"` bucket dominating the first run was *not* mostly a
technical/network problem. Neither did `"voice-null-abstention"` or
`"missing-voice-key"` show up at any meaningful count. Instead, what
had been flattened into `"no-response"` redistributed almost entirely
into two places: more outright successes, and a large jump in
`"llm-active-missing-np"`/`"llm-passive-missing-np"` -- the model
naming a voice but leaving one of that voice's required NP slots
`null`, a schema-noncompliant hybrid the original prompt never
explicitly forbade. That pair is now the dominant single failure mode
in both corpora (60/150 WiMCor, 59/150 ConMeC) -- bigger than any other
LLM-tier bucket combined.

Per the user's own choice of which lever to pull next (of root-
lemma-mismatch, this prompt, the separate adjective-noun semantics gap
below, or stopping here), `PROMPT_TEMPLATE` in
`scripts/llm_propose_clause_structure.py` now says explicitly: a chosen
voice's required NPs must both be filled in with one of the three
supported shapes, *or* the model must use the complete `{"voice": null,
...}` abstention -- never a non-null voice paired with a null value in
one of its own required fields. This also makes explicit, for the first
time, that a passive sentence with no stated `"by X"` agent is out of
this round's scope (the renderer's `PassCompl` requires an agent) --
previously the model had no way to know that and would reasonably
extract a real, agent-less passive structure that was always going to
be rejected as `"llm-passive-missing-np"` downstream regardless of how
well it followed instructions. This prompt-only change can't invent new
successes (it doesn't widen what the renderer can build), but it does
turn wasted, always-failing attempts into honest, cheaper abstentions,
and gives a real test of whether the missing-np hybrid was a prompt-
clarity issue at all.

The other real finding from this run is out of the LLM tier's own
scope entirely: ConMeC's `"unsupported GF adjective-noun semantics"`
bucket jumped from 6 to 25 -- an already-known, already-bucketed
`compile_gf_constraints` limitation (not something this round
introduced), just hit far more often now because the LLM tier builds
many more adjective-modified common nouns than the legacy GF-parser
path ever did. Widening that semantic check is a separate task,
deliberately not pursued this round.

**Next step**: run the full local suite, commit, push, wait for
`ci.yml`, then re-run `contextual-tower-evaluation.yml` once more --
`llm_decline_reason_counts`' missing-np counts should drop now that the
prompt forbids the hybrid outright, either into more successes (if it
really was a prompt-clarity issue) or into `"voice-null-abstention"`
(if the model was already doing its best and the sentence genuinely
doesn't fit the three-NP-shape schema).

### Third real run: the prompt-tightening fix caused its own regression

The prediction above wasn't what happened. `"query-exception"` --
previously near zero (1/150 WiMCor, 7/150 ConMeC) -- became the
overwhelming majority of LLM-tier attempts (76/150, 108/150), and
`tree_source_counts`' `"llm"` count collapsed back down (WiMCor
25&rarr;4, ConMeC 39&rarr;6). The missing-np hybrid the prompt change
targeted *did* shrink sharply where it was even reached (WiMCor
`llm-active-missing-np` 48&rarr;2), but that's a hollow win when almost
nothing reaches a usable response at all anymore.

Measured, not guessed, before writing a fix: the previous round's
prompt addition took `build_prompt`'s output from 1539 to 2271
characters for the same sentence -- a 48% jump. On a CPU-only GitHub
Actions runner running `run_contextual_corpus.py --workers 4` (four
concurrent subprocesses hitting the same single Ollama instance),
`query_ollama`'s 60-second timeout easily explains a jump this large
and this sudden, given the previous round's near-zero baseline showed
60 seconds was clearly enough *before* the prompt grew.

Two changes, kept in one round since they answer two different
questions:

1. **Trimmed `PROMPT_TEMPLATE` back down** to 1752 characters (a 14%
   increase over the pre-regression 1539, not 48%) -- same rule (a
   chosen voice's required NPs must both be filled in, or abstain
   completely), stated once, concisely, instead of restated three
   times across two paragraphs.
2. **Split `"query-exception"` itself**, since it was already known to
   be the single largest bucket and a bare `except Exception` can't
   tell a timeout apart from the model's raw output not being valid
   JSON -- two very differently-fixed problems.
   `propose_clause_structure_with_reason` now distinguishes
   `"query-network-or-timeout"` (an `OSError` -- covers
   `urllib.error.URLError`/`HTTPError`, both `OSError` subclasses, and
   a raw socket timeout alike: no usable response was ever received)
   from `"query-malformed-response"` (a `json.JSONDecodeError` or
   `KeyError` -- a reply came back, just not shaped like JSON), with a
   generic `"query-exception"` kept only as a fallback for anything
   else unanticipated. `test_prompt_stays_reasonably_short` is a new
   regression guard (asserts `len(prompt) < 1900`) so a future prompt
   edit can't silently repeat this mistake.

**Next step**: run the full local suite, commit, push, wait for
`ci.yml`, then re-run `contextual-tower-evaluation.yml` once more.
If the regression really was timeout-driven, `"llm"` tree counts and
detection numbers should recover toward (or past) the second run's
levels, and `"query-network-or-timeout"` should drop back near zero.
If a large `"query-network-or-timeout"` (or a new
`"query-malformed-response"`) count remains even at the shorter prompt
length, that's a decisive, different next diagnosis -- worker
concurrency contention on a single CPU-only Ollama instance, or the
timeout itself needs raising -- not more prompt trimming.

## Fixing `root-lemma-mismatch`: build the tree around `governing_start`, not the UD root

Across every real `contextual-tower-evaluation.yml` run this session,
`decline_reason_counts`'s `root-lemma-mismatch` stayed the single
largest bucket in the whole Stanza tier -- 35/92 WiMCor, 43/122 ConMeC
(~63%/~46% of every Stanza-tier decline) -- unmoved since it was first
diagnosed (Phase 1, round 5, above). Asked directly what would move the
needle most, independent of the LLM tier's own tuning: fixing this.

**The bug was architectural, not a comparison typo.**
`_build_gf_tree_inner` finds the sentence's UD root (`deprel == "root"`)
and requires the already-resolved action's lemma to equal *that* word's
own lemma, or bails `"root-lemma-mismatch"`. But
`annotate_dependency_hints.py`'s `classify_word` -- the source of the
resolved action whenever `dependency_hint`'s `dep_status ==
"direct-argument"` -- only ever looks exactly one level up from the
target word, never requiring that word to be the sentence's own
structural root. In a real, syntactically complex WiMCor/ConMeC
sentence, the target's actual governing verb is very often embedded in
a relative, subordinate, or complement clause -- Stanza's own parse was
correct the whole time; the tree-builder's filter was just needlessly
narrow.

**The fix needed no new grammar.** `classify_word` already computes
`governing_start`/`governing_end` -- the governing word's own absolute
character span -- for exactly this case; `build_gf_tree` just never
received it, independently re-deriving "the verb to build around" from
the UD root instead. Confirmed by reading `compile_gf_constraints`'s own
tree-walkers directly: `first_node` (an unconditional depth-first
search for the first `Compl`/`PassCompl`) and `walk` (a separate,
similarly unconditional scan for `OpenAdjDefCN`/`OpenAdjIndefCN`, for
`FrameModifier`/`FrameComposition`) only ever derive constraints from
whatever tree they're actually given -- never anything syntactically
"outside" it. So a tree representing *only* the local clause around the
target's real governing verb, deliberately not representing whatever
wraps it, can only ever under-generate constraints, never derive a
wrong one -- the same risk class already accepted for this module's
other deliberately-unbuilt shapes (verb-level oblique PP adjuncts).

**One subtlety, found by tracing a concrete example, not guessed**: for
a passive clause, `classify_word`'s own `_passive_verb_span` anchors
`governing_start` to `min(content_verb.start, aux_pass.start)` -- and in
real English word order ("was announced"), the auxiliary precedes the
participle, so `governing_start` for a passive *root* clause points at
the auxiliary's own start, not the content verb's (the actual UD root).
Comparing `governing_start` to the root's own offset directly would
misroute a perfectly ordinary passive-root sentence into the new
embedded-clause branch, losing today's fronted-date/subordinate-clause
enrichment and its strict whole-sentence completeness check for no
reason. Fixed by resolving `governing_start` to an actual `ud_words`
entry first, hopping through exactly one `aux:pass -> its head` step
when that's what it resolves to, and only then comparing word identity
(never raw offsets) against the root.

**Implemented** (`scripts/build_gf_tree_from_dependencies.py`):
`build_gf_tree`/`build_gf_tree_decline_reason` gained a new optional
`governing_start: int | None = None` parameter (default `None` = 100%
today's pre-existing root-anchored-only behavior, unchanged). Two new
helpers: `_word_by_governing_start` (resolves the offset to a word,
with the `aux:pass` hop above) and `_subtree_ids` (walks `head`
pointers to compute one word's full descendant set). When the resolved
governing word is *not* the sentence's root, `_build_gf_tree_inner`
builds the local clause by calling the exact same `_clause` helper the
root-anchored path already uses (zero duplication -- `_clause`/`_np`/
`_object_np`/`_relative_clause_vp` are completely unchanged), explicitly
excludes any `mark` child of the governing verb from its own
completeness check (wrapper information like "because", not local-clause
content -- the same technique the existing subordinate-clause branch
already uses once it picks a `Because`/`If`/`When`/`Although`
constructor to account for its own `mark` word; here there's no such
wrapper constructor, so this is the only place that ever accounts for
it), and requires only its own local descendant subtree -- not the
whole sentence -- to be fully consumed. Four new closed-vocabulary
`_Bail` codes: `governing-start-not-found`, `governing-word-not-verb`,
`governing-lemma-mismatch` (mirrors `root-lemma-mismatch` exactly, kept
distinct so a future run can tell whether genuine mismatches persist on
each path separately), and `embedded-leftover-words` (mirrors
`leftover-words`, same reasoning). All four appear in
`decline_reason_counts` automatically -- it's a plain `Counter`, not a
closed allowlist, so no registration was needed anywhere else.
`scripts/run_automatic_contextual_pipeline.py`'s only change: thread
`dependency_hint_data.get("governing_start")` through to both call
sites.

**Deliberately not done this round**: no new `grammar/Metonymy.gf`
constructs at all -- this widens only *which verb* the existing local-
clause shapes get built around, never adds a new shape (an object-
relative modifying some other NP, reported-speech/`ccomp` as a
modifier, S-level coordination remain exactly as out of scope as
before). Coordination on the governing verb itself surfaces as the
already-existing `subject-count` (no bare workaround added). The
embedded branch never attempts its own nested fronted-date/subordinate-
clause enrichment -- any such extra structure on the embedded verb
correctly shows up as `embedded-leftover-words`, not silently dropped.
`governing_end` isn't threaded (`governing_start` alone, with the
existing `len(candidates) != 1` guard, is a sufficient unique key,
including for the Stanza multi-word-token span-collision edge case).
Multi-level embedding (the governing verb sitting two or more UD levels
below the root) needed no special handling at all -- `classify_word`
already always looks exactly one level up from the target regardless of
that verb's own depth, and this design never inspects anything above
the governing word, so arbitrary nesting depth already works uniformly.

Tests: a new `GoverningStartTests` class (10 cases) in
`test_build_gf_tree_from_dependencies.py` -- an `acl:relcl` case with
the embedded verb's own separate subject (distinct from the pre-existing
`RelativeClauseTests.test_relative_clause_with_its_own_subject_is_out_
of_scope`, which is about a relative clause modifying an NP *elsewhere*
in the sentence via `ModifyRelVP`; here the metonymy target itself sits
inside the relative clause, so `ModifyRelVP` is never entered at all),
an `advcl` case, the passive-root `aux:pass`-hop regression case, the
`governing_start=None` byte-for-byte regression case, a `ccomp`
(reported-speech) wrapper case that must still decline for the
*existing* `object-count` reason (proving the fix never inspects the
wrapper's own deprel -- `ccomp` is handled identically to `acl:relcl`/
`advcl`, it just happens to hit an unrelated, pre-existing grammar
limitation here) paired with a positive `ccomp` case that succeeds, and
one test per new `_Bail` code. One new test in
`test_run_automatic_contextual_pipeline.py` confirming `governing_start`
is threaded from `--dependency-hint` all the way into `build_gf_tree`
and still resolves to `tree-source=stanza` for an embedded-verb
sentence. No new GF constructors were introduced, so no new local
`gf.exe` verification was needed this round -- every tree shape produced
is one already verified in an earlier round. Full local suite: same
pre-existing baseline (2 failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then re-run
`contextual-tower-evaluation.yml` -- `decline_reason_counts` will give
the first real measurement of how much of `root-lemma-mismatch` this
actually recovers, and what (if anything) remains -- decisively, not
another guess.

### First real run: the fix reclassifies correctly, but redirects into other pre-existing walls -- and one, `subject-count`, is a real, buildable follow-up

`root-lemma-mismatch` did drop -- 35&rarr;20 (WiMCor), 43&rarr;14
(ConMeC) -- confirming the reclassification mechanism works. But
`tree_source_counts` still showed **zero** real `"stanza"` successes in
either corpus: every one of the 15 (WiMCor) / 29 (ConMeC) cases that
left `root-lemma-mismatch` landed on a *different* decline reason, not a
success. `root-lemma-mismatch` was masking a chain of other, pre-existing
limitations that were always there -- just never reached, because the
old code bailed before it could try.

The single largest of the newly-surfaced reasons, by far: `subject-count`
appeared for the first time at 12/150 (WiMCor) and 13/150 (ConMeC) --
accounting for most of the redirected cases on its own. Read directly:
`_clause` (the helper the new `governing_start`-anchored branch delegates
to, same as the root-anchored branch) only ever looks for a literal
`nsubj` child of the governing verb; when the governing verb turns out to
itself be a subject-relative `acl:relcl` ("the county **which** governs
Prussia" -- the relativized noun implicitly fills the embedded verb's
subject role, no separate `nsubj` word for it at all), there simply isn't
one to find. This exact shape was already fully supported elsewhere in
this module -- `_relative_clause_vp`, used whenever a relative clause
modifies some *other* NP as a `ModifyRelVP` wrapper -- just never reused
for the case where the metonymy *target itself* is the argument that
implicit-subject verb governs.

**Fixed** (still zero new grammar constructs): refactored `_np`'s
per-UPOS dispatch into a new `_np_base` (pure extraction, behavior-
preserving -- confirmed by the full existing suite passing unchanged),
so it can be reused without `_np`'s own automatic `ModifyRelVP`
re-attachment kicking in a second time. New
`_implicit_subject_relative_clause_np`: when the governing word is
itself `acl:relcl` with no own `nsubj`/`nsubj:pass`, builds its subject
NP from the head noun it modifies via `_np_base` directly (deliberately
*not* through plain `_np`, which would incorrectly try to re-attach the
governing verb itself as a `ModifyRelVP` wrapper around its own
subject). One safety check this needed that a first pass might miss:
the head noun could have a *second*, unrelated relative clause of its
own -- outside the governing verb's own descendant subtree entirely, so
the existing `embedded-leftover-words` check can't catch it -- handled
with a new, explicit `governing-relcl-head-has-other-relative-clause`
reason rather than silently dropping it. A second new reason,
`governing-relcl-head-not-found`, guards the same defensive "should be
structurally impossible, but never guess" case `governing-start-not-
found` already does for the outer lookup.

Tests: 2 new cases in `GoverningStartTests` (the implicit-subject
success case, and the other-relative-clause-on-the-head decline case),
confirmed the full existing suite (including every pre-existing
`_np`/relative-clause test) is byte-for-byte unaffected by the `_np`/
`_np_base` refactor. No new grammar constructors, so no new `gf.exe`
verification needed -- the tree shape produced (`Pred subject_np (Compl
... object_np)`) is the same already-verified shape every other active
clause in this module produces. Full local suite: same pre-existing
baseline, no regressions.

**Next step**: commit, push, wait for `ci.yml`, then re-run
`contextual-tower-evaluation.yml` once more -- watch whether
`subject-count` drops toward zero and whether any real `"stanza"`
successes finally appear in `tree_source_counts`, or whether the
remaining redirected cases (`embedded-leftover-words`,
`common-noun-determiner-or-adjective-count`, `passive-agent-count`,
`pronoun-unrecognized`) turn out to need their own follow-up round.

### Second real run: subject-count unmoved, and the LLM tier's own real bottleneck found

The implicit-subject-relative-clause fix above had **zero** measurable
effect: `decline_reason_counts` came back byte-for-byte identical to the
previous run in both corpora, `subject-count` still exactly 12/150
(WiMCor) and 13/150 (ConMeC). The hypothesis (an `acl:relcl` governing
verb with no own `nsubj`) was reasonable and the fix is presumably
correct for that shape, but it simply isn't what's actually happening in
these 25 real rows -- a real reversal, same class as the PredPatt one
earlier in this document. The far more likely real cause (not yet
confirmed, not yet fixed): coordination with a shared, elided subject
(`governing_word["deprel"] == "conj"`, its own `nsubj` living on the
*first* conjunct verb instead) -- a parallel case to what was just
built for `acl:relcl`, but unexplored, deliberately not guessed at a
third time without sub-bucketing `subject-count` by the governing
word's own deprel first.

The same run's `query-network-or-timeout` collapsed from 76-108 down to
7-9 in both corpora -- with no code change to the LLM tier at all this
round, strong evidence the earlier timeout surge really was CI-runner
variance (a noisy-neighbor/capacity-limited shared GitHub Actions
runner), not something in this project's own code. With the LLM tier
finally running near its real capacity, `tree_source_counts`' `"llm"`
count jumped sharply (WiMCor 7&rarr;27, ConMeC 7&rarr;**63/150** -- 42%
of the whole corpus). But recall still didn't move: `exit4_tree_source_
counts` showed the LLM-built trees themselves now dominating exit4
(ConMeC: `llm`=38 of the corpus's exit4 failures), nearly all of them
`"unsupported GF adjective-noun semantics"` (6&rarr;25&rarr;**38**/150
across three consecutive runs, tracking the LLM tier's own rising
adjective-modified-NP output almost exactly).

Read directly rather than guessed: `data/wordnet-context-rules.json`'s
`adjective_sorts` has only **4** entries total
(`political`/`commercial`/`educational`/`scientific`) against
`lexical_sorts`'s 5148 -- but that's not even the deeper limit.
`compile_gf_constraints`'s `walk` composes an adjective+noun pair
through THREE layers: `adjective_sorts` (a word), `composition_matrix`
(`data/contextual-language-rules.json`, 16 hand-curated `(modifier_sort,
noun_sort) -> result_sort` rules, e.g. `Political×Agreement ->
PoliticalAgreement`), and `action_object_requirements` (a per-action
`Sort -> candidate_requirement` table covering exactly **3 actions**:
`sign`, `announce`, `read`). This whole subsystem reads as a narrow,
hand-built demo feature from early in the project (the original
"Waterloo announces a programme" example) that was never extended
alongside the later VerbNet-based action-vocabulary import (4499 real
lemmas) -- meaning even a much richer `adjective_sorts` would still fail
for almost every real action outside those original 3.

A second, more fundamental finding: `walk` traverses the *entire* tree
unconditionally, and a single unsupported `OpenAdjDefCN`/`OpenAdjIndefCN`
composition **anywhere** in it -- not necessarily anything to do with
the metonymy target itself -- raised and aborted `compile_gf_constraints`
entirely, discarding every other constraint the tree could otherwise
have yielded (including the target's own core action/role constraint,
independently derived by `first_node` with no dependency on this block
at all).

**Fixed**: the whole `OpenAdjDefCN`/`OpenAdjIndefCN` composition
attempt in `walk` is now wrapped in `try/except ValueError: pass` --
any of its five failure points (malformed node, missing
`adjective_sorts`/`lexical_sorts` coverage, ambiguous noun sort, no
`composition_matrix` entry, no `action_object_requirements` entry for
this action) now simply skips deriving that one `FrameComposition`
constraint and continues walking the rest of the tree, instead of
discarding everything. This is optional-enrichment logic (an extra,
narrowing role constraint layered on top of the target's own
independently-derived core constraint) -- skipping it is safe
under-generation (fewer narrowing constraints in that one stage, never
a wrong one), the same principle already applied to the `governing_
start` tree-builder's own "don't represent the wrapper" choice. No data
expansion attempted this round (that's a separate, judgment-heavy task
-- which new adjective/composition/action-role mappings are safe enough
to curate, mirroring the VerbNet `AUDITED_ROLE_SORTS` precedent) --
purely a control-flow fix.

Tests: a new `test_unsupported_adjective_noun_composition_is_skipped_
not_fatal` in `test_qid_fiber.py` confirms directly (no exception, no
`FrameComposition` constraint, but the tree's other, unrelated
`FrameArgument` constraint still comes through). `Exit4TreeSourceTagging
Tests.test_tags_stanza_when_the_stanza_built_tree_was_used` in
`test_run_automatic_contextual_pipeline.py` needed reworking -- it
relied on exactly the old hard-abort behavior to reach exit4 at all;
now uses a *different*, still-hard-failing path unrelated to adjectives
entirely (`_cumulative_origin`'s own "GF lexical token is absent from
source", via a plain "Waterloo announces a programme" tree paired with
a mocked `proposal["sentence"]` that never actually contains the word
"programme") to keep confirming the same `tree_source=stanza` tagging.
Full local suite: same pre-existing baseline, no regressions.

**Next step**: commit, push, wait for `ci.yml`, then re-run
`contextual-tower-evaluation.yml` -- watch whether `"unsupported GF
adjective-noun semantics"` disappears from `literal_prediction_reasons`
entirely (it should -- this exact string can no longer be exit4's
cause) and whether the LLM tier's now-substantial real tree output
(63/150 ConMeC) finally converts into real detections, or whether
recall stays flat because these trees hit some other wall next.

### Sub-bucketing `subject-count` before guessing at it a second time

After the LLM/adjective-composition work above, focus deliberately
shifted back to the deterministic Stanza-UD tree-builder -- it still
sits at zero real successes despite two rounds of fixes, and the second
of those (the `acl:relcl`-implicit-subject fix) had measurably zero
effect on real corpus data. Rather than guess at `subject-count`'s real
cause a third time (the leading hypothesis: coordination with a
shared/elided subject -- `governing_word["deprel"] == "conj"`, its own
`nsubj` living on the *first* conjunct verb instead -- structurally
parallel to the `acl:relcl` case that turned out not to be it), both of
`_clause`'s "no single `nsubj` child" checks now suffix the reason with
the clause-building verb's own UD deprel: `subject-count:root` for the
ordinary root-anchored path (always "root" there, kept only for a
uniform vocabulary), and whatever real relation actually attaches an
embedded governing verb to the rest of the sentence -- `"conj"`,
`"xcomp"`, `"ccomp"`, or anything else -- for the `governing_start`
branch. Purely diagnostic, zero behavior change (still declines exactly
when it did before, only the reason string is more specific) -- the
same closed-vocabulary-deprel-suffix technique already used for
`nested_modifier_deprel` earlier this project's history.

Tests: the existing `test_subject_count` updated to expect
`"subject-count:root"`; a new `test_subject_count_reports_the_governing_
verbs_own_deprel` confirms the coordination case specifically
(`"Napoleon announced Henry and praised Waterloo"`, target=Waterloo,
governing verb="praised", a `conj` sibling of the root sharing its
subject) resolves to `"subject-count:conj"`. Full local suite: same
pre-existing baseline, no regressions.

**Next step**: commit, push, wait for `ci.yml`, then re-run
`contextual-tower-evaluation.yml` -- `decline_reason_counts`'s
`subject-count:<deprel>` breakdown will say, with real data, whether
`conj` actually dominates (confirming the coordination hypothesis and
pointing at a concrete, scoped fix: when the governing verb is `conj`
with no own subject, borrow the first conjunct's own `nsubj`, the same
"borrow the implicit subject from context" pattern already built for
`acl:relcl`, just keyed off a different UD relation) or something else
entirely does -- decisively, not a third guess.

### Real breakdown: subject-count is a heterogeneous mix, conj the largest single share

`"unsupported GF adjective-noun semantics"` disappeared from
`literal_prediction_reasons` entirely in both corpora, confirming the
skip-not-abort fix worked exactly as intended. The `subject-count:
<deprel>` breakdown gave a decisive, real answer instead of a third
guess: **`conj`** (6/150 WiMCor, 4/150 ConMeC -- 10 combined) is the
single largest share, but not an overwhelming majority -- `advcl` (8
combined) and `acl` (4 combined, this module's own already-built
`acl:relcl` shape, confirmed a real but modest slice as its own updated
docstring now says) and `xcomp` (3, ConMeC only) all contribute too.
`subject-count` was never one clean cause; it is several genuinely
different UD shapes bundled under one label.

**Implemented `conj` (the largest share)**: new
`_shared_subject_from_conjunct` -- when the governing verb is itself a
UD `"conj"` with no own `nsubj`/`nsubj:pass`, English coordination
shares the first conjunct's subject with every later one unless a later
conjunct states its own (a real syntactic fact `"conj"` encodes, not a
guess -- the same class of confidence as the already-built `acl:relcl`
case). Walks the `"conj"` chain up past however many hops a 3+-way list
needs ("A, B, and C" -- UD may attach both B and C as `"conj"` of A
directly, or chain C as `"conj"` of B; both resolve the same way) to the
true first conjunct, borrows its own `nsubj` if it has exactly one.
`_implicit_subject_relative_clause_np` and this new function are now
unified behind a single `_implicit_subject_np` dispatcher, tried once
from `_build_gf_tree_inner`'s embedded branch, trying each known shape
in turn.

**A real bug caught by testing the fix against a realistic fixture, not
just the simplest one**: the coordinating conjunction word itself
("and"/"or", UD's own `"cc"` relation, attached to the conjunct it
precedes) sat inside the governing verb's own descendant subtree but
was never added to `accounted` -- so `embedded-leftover-words` fired
even when the shared subject was found correctly, on nearly every real
coordinated sentence (almost all of them spell "and"/"or" out
explicitly; only a two-word toy fixture without it happened to pass by
accident). Fixed by explicitly excluding the governing verb's own `"cc"`
child from the completeness check, the same treatment already given to
`"mark"` for subordinate clauses.

Tests: the earlier `subject-count:conj`-asserting test became a real
success test (`test_shared_subject_from_the_first_conjunct`); a new
`test_conj_without_a_clean_first_conjunct_subject_still_declines`
confirms the still-honest decline path when the first conjunct itself
has no single clean subject to borrow; a new
`test_shared_subject_walks_a_chained_three_way_conjunct` confirms the
multi-hop walk *and* deliberately includes a real `"cc"` word to catch
the exact leftover-words bug above (this test failed against the first
version of the fix, caught before commit). Full local suite: same
pre-existing baseline, no regressions.

Deliberately not attempted this round: `advcl` and `xcomp` (both real,
smaller shares of the same bucket) -- each is a different UD shape
(likely needing its own control/shared-subject reasoning, not
necessarily the same pattern as `conj`) and deserves its own
narrow-slice-then-measure round rather than being guessed at together
with `conj` in one commit.

**Next step**: commit, push, wait for `ci.yml`, then re-run
`contextual-tower-evaluation.yml` -- watch whether `subject-count:conj`
drops to (near) zero, whether any real `"stanza"` tree-source successes
finally appear, and what `advcl`/`xcomp`'s own real shares look like
once `conj` is no longer inflating the total.

## Third real run: still 0% real successes, three more buckets diagnosed and closed in one round

A fresh `decline_reason_counts` breakdown (after conj-coordination) gave
the honest, uncomfortable headline: the Stanza tree-builder is still at
**zero** real `tree_source="stanza"` successes across both corpora,
after five rounds of fixes that each mechanically work but keep
revealing the next barrier in the same sentence. Meanwhile the LLM tier
(discussed with the user directly) gave a first real true positive in
ConMeC and doubled WiMCor's -- but its own timeout volatility and lack
of per-failure diagnosability (we can tell *what shape* a bad LLM answer
took, never *why* the model produced it) made the user choose to keep
pushing the deterministic path, explicitly accepting that progress
there is slower but fully explainable and reproducible.

Three parallel Explore agents characterized the four largest remaining
buckets (`root-not-verb`=36, `root-lemma-mismatch`=34,
`passive-agent-count`=31, plus the `common-noun`/`leftover-words`
family combined &asymp;58), a Plan agent validated concrete designs for
three of them, and every non-obvious claim (grammar `open`/`cat`/`fun`
lists, `resolve_action`'s exact branch order, `propose_contextual_
scenario.py`'s real `wordnet_rules` load order relative to
`resolve_action`) was independently re-verified by reading the actual
current code before writing the plan, not just trusted from agent
output. `object-count` (12, intransitive verbs) was deliberately
deferred -- a deeper architectural question (what a constraint even
means without an object) than a tree-builder gap, and the smallest of
the four.

### 1. nmod PP-modifier on NPs -- zero grammar risk, done first

"the museum **in Kent**" -- a trailing UD `nmod`+`case` modifier on a
noun -- was never checked by `_np`/`_np_base` at all (only
`det`/`amod`/`acl:relcl` were). `grammar/Metonymy.gf`'s `ModifyNP` +
13-preposition family was already compiled and already used (the
fronted-date path), and `contextual_rule_compiler.py`'s own `walk`/
`lexical_head` already traverse any `ModifyNP` node generically
(confirmed directly by the existing `test_of_pp_modifier_does_not_
crash_the_walker` in `test_compile_gf_constraints_batch2.py`, which
needed zero changes to keep proving the point) -- so this feature is
entirely self-contained inside `build_gf_tree_from_dependencies.py`. New
`_NMOD_PP_CONSTRUCTORS` (the same 13-word table, inverted); `_np` now
checks for an `nmod` child alongside its existing `acl:relcl` check,
declining (`nmod-and-relative-clause`) if a noun somehow has both rather
than guessing which one matters, and (`nmod-count`/`nmod-case-count`/
`nmod-preposition-unrecognized`) on anything else unrecognized. Recurses
through `_np` itself (not `_np_base`) so a modifier NP can have its own
nested nmod/relative clause too ("the museum in the county of Kent").
No `gf.exe` verification needed -- no new grammar constructs at all.

### 2. Agentless passive -- the one new grammar construct this round

`passive-agent-count` (31, second-largest bucket): `_clause` required
exactly one "by"-agent for *any* `nsubj:pass`, but most real passives
never name one at all. `PassCompl : V2 -> NP -> VP` had no agentless
alternative. Read directly from the pinned `gf-rgl-src` clone (not
fetched, not guessed): `Verb.gf`/`VerbEng.gf` already declare
`PassV2 : V2 -> VP` ("be loved"), structurally independent of
`PassCompl`'s own `ExtendEng.PassAgentVPSlash`+`SlashV2a` combination --
`VerbEng` was already `open`ed, and a repo-wide grep of the whole pinned
RGL tree found no competing `PassV2` declaration anywhere, unlike
`PassCompl`'s own collision history. New `PassCompl0 : V2 -> VP` in
`grammar/Metonymy.gf`, `PassCompl0 verb = VerbEng.PassV2 verb ;` in
`grammar/MetonymyEng.gf` (qualified anyway, matching this file's
existing defensive discipline). **Verified locally against `gf.exe` +
the pinned `gf-rgl-src` clone before writing a single test**: compiled
with zero new conflicts beyond the pre-existing harmless `CatEng.*`
ones; `l -lang=MetonymyEng (Pred (OpenPN "Henry") (PassCompl0
Announce))` -> "Henry is announced"; the pre-existing agent-present
`(PassCompl Announce (OpenPN "Waterloo")))` re-checked unaffected ->
"Henry is announced by Waterloo"; a round-trip parse of "Henry is
announced" found our new tree as its first (and, expectedly, not only --
GF's parser also offers a `PredCopNP`-based reading treating "announced"
as a bare-string predicate, a pre-existing ambiguity class this addition
didn't create, and one our own tree-builders never rely on `p` to
disambiguate anyway) reading.

`_clause`'s passive branch: `len(agents) > 1` still declines (genuine
ambiguity -- which agent is real?); `len(agents) == 0` now builds
`Pred subject_np (PassCompl0 gf_function)` instead. `ARITIES["PassCompl0"]
= 1`; deliberately *not* added to `first_node`'s `{"Compl", "PassCompl"}`
set (a 1-arg node has no agent to derive a `FrameArgument` enrichment
from anyway, and `len(complement.arguments) == 2` would be `False`
regardless -- confirmed by tracing the exact code, not assumed). A real
existing-test inversion: the old `test_passive_without_a_by_agent_is_
out_of_scope`/`test_a_passive_clause_is_out_of_scope` fixtures now
*succeed* -- rewritten into a success test (exact tree string) and
removed as a now-redundant duplicate, respectively; `test_passive_agent_
count` rebuilt around a genuine 2-agent ambiguity instead.

### 3. Copula -- the largest bucket, and a genuinely separate resolution path

`root-not-verb` (36, the single largest bucket): "Waterloo is a county"
-- UD's own root is the predicate NOUN "county", never VERB/AUX, so
`classify_word`'s existing `GOVERNING_UPOS` check never fires for it at
all; the whole pipeline never reached tree-building for such a target.
`PredCopNP : NP -> NP -> S` already existed in the grammar (confirmed:
it needed no new construct) and was already proven a safe no-op by
`compile_gf_constraints`'s own existing
`test_a_pure_copula_tree_is_a_safe_no_op_not_a_crash`.

**The real scope, found by tracing rather than assuming**: there is no
VerbNet "action" for a copula at all -- `data/predicates.tsv`/
`data/verbnet-action-roles.tsv` contain zero "is-a" entries (grep-
confirmed). So this needed a genuinely separate resolution path inside
`resolve_action`, not just a new tree-builder branch: the predicate
noun's own lemma stands in for "action" (the same role `root-lemma-
mismatch`'s check already generalizes to), and the `HasSort` requirement
comes directly from `wordnet_rules["lexical_sorts"][predicate_lemma]`
-- a different data source than every other branch of `resolve_action`
touches. This also surfaced a real, honest coverage ceiling worth
stating up front rather than discovering after the fact:
`data/wordnet-context-rules.json`'s `lexical_sorts` (5148 entries) does
**not** contain "county"/"museum"/"town"/"city"/"river" (only
"company"/"country" among common examples checked) -- even a fully
correct implementation will correctly, safely decline
(`unsupported-copula-predicate:<lemma>`, tracked in
`literal_prediction_reasons` the same way `unsupported-action-role`
already is) for a real share of "X is a Y" sentences, the same class of
ceiling already documented for `adjective_sorts`'s own 4-word coverage.

New `dep_status == "copula-argument"` in `annotate_dependency_hints.py`'s
`classify_word` (inside the existing `SUBJECT_DEPRELS` branch, scoped to
a `NOUN`-headed subject with exactly one `cop` child -- deliberately not
`ADJ`/`PROPN`: `grammar/Metonymy.gf` has no `AP` category at all,
confirmed by reading its full `cat` list, so an adjectival predicate is
structurally unreachable regardless of Python wiring). `governing_lemma`/
`governing_start`/`governing_end` are repurposed with copula-specific
meaning (predicate noun's lemma; span of the copula word alone, not the
whole predicate NP) -- documented distinctly in the module's own schema
comment. New `resolve_action(..., wordnet_rules=None)` parameter and
`_resolve_copula_predicate` early-exit branch (right after the existing
`"nested-modifier"` check); `propose_contextual_scenario.py`'s
`wordnet_rules` load moved earlier (it previously loaded *after*
`resolve_action`'s own call site -- confirmed by reading the file, not
assumed) and threaded through, with the existing `lexical_evidence`
block downstream reusing the same loaded object instead of loading
twice. New `_copula_clause` in `build_gf_tree_from_dependencies.py`,
dispatched as an alternative to the unconditional `root-not-verb` bail
when the root is `NOUN`-with-`cop`; reuses `_np` (not `_np_base`) for
*both* subject and predicate NPs, so a copula predicate already gets
feature 1's `nmod` support for free ("Waterloo is a county in Iowa"),
verified directly via `gf.exe`: `l -lang=MetonymyEng (PredCopNP (OpenPN
"Waterloo") (ModifyNP (OpenIndefCN "county" "county") (InPP (OpenPN
"Iowa"))))` -> "Waterloo is a county in Iowa". Every downstream consumer
of `resolve_action`'s return dict was traced and confirmed already fully
generic over lemma/role/requirement (not "is this a verb") -- zero
changes needed anywhere else in that chain.

### Tests (all three features)

`NmodModifierTests` (6), `PassiveClauseTests`/`BuildGfTreeDeclineReasonTests`
updates + a new standalone `test_compile_gf_constraints_passcompl0.py`
(3), `ClassifyWordTests` copula cases (3) + a new
`test_resolve_action_copula.py` (5) + `CopulaClauseTests` (5) in
`test_build_gf_tree_from_dependencies.py`, plus one new
`literal_reason` suffix test for `unsupported-copula-predicate`. Full
local suite: same pre-existing baseline (2 failures/13 errors/8
skipped), no regressions, across all three features together.

**Next step**: commit (one commit per feature -- each is independently
testable and revertible, matching this project's own established
discipline), push, wait for `ci.yml` for each, then ask the user to
re-run `contextual-tower-evaluation.yml` -- decisive this time on
whether any of `root-not-verb`/`passive-agent-count`/`leftover-words`'s
`nmod` share actually convert into real `tree_source="stanza"`
successes, or whether (as happened with `conj`) they mechanically work
but reveal yet another compounding barrier in the same real sentences.

## Enumerating every blocker a sentence carries, not just the first

The three-feature batch above (`25305f9`) landed and CI went green, and
the next real corpus run confirmed the mechanism works exactly as
intended, bucket by bucket: `root-not-verb` dropped substantially
(WiMCor 23→8, ConMeC 13→6, the copula path firing for real), a new
`unsupported-copula-predicate:mile` appeared (the copula path reaching
all the way to `lexical_sorts`'s own known coverage ceiling), and
`passive-agent-count` vanished entirely. At the same time several other
buckets *grew*: `root-lemma-mismatch` (WiMCor 20→33, ConMeC 14→21),
`leftover-words`, and `common-noun-determiner-or-adjective-count`. And
`tree_source_counts` still showed **zero** real `"stanza"` successes in
either corpus -- the sixth consecutive round where every individual fix
is independently confirmed correct (unit tests plus, where the grammar
changed, real `gf.exe` verification) yet the corpus-level number does
not move.

The user asked directly how to get a precise list of every blocker a
sentence carries, not a guess. The honest answer: today's code
structurally cannot answer that. `_build_gf_tree_inner` raises `_Bail`
(a plain exception) on the very first check it fails, and every caller
(`build_gf_tree`, `build_gf_tree_decline_reason`) stops there --
`decline_reason_counts` has only ever reported the *first* blocker per
sentence. A bucket growing after a real fix is exactly consistent with
"sentences that used to fail an early, coarse check now pass it and
reach a different, still-unaddressed one further down the same
pipeline" -- the same "compounding blockers" pattern named at the very
start of Phase 1 -- but `decline_reason_counts` alone can only ever
suggest that indirectly, from bucket sizes moving between runs, never
confirm it.

**New diagnostic: `enumerate_gf_tree_blockers`
(`scripts/build_gf_tree_from_dependencies.py`)**, an "ablate and retry"
search built entirely on top of `_build_gf_tree_inner` *unmodified* --
zero risk to the production tree-building path, since none of its own
code changed. On each `_Bail`, it applies one of a small set of
deliberately narrow "ablations" -- each one either deletes an
already-unbuildable subtree (an unrecognized preposition's `nmod`, an
extra determiner/adjective/agent/object/subject beyond the first) or
coerces one already-wrong field (an unrecognized pronoun/determiner
lemma, or injects a placeholder lexicon entry for a missing verb) -- and
retries the *exact same* `_build_gf_tree_inner` to see what the next
independent blocker is. It never invents new syntactic structure, and
the ablated tree is never linearized, never reaches
`compile_gf_constraints`, and never influences any real prediction --
only the ordered list of reason codes it collects is ever returned.
Roughly half the closed reason-code vocabulary has a known ablation
(every "N != 1" multiplicity check, plus the two unrecognized-vocabulary
checks and the two lexicon-gap checks); the rest (`root-count`,
`root-not-verb`, `leftover-words`/`embedded-leftover-words`, the
`governing-*` family, `root-lemma-mismatch`, and a handful of others)
stay honestly terminal in this round -- a real, not-yet-diagnosable-
further limitation, not a guess past it. `leftover-words` in particular
has no *single* structural cause (it is a catch-all "something wasn't
accounted for"), so distinguishing its own sub-causes is left for a
later round, informed by what this one measures.

Wired in exactly like `tree_source`/`decline_reason` already are:
`run_automatic_contextual_pipeline.py` computes `all_decline_reasons`
unconditionally alongside `decline_reason` (defensively wrapped -- any
unexpected exception degrades to `["enumeration-error"]` rather than
taking down a row that would otherwise have succeeded or failed for an
unrelated reason), threads it into every exit3/4/7 JSON payload and a
new unconditional `all-decline-reasons=` stdout line;
`run_contextual_corpus.py`'s line-scan picks it up (comma-joined, since
the closed reason-code vocabulary never contains a comma);
`score_contextual_detection.py`'s new `row_all_decline_reasons` mirrors
`row_decline_reason` exactly, aggregated into two new report fields:
`blockers_per_sentence_histogram` (how many sentences carry 0/1/2/3+
independent blockers at once -- the direct, measured answer to the
compounding-blockers question, not an inference from bucket sizes) and
`co_occurring_blocker_pairs` (which pairs of reason codes co-occur most
often in the same sentence -- points at which *two* fixes together
would actually free a sentence, rather than shifting it one blocker
forward, the exact failure mode this round's own data kept showing).

**A real finding surfaced immediately while writing the test suite**:
the existing two-"by"-agent passive fixture
(`test_falls_back_to_engine_parse_when_build_gf_tree_declines`,
`"Henry was announced by Waterloo and by Napoleon"`) enumerates to
`["passive-agent-count", "leftover-words"]`, not just the one blocker --
once the extra agent is ablated away, the sentence's own "and" (`cc`)
word is left unaccounted for (the passive branch only ever consumes the
subject/aux/verb/single agent, never a coordinating conjunction between
two agents), a second, genuinely different blocker the single-reason
view could never have shown.

Tests: `EnumerateAllBlockersTests` (11, `test_build_gf_tree_from_dependencies.py`)
covering the zero/one/terminal/two-compounding-blockers cases plus one
direct test per ablation; new stdout-line/JSON-field assertions in
`test_run_automatic_contextual_pipeline.py` and
`test_run_contextual_corpus.py`; `RowAllDeclineReasonsTests` (7) plus a
new `ScoreTests` case for both aggregate fields in
`test_score_contextual_detection.py`. Full local suite: same pre-
existing baseline (2 failures/13 errors/8 skipped), no regressions. No
grammar changed this round, so no `gf.exe` verification was needed.

**Next step**: commit, push, wait for `ci.yml`, then ask the user to
re-run `contextual-tower-evaluation.yml` -- `blockers_per_sentence_
histogram` gives the first *measured* (not inferred) answer to how many
real sentences carry 2+ simultaneous blockers, and
`co_occurring_blocker_pairs` should point at the next pair of fixes
worth doing together.

## The real corpus run: still 0% Stanza successes, and root-lemma-mismatch confirmed dominant

The first real run of `enumerate_gf_tree_blockers` (after fixing an
unrelated, real CI infra bug it surfaced along the way -- a transient
504 from `ollama.com`'s install endpoint was silently short-circuiting
the whole job before it ever reached the Stanza-tier data at all; see
that commit for the fix) gave decisive numbers, not another guess:

- **`tree_source_counts` still shows zero real `"stanza"` successes in
  either corpus** -- the eighth consecutive round where every
  individual fix is independently verified correct, yet the corpus-
  level number does not move.
- **`blockers_per_sentence_histogram` confirmed real compounding, but at
  a smaller scale than expected, for an explainable reason**: WiMCor
  `{0: 59, 1: 89, 2: 2}`, ConMeC `{0: 28, 1: 106, 2: 15, 3: 1}`. Every
  "0" row is a `not-applicable` row (no `ud_words` at all), confirmed by
  `decline_reason_counts`/`tree_source_counts` reporting the exact same
  count -- there is *no* genuine zero-blocker success hiding in that
  bucket. The reason ConMeC shows far more real compounding (16/122,
  ~13%) than WiMCor (2/91, ~2%) is that WiMCor's declines are dominated
  by reasons this round's ablation set treats as terminal
  (`root-lemma-mismatch`, `leftover-words`, `root-not-verb` alone cover
  57/91) -- `enumerate_gf_tree_blockers` correctly stops at 1 for those,
  since it has no safe way to see past them yet. Real compounding behind
  those terminal reasons may well be larger still; it is simply not
  visible with today's ablation coverage.
- **`root-lemma-mismatch` is now unambiguously the single largest
  terminal blocker in both corpora** (WiMCor 33/91 ≈ 36%, ConMeC
  21/122 ≈ 17%), and has grown every round it has been measured
  (20→33, 14→21).
- ConMeC's `co_occurring_blocker_pairs` gave real, actionable pairs for
  a future round: `common-noun-determiner-or-adjective-count +
  pronoun-unrecognized` (4) and `common-noun-unrecognized-determiner +
  leftover-words` (4) stand out -- an unusual pronoun (outside the
  4-word `he`/`she`/`it`/`they` closed set) or determiner often
  co-occurs with a separate NP-building problem in the same sentence.

The user asked directly to break `root-lemma-mismatch` down further
before guessing at a fix. Reading `_build_gf_tree_inner` closely found a
third, previously-unnamed case hiding inside the single reason code:
`_main_clause`'s own lemma check (`root["lemma"] != lemma`) fires in
three structurally distinct situations, only two of which had ever been
named:

1. `governing_start` is `None` entirely -- `resolve_action` fell back to
   its own positional heuristic, with no UD grounding at all (the
   original, already-understood cause).
2. `governing_start` resolves to a *different* word than the sentence's
   own root -- already reported separately, as `governing-lemma-
   mismatch`, by the `governing_start` branch itself.
3. **`governing_start` resolves successfully, and to this very root --
   yet the lemmas still disagree.** This case was silently folded into
   the same `root-lemma-mismatch` bucket as case 1, even though it means
   something completely different: real UD grounding *was* available
   and *did* point at the sentence's own root, so the mismatch must come
   from somewhere else entirely -- a genuine Stanza/`resolve_action`
   lemmatization discrepancy (irregular verb forms, tokenizer
   differences), or an MWT (multi-word token) edge case, not a "wrong
   clause" problem at all.

Fixed by threading `governing_start` into `_main_clause` (and
`_copula_clause`, which has its own separate but structurally similar
check -- though its own branch dispatches *before* the governing_start
resolution code ever runs, so it can only report "a hint was present at
all" and not the stronger "resolves to this same root") and suffixing
the reason: `root-lemma-mismatch:no-governing-start` for case 1,
`root-lemma-mismatch:governing-start-is-root` for case 3,
`root-lemma-mismatch:governing-start-present` for the copula path's own
weaker version of case 3. Purely diagnostic -- no behavior change, only
which string a `_Bail` carries. New tests directly exercise both
suffixes on both call paths, matching this project's established
sub-bucketing pattern (the same technique already used for
`subject-count:<deprel>`). Full local suite: same pre-existing baseline
(2 failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user to
re-run `contextual-tower-evaluation.yml` once more -- the real split
between `no-governing-start` and `governing-start-is-root` (and the
copula path's own `governing-start-present`) will say whether
`root-lemma-mismatch` is mostly a `resolve_action` dependency-hint
coverage gap (cause 1, meaning the real fix is upstream of this module
entirely) or mostly a genuine tree-builder/lemmatization discrepancy
(cause 3, meaning the fix belongs here).

## The split confirms cause 1: sub-bucketing `no-governing-verb` itself

The real numbers were decisive, cleanly resolving the question the
previous round asked: **`root-lemma-mismatch:no-governing-start`
dominates overwhelmingly** (WiMCor 30/33 ≈ 91%, ConMeC 17/21 ≈ 81% of
all `root-lemma-mismatch` rows) over `governing-start-is-root`/
`governing-start-present` (a handful of rows total in each corpus). So
`root-lemma-mismatch` is, in the overwhelming majority of real cases,
**not a tree-builder problem at all** -- it is
`annotate_dependency_hints.py` never computing a `governing_start` in
the first place, forcing `resolve_action` back onto its own unreliable
positional heuristic. (The same real run also confirmed the whole
`enumerate_gf_tree_blockers` mechanism from the previous round is
stable and inert on its own: `blockers_per_sentence_histogram`/
`co_occurring_blocker_pairs` came back byte-identical to the prior run
in both corpora, exactly as expected -- this round changed no tree-
building behavior, only reason-code labels. `tree_source_counts` still
shows zero real `"stanza"` successes in either corpus -- the ninth
consecutive round. F1 moved (WiMCor 0.048→0.093, ConMeC null→0.045),
but `llm_decline_reason_counts`'s own `query-network-or-timeout` count
dropping sharply in this run -- the same CI-runner variance already
documented for the LLM tier, unrelated to anything in this round.)

That single `"no-governing-verb"` status was itself undifferentiated --
`classify_word`'s own final catch-all, reached whenever the target's UD
deprel isn't one of the handful explicitly checked (`nsubj`/`csubj`/
`nsubj:pass`/`csubj:pass`/`obj`/`iobj`/`obl`/the `NESTED_MODIFIER_DEPRELS`
family), *or* when the deprel is a good clause-argument relation but the
UD head itself isn't a usable governor (wrong UPOS, or no `case` word for
an oblique). Rather than guess which of these dominates before extending
`classify_word`'s coverage, the same real question this whole session
keeps returning to -- sub-bucketed it first: `_no_governing_verb`'s new
suffix vocabulary distinguishes `:head-upos-<UPOS>` (target had a good
deprel, bad head type), `:no-head` (dangling head reference), `:no-case-
word` (a verbal-headed oblique with no preposition attached at all), and
`:target-deprel-<deprel>` (the target's own deprel wasn't checked at
all -- e.g. `"conj"`, `"xcomp"`, `"ccomp"`, `"advcl"`, `"parataxis"`) --
the same technique already used for `nested_modifier_deprel`/
`subject-count:<deprel>`/`root-lemma-mismatch:<suffix>`. Confirmed safe
to change: `resolve_action` (`scripts/contextual_rule_compiler.py`) only
ever checks `dep_status` against the exact strings `"direct-argument"`/
`"copula-argument"`/`"nested-modifier"`; nothing anywhere in the repo
checks for the bare string `"no-governing-verb"`, so suffixing it changes
no real control flow, only which label a row carries.

Tests: 3 existing `ClassifyWordTests` updated for the new suffix, 2 new
ones covering the previously-untested `:no-head`/`:no-case-word`
sub-cases directly. Full local suite: same pre-existing baseline (2
failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user to
re-run `contextual-tower-evaluation.yml` once more -- the real split
across `no-governing-verb`'s four sub-reasons will say which UD shape
(a specific deprel like `"conj"`/`"xcomp"`, or a specific bad-head
pattern) actually dominates the positional-fallback cases, pointing at
exactly which branch of `classify_word` is worth extending next.

## A real gap found before the data could even be re-measured: `dep_status` was never surfaced anywhere

The user reported the next `contextual-tower-evaluation.yml` run's
numbers came back byte-identical to the previous one. Checked directly
rather than assumed: the run's own `head_sha` (via the GitHub API)
showed it had actually run against the *previous* commit (the
`root-lemma-mismatch` sub-bucketing one), not the `no-governing-verb`
one -- a stale/duplicate dispatch, not a real null result.

But re-reading the wiring found a second, more important problem that
would have made even a fresh run uninformative: the new
`no-governing-verb:<reason>` suffix lives entirely inside
`annotate_dependency_hints.py`'s own `dep_status` field, and
`run_automatic_contextual_pipeline.py` never reads `dep_status` off
`dependency_hint_data` *at all* -- it only ever reads `ud_words` and
`governing_start` from it. `resolve_action` consumes `dep_status`
internally (`scripts/contextual_rule_compiler.py`), but nothing
downstream of that ever reports which value it saw. The previous
round's suffixing work was real and correct, but invisible to every
report this project produces -- exactly the kind of "changed the code,
forgot the wiring" gap the *measure* half of "measure before fixing"
exists to catch, before spending another CI round on a guess.

Fixed by threading `dep_status` through the exact same path
`tree_source`/`decline_reason`/`all_decline_reasons` already use:
`run_automatic_contextual_pipeline.py` reads it once
(`(dependency_hint_data or {}).get("dep_status") or "no-hint"` --
`"no-hint"` is a genuinely distinct case from any status
`classify_word` itself produces, when `--dependency-hint` wasn't passed
at all), includes it in every exit3/4/7 JSON payload, and prints an
unconditional `dep-status=` stdout line on every other outcome;
`run_contextual_corpus.py`'s line-scan picks it up;
`score_contextual_detection.py`'s new `row_dep_status` mirrors
`row_llm_decline_reason` exactly, aggregated into a new
`dep_status_counts` report field.

Tests: `RowDepStatusTests` (6, mirroring `RowLlmDeclineReasonTests`), a
new `ScoreTests` case for `dep_status_counts`, new line-scan tests in
`test_run_contextual_corpus.py`, and new `dep-status=` assertions
threaded into three existing `test_run_automatic_contextual_pipeline.py`
tests (including one exercising the `"no-hint"` default directly, via
`SourceDisambiguationTests`'s own argv, which never passes
`--dependency-hint`). Full local suite: same pre-existing baseline (2
failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user to
re-run `contextual-tower-evaluation.yml` once more, on this actually-
current commit -- `dep_status_counts` will, for the first time, show
the real split behind `root-lemma-mismatch:no-governing-start`.

## `dep_status_counts` finally answers the question, and finds a real (not just missing-coverage) bug along the way

The real (this time genuinely current) run gave a decisive breakdown.
WiMCor's `no-governing-verb` (38 rows) is dominated by one shape:
**`target-deprel-conj` alone is 27/38 (≈71%)** -- the target itself is
a second-or-later conjunct in a coordination ("Napoleon and **Waterloo**
announced...", target's own UD deprel is `"conj"`, not `"nsubj"`/`"obj"`
directly). `classify_word` has no notion of this at all today -- it is
a structurally different question from the tree-builder's own
`_shared_subject_from_conjunct` (which handles a *governing verb* being
coordinated, not the *target* itself). ConMeC's own split is far more
even (`xcomp`/`ccomp`/`advcl`/`parataxis`/`obl:*`/`root`, 1-3 rows
each) -- no single dominant shape there.

A second, smaller finding turned out to be a real bug, not just missing
coverage: `target-deprel-nmod:unmarked` (5, WiMCor) and
`target-deprel-nmod:desc`/`target-deprel-obl:agent`/`target-deprel-obl:unmarked`
(3+2+3, ConMeC) are all UD colon-subtyped variants of relations
`classify_word` already handles -- `NESTED_MODIFIER_DEPRELS`/
`OBLIQUE_DEPRELS` matched by *exact* set membership, so a subtype like
`"nmod:unmarked"` (structurally identical to bare `"nmod"` for this
module's purposes) fell through to the undifferentiated catch-all
instead of the safe, already-correct `"nested-modifier"`/oblique path.
That is strictly worse than a coverage gap: it meant `resolve_action`
fell back to its unreliable positional heuristic on rows that already
had a perfectly good, honest answer available.

Fixed narrowly, exactly matching what the data showed (not
generalized to every deprel family): `word.deprel.startswith("obl:")`
and `word.deprel.startswith("nmod:")` are now checked alongside the
existing exact-set membership, in both the `OBLIQUE_DEPRELS` and
`NESTED_MODIFIER_DEPRELS` branches respectively. Deliberately does
*not* touch `amod`/`appos`/`compound`/`acl`/`nummod` (no subtype misses
observed for those in real data) or `nsubj`/`obj`/`csubj` (already have
their own explicit passive-subtype family, `PASSIVE_SUBJECT_DEPRELS`,
which broadening `SUBJECT_DEPRELS` by prefix would have silently
bypassed). The underlying resolution logic inside each branch (case-word
lookup, `_is_passive` detection) already worked correctly for any
subtype -- only the *entry* check needed broadening.

Tests: 2 new `ClassifyWordTests` (`nmod:unmarked` routing to
`"nested-modifier"`; `obl:agent` still correctly reconstructing a
passive by-agent, confirming the subtype broadening doesn't disturb the
existing `_is_passive` logic). Full local suite: same pre-existing
baseline (2 failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user to
re-run `contextual-tower-evaluation.yml` -- expect the `nmod:*`/`obl:*`
slice of `no-governing-verb` to disappear from `dep_status_counts`
(reclassified as `"nested-modifier"` or correctly resolved as
`"direct-argument"`), and `target-deprel-conj`'s own share to become
even more clearly the dominant remaining cause in WiMCor. The larger,
separate question -- whether to build real `"conj"`-coordination
handling into `classify_word` -- is a bigger design decision left for
its own round, per the user's own explicit choice to do the narrow, safe
fix first.

## Confirmed, then closed: `target-deprel-conj`

The (this time verified-current, via the run's own `head_sha`) real run
confirmed the subtype fix cleanly: WiMCor's `no-governing-verb:target-
deprel-nmod:unmarked` (5) moved to `literal_prediction_reasons`'s
`nested-modifier-unsupported:nmod:unmarked` exactly; ConMeC's `nmod:desc`
did the same, and `obl:agent`/`obl:unmarked` correctly resolved into the
oblique branch -- some straight to a precise `no-governing-verb:no-case-
word` (they have no preposition word at all), confirming the fix works
exactly as designed rather than just moving the label around. Both
corpora still showed zero real `"stanza"` tree_source successes.
`target-deprel-conj` held steady at 27 (WiMCor)/2 (ConMeC) -- a
deterministic property of the UD parse, not sampling noise -- now ~82%
of WiMCor's remaining `no-governing-verb`.

Implemented directly on the user's "давай": a target whose own UD
deprel is `"conj"` is a coordinated conjunct ("Napoleon and **Waterloo**
announced a treaty") -- UD's own coordination semantics mean it shares
its first conjunct's syntactic role, so `classify_word` now walks the
`"conj"` chain to the true first conjunct (new `_first_conjunct`,
mirroring `build_gf_tree_from_dependencies.py`'s own
`_shared_subject_from_conjunct` -- for "A, B, and C", UD may attach
every later conjunct directly to A, or chain them one to the next;
either shape resolves to A) and recurses `classify_word` on it,
propagating *whatever* that word's own classification turns out to be
(`direct-argument`, `nested-modifier`, even another `no-governing-verb`
case) rather than only handling the clause-argument case. Recursion
terminates by construction (`_first_conjunct`'s own loop only stops on
a non-`"conj"` deprel, so the recursive call can never re-enter this
branch). A dangling `"conj"` chain (malformed UD graph, not expected in
practice) degrades to a new, distinct `no-governing-verb:conj-chain-
broken` rather than crashing.

Tests: 4 new `ClassifyWordTests` -- a coordinated subject, a chained
three-way coordinated object (exercising the multi-hop walk), a
coordinated *nested modifier* (confirming the recursion propagates a
non-direct-argument classification correctly, not just the common
case), and the defensive broken-chain case. Full local suite: same
pre-existing baseline (2 failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user to
re-run `contextual-tower-evaluation.yml` -- expect WiMCor's own
`no-governing-verb:target-deprel-conj` (27) to convert substantially
into real `direct-argument` rows, which should (for the first time in
many rounds) move `root-lemma-mismatch:no-governing-start` and, more
importantly, finally test whether any of these newly-`direct-argument`
rows produce a real `tree_source="stanza"` success.

## The `conj` fix confirmed, and the bottleneck moves inside the tree-builder itself

The real run confirmed the `conj`-coordination fix cleanly:
`no-governing-verb:target-deprel-conj` is gone from `dep_status_counts`
in both corpora, `root-lemma-mismatch:no-governing-start` collapsed
further (WiMCor 30→7, ConMeC 17→12 across the whole chain of
`annotate_dependency_hints.py` fixes), and WiMCor's own
`nested-modifier-unsupported:nmod` grew (45→61) -- a real, correct side
effect: some `conj`-coordinated targets turned out to be coordinated
*nested modifiers*, not clause arguments, and now honestly decline via
the already-safe path instead of risking a wrong positional guess.

But `tree_source_counts` still showed **zero** real `"stanza"`
successes in either corpus, and `blockers_per_sentence_histogram`'s own
"0" bucket was found to exactly equal `not-applicable` in both -- not
one sentence that actually reaches `build_gf_tree_from_dependencies.py`
builds cleanly. The bottleneck had fully moved from
`annotate_dependency_hints.py` (now well-diagnosed and substantially
fixed) into the tree-builder's own `decline_reason_counts`: `leftover-
words` (16/27), `common-noun-determiner-or-adjective-count` (11/24),
`object-count` (5/7), `root-not-verb` (6/6) -- all still single,
undifferentiated reason codes.

Per the user's request to "globally" work through the remaining
blockers rather than one CI round per bucket, this round applied the
exact same proven technique (suffix with closed-vocabulary UD
information -- deprel/UPOS/lemma -- before guessing a fix) to every one
of those buckets at once, all purely diagnostic (no change to which
sentences succeed or decline, only to the string naming why):

- `common-noun-determiner-or-adjective-count` split into
  `:zero-determiners` / `:multiple-determiners` / `:multiple-adjectives`
  (previously one undifferentiated code covering three structurally
  different causes).
- `common-noun-unrecognized-determiner` now carries the determiner's
  own lemma (`:every`, `:this`, ...) -- a small closed vocabulary of
  English function words, the same safety class as `governing_lemma`
  elsewhere.
- `np-unsupported-upos` now carries the head word's own UPOS
  (`:NUM`, `:ADJ`, ...).
- `object-count` split into `:zero` / `:multiple`.
- `root-not-verb` now carries the root word's own UPOS.
- `leftover-words`/`embedded-leftover-words` -- the largest, most
  opaque bucket, previously deferred as needing a deeper refactor to
  expose `_build_gf_tree_inner`'s internal `accounted` set -- turned
  out to need no such refactor: each of the three raise sites already
  computes its own local `leftover` set right before bailing. New
  `_leftover_reason(words, leftover, prefix)` picks the UD deprel of
  the *earliest-starting* leftover word (the same "first blocker"
  principle used everywhere else in this module, not a full audit) and
  suffixes with it.

Confirmed safe without touching `enumerate_gf_tree_blockers` at all:
its own `_GROUP_ABLATIONS` dispatch already keys off `bail.reason.
split(":", 1)[0]` (the prefix only), so every one of these newly-
suffixed reasons still routes to exactly the same ablation (or stays
correctly terminal) as before -- confirmed by re-running the full
`EnumerateAllBlockersTests` suite unmodified in logic, only in expected
literal reason strings.

Tests: ~10 existing `test_build_gf_tree_from_dependencies.py` assertions
updated to the new suffixed values (each traced by hand against its
own fixture, not guessed). Full local suite: same pre-existing baseline
(2 failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user for
one more real `contextual-tower-evaluation.yml` run -- this one round
should reveal, simultaneously, which UPOS actually dominates
`root-not-verb`/`np-unsupported-upos`, the real 0-vs-2+ split for
`object-count`/`common-noun-determiner-or-adjective-count`, and --
decisively -- which UD deprel actually dominates `leftover-words`/
`embedded-leftover-words`, the single largest bucket that has stayed
completely opaque since the very start of this diagnostic effort.

## `leftover-words` finally decoded, and a strategic pivot

The real, sub-bucketed run gave decisive numbers. **`common-noun-
determiner-or-adjective-count:zero-determiners` is now unambiguously
the single largest decline_reason** (11/11 WiMCor, 23/24 ConMeC of that
whole bucket) -- a bare common noun with no article at all ("programmes",
"counties"), which `_np_from_common_noun` has never supported (it
requires exactly one determiner). **`leftover-words`/`embedded-
leftover-words` turned out to be dominated by `case`** (9+3=12 WiMCor,
10+3=13 ConMeC) -- confirmed to be the module's own already-documented,
deliberate limitation (a verb-level oblique PP, "announces X **in
Y**", has no VP-level attachment point in the grammar; attaching it to
the object anyway would silently reinterpret which constituent it
modifies -- see this module's own docstring), not a new bug. The rest
(`aux`, `cc`, `flat`, `mark`, `compound:prt`, `discourse`, `vocative`)
are each 1-3 occurrences -- a long tail, not a second dominant cause.
`tree_source_counts` still showed zero real `"stanza"` successes in
either corpus.

The user asked, stepping back, whether continuing to chase individual
`build_gf_tree_from_dependencies.py` buckets was still the right use of
effort for the paper's actual goal (formally verifying the contextual
tower against real corpus data), or whether a different verification
strategy made more sense. Talking it through surfaced a fact this
session's Stanza-tier focus had obscured: **`tree_source_counts` had
been showing real, substantial success the whole time -- just not via
Stanza.** The legacy tier (`engine parse` on raw text, using GF's own
native PMCFG parser against `grammar/MetonymyEng.gf`'s hand-written
concrete syntax -- an entirely different mechanism from the UD-based
tree-builder, sharing only the same output abstract syntax) already
produces a real tree for 60/150 WiMCor and 113/150 ConMeC rows today,
plus a further 8/150 and 3/150 via the LLM tier -- 68/150 (45%) and
116/150 (77%) of each corpus already reaches the contextual tower with
a genuine tree, fully automatically, regardless of how much (or little)
the Stanza tier itself contributes.

This matters because the tower's own machinery -- constraint
derivation, the layered `ContextConstraint` filtering, Agda-checked
`runtimeCheck` at each stage, context/candidate expansion -- is
**architecturally provably agnostic to tree provenance**: every one of
these steps consumes only `trees[0]`'s text and the constraints derived
from it, with no branch anywhere on which of the three untrusted
proposers produced it (confirmed by re-reading `run_automatic_
contextual_pipeline.py`'s own call sites). So the paper's core formal
claim -- "the tower correctly separates metonymic from literal readings
on real corpus data" -- does not require the automatic *frontend* to
reach 100% coverage; it only requires measuring the tower's own
precision/recall restricted to the subset of real sentences that
already get a tree by any means, decoupling that from the separate,
harder, honestly-still-limited question of open-domain frontend
coverage.

**New report field**: `score_contextual_detection.py`'s `score()` now
computes a second confusion matrix restricted to rows where
`row_tree_source(...)` is `"stanza"`/`"llm"`/`"gf-parser"` (a real tree
actually reached `compile_gf_constraints`, whatever its source) --
`tree_available_instances`/`tree_available_confusion`/
`tree_available_precision`/`tree_available_recall`/`tree_available_f1`,
alongside the existing (whole-corpus, frontend-limited) `precision`/
`recall`/`f1`. New `_precision_recall_f1` helper factors out the shared
computation (used for both matrices, no behavior change to the existing
top-level metric). No corpus text is newly exposed anywhere --
`tower-inference.jsonl` (the only place raw failure text and lexicalized
trees ever appear) is still never uploaded as a CI artifact, per the
workflow's own existing privacy policy; this is purely a new aggregate
number computed and reported the same way every other Counter in this
function already is.

Tests: new `ScoreTests.test_tree_available_metric_is_restricted_to_
rows_with_a_built_tree`, confirming a true positive with no tree
(`tree_source="not-applicable"`) does not inflate the restricted metric
while an identical true positive with a real tree does. Full local
suite: same pre-existing baseline (2 failures/13 errors/8 skipped), no
regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user for
one more real `contextual-tower-evaluation.yml` run -- `tree_available_
precision`/`recall`/`f1` will, for the first time, give a real number
for "how well does the formally-verified tower itself detect metonymy
on real corpus sentences that actually reach it", independent of the
still-limited automatic frontend coverage. If that subset turns out
too small or skewed (e.g. almost entirely literal, or dominated by one
bridge family) to be a convincing publication result on its own, the
next step would be a small, targeted manual/semi-automatic supplement
(using `enumerate_gf_tree_blockers`'s own diagnostics as a triage aid,
verified against local `gf.exe`) -- not a full from-scratch annotation
of ~100 sentences, since the large majority already has a real,
automatically-built tree today.

## A real bug in `tree_available`, found before trusting its first number

The real run's own `tree_available_instances` (68/150 WiMCor,
116/150 ConMeC) turned out to be inflated, caught by re-reading
`run_automatic_contextual_pipeline.py` before drawing any conclusion
from the numbers rather than after. `tree_source` is computed **once**,
right before the pipeline decides whether to even attempt the legacy
`engine parse` fallback -- so it is unconditionally `"gf-parser"` for
exit 3 (`gf-parse-failed`, GF's own parser errored) and exit 7
(`gf-parse-empty`, GF's own parser found zero trees) too, even though
the entire reason those two exit codes exist is that **no tree was
produced at all**. `row_tree_source` alone cannot tell "gf-parser
really built a tree" apart from "gf-parser was about to be tried and
immediately failed" -- and the previous round's `tree_available` filter
relied on `row_tree_source` alone, so it silently counted every exit-7
row (44/150 WiMCor, a huge share) as if a real tree existed. (Reaching
exit 3/7 requires both the Stanza and LLM tiers to have already
declined, which is exactly why `tree_source` is always `"gf-parser"` --
never `"stanza"`/`"llm"` -- for both; neither of those two sources' own
counts was affected.)

Fixed with a new `row_tree_really_built(inference_row) -> bool`
(`scripts/evaluation/score_contextual_detection.py`), which additionally
excludes exit codes 3 and 7 (`_EXIT_CODES_WITHOUT_A_REAL_TREE = {1, 2,
3, 7}`) before trusting `row_tree_source`'s value -- `score()`'s own
`tree_available` gating now calls this instead of checking
`row_tree_source(...) in _TREE_BUILT_SOURCES` directly. Tests: a new
`RowTreeReallyBuiltTests` class (6 cases, including the two that
actually caught the bug -- exit 3/7 with an explicit `"gf-parser"`
`tree_source` label must both read `False`) plus a correction to the
existing `tree_available` integration test's own fixture (it had used
`failed_row`'s default `exit_code=3` for what was meant to simulate a
real, tree-available failure -- an easy mistake to make now that exit 3
specifically carries this meaning, exactly the kind of thing this fix
exists to catch). Full local suite: same pre-existing baseline (2
failures/13 errors/8 skipped), no regressions.

The previous round's real numbers should not be trusted as-is; the
genuine `tree_available_instances` (and the precision/recall built on
it) can only come from a fresh run against this fix.

**Next step**: commit, push, wait for `ci.yml`, then ask the user for
one more real `contextual-tower-evaluation.yml` run -- this time
`tree_available_instances`/`tree_available_precision`/`tree_available_
recall`/`tree_available_f1` will reflect only rows where a tree
genuinely reached the tower, giving the real number the paper's formal-
verification claim needs.

## Diagnosing `ok:empty-fiber`: which layer actually kills real, tree-available sentences

With the two true/false-positive counts (guaranteed unaffected by the
`tree_available` bug, since a positive prediction structurally requires
a real tree and a non-empty final fiber either way) already in hand from
the last real run, the picture was: WiMCor 1 correct / 3 wrong among
rows where the tower reached a positive verdict at all; ConMeC 0 correct
/ 2 wrong. Small samples, but `ok:empty-fiber` (`literal_reason`'s own
bucket for "a real tree built, the tower ran to completion, but the
final fiber came back empty") had shown up as large as 56/150 in one
ConMeC round -- by far the single biggest source of false negatives
among tree-available rows, with zero diagnosis of *why* until now.

**New `empty_fiber_reason(inference_row)`**
(`scripts/evaluation/score_contextual_detection.py`): for an
`ok:empty-fiber` row, names the *first* stage (in narrowing order)
whose own `"survivors"` list is already empty -- once a stage's
survivors reach zero every later stage can only narrow further, so the
first empty one is exactly the elimination point, the same "first
blocker" principle this whole diagnostic effort has used throughout.
`"no-constraints-derived"` for the (structurally earlier, different)
case where the row has zero stages at all -- the tree produced no
derivable constraints whatsoever, not that some specific constraint
filtered everyone out.

Confirmed safe to aggregate by reading the engine's own rendering
directly, not assumed: `engine/app/Main.hs`'s `renderConstraint` prints
`show(ConstraintPayload) <> "@" <> anchorLemma(...)` -- never the full
`LexicalAnchor` record (`engine/src/Metonymy/Contextual.hs`), which
*does* carry the sentence's own `anchorSurface`/`anchorStart`/
`anchorEnd` but is deliberately never shown as a whole, only its own
`anchorLemma` field extracted explicitly. `ConstraintPayload`
(`Requires`/`RequiresRelation`/`RequiresSome`/`Prefers`/
`PrefersRelation`/`PrefersSome`) only ever wraps a `Requirement`
(composed of `Sort`, a 46-member closed enum), a `Relation` (a
19-member closed enum), or an `EntityId` (a public, stable Wikidata
QID, already printed throughout this project's own
`survivors=`/`obstruction=` lines) -- confirmed by reading
`engine/src/Metonymy/Types.hs` directly. No Haskell changes were needed
at all: the engine already prints this safely on every stage line;
`run_contextual_corpus.py`'s existing line-scan already captures it
onto each row's own `stages[i]["constraint"]`.

New report field: `empty_fiber_reason_counts`, aggregated the same way
as every other Counter in `score()`. Tests: `EmptyFiberReasonTests` (4
cases, including the two structurally distinct "no stages at all" vs
"a specific stage's own constraint" causes) plus one new `ScoreTests`
integration case. Full local suite: same pre-existing baseline (2
failures/13 errors/8 skipped), no regressions.

**Next step**: commit, push, wait for `ci.yml`, then ask the user for
one more real `contextual-tower-evaluation.yml` run (the same one that
will also give the corrected `tree_available_*` numbers) --
`empty_fiber_reason_counts` should finally reveal whether one dominant
`Requirement`/`Sort` (a knowledge-base coverage gap) or one dominant
`Relation` (an entity-linking/bridging gap) accounts for most of the
`ok:empty-fiber` false negatives, or whether it is a long, spread-out
tail -- either way, the first real, measured answer to "why does the
tower say literal even when it got a real tree to work with".

## `empty_fiber_reason_counts`'s real answer: 100% "graph-related", and a concrete, testable hypothesis

The real (corrected) run gave a decisive, surprising answer:
**`empty_fiber_reason_counts` was `{"graph-related": 17}` for WiMCor and
`{"graph-related": 41}` for ConMeC -- 100% in both corpora.** Not one
single `ok:empty-fiber` row was eliminated by a lexical/semantic
`Requirement` (a `HasSort` check derived from the sentence's own words)
-- ruling out the "WordNet `lexical_sorts` coverage gap" hypothesis this
session had been carrying since much earlier rounds. `"graph-related"`
is `engine/app/Main.hs`'s own fallback string for a stage whose
`stageConstraint` is `Nothing` -- and `engine/src/Metonymy/Contextual.hs`'s
`contextualFiber` shows there is exactly one such stage: **stage 0, the
very first**, computed by `expandFiber` walking every path from the
source entity via the configured bridge relations, up to `maxDepth`
hops, keeping anything satisfying the near-trivial starting requirement
`HasSort Entity`. If stage 0 alone comes back empty, no lexical
constraint from the sentence is ever even applied -- the tower never
gets the chance to use the very thing this whole session's frontend
work has been building.

Read further (not guessed): `scripts/propose_contextual_scenario.py`
sets `max_depth = language_rules.get("max_bridge_depth", 1)`, and
`data/contextual-language-rules.json` had it hardcoded to **exactly
1** -- only entities *directly* connected to the source via one of 14
specific Wikidata properties (`data/wikidata-runtime-rules.json`: P131/
P159/P17/P276/P749/P361/P355/P463/P527/P101/P921/P176/P50/P137) counted
at all. Many real metonymic bridges plausibly need two hops (place →
organization located there → a specific role/output of that
organization, etc.) that this configuration could never reach even in
principle, regardless of how good the frontend's tree-building or the
knowledge base's lexical coverage ever gets.

**Bumped `max_bridge_depth` from 1 to 2** in
`data/contextual-language-rules.json` -- a single, reversible data value
(no code, grammar, or Haskell logic changed; confirmed no test anywhere
depends on the specific value 1). A real, direct experiment following
from what was just measured, not a guess: if the dominant cause really
is depth, `empty_fiber_reason_counts`'s "graph-related" share should
drop measurably on the next real run; if it stays at (or near) 100%
even at depth 2, that would instead point at the 14-relation whitelist
or the live snapshot's own edge coverage as the real bottleneck --
either way, decisive, not another guess. Full local suite: same
pre-existing baseline (2 failures/13 errors/8 skipped) confirmed
unaffected.

**Next step**: commit, push, wait for `ci.yml`, then ask the user for
one more real `contextual-tower-evaluation.yml` run -- watch
`empty_fiber_reason_counts` (did "graph-related" drop?), `tree_available_
recall` (did it move at all?), and note that deeper graph traversal is a
real, if likely modest, added computational cost for the engine's own
`outgoingPaths`/`incomingPaths` search (branching-factor-to-the-depth),
worth keeping an eye on run time even though nothing here suggests it
would be prohibitive at depth 2.

## The `max_bridge_depth` experiment immediately found a real bug: the source can bridge to itself

`ci.yml` failed on the very first push of the depth-2 change --
`test_verbnet_only_action_builds_checked_layers`
(`tests/evaluation/test_qid_fiber.py`, exercising the real curated
`data/wikidata-openalex-snapshot`) showed stage 0's own `survivors=`
line had grown a fourth entry: `Q639408` -- Waterloo, the query's own
source entity, now appearing as one of its own "bridge candidates".

Read (not assumed) directly from `engine/src/Metonymy/Resolution.hs`:
`outgoingPaths`'s cycle guard only stops a path from revisiting a node
it has already passed *through* (`current \`Set.member\` visited`) --
it never checks whether a path's own *final target* lands back on the
original source. At `maxDepth=1` this can never surface (a single hop
from X can't return to X without a literal self-loop edge, essentially
never present in real data); at `maxDepth=2` it becomes commonplace
wherever the relation set contains a forward/inverse pair over the same
underlying property -- exactly what `data/wikidata-runtime-rules.json`
has for Wikidata P131 (`LocatedIn` forward, `InstitutionOf` inverse),
confirmed as the real cause here (Waterloo → some region (`LocatedIn`)
→ back to Waterloo (`InstitutionOf`) is a genuine two-hop round trip in
the real snapshot). This is a real correctness gap this session's
narrow depth-1 default had been silently hiding the entire time, not
something introduced by the experiment -- raising the depth just
happened to be what finally surfaced it.

The source referring to itself is never a genuine metonymic bridge --
that is exactly the literal reading, already handled by the pipeline's
own separate direct-argument path, not something `expandFiber` should
ever offer as a candidate "fine meaning." Fixed with a one-line filter
in `expandFiber` (`target /= fiberSource query`), with a comment
explaining the exact mechanism and citing the real corpus run that
surfaced it. Confirmed the existing Haskell unit tests are unaffected
by reading them directly: both `engine/test/Main.hs` call sites for
`contextualFiber` hardcode `maxDepth=1` (unrelated to
`data/contextual-language-rules.json`'s own value, which only feeds the
Python-side CLI path), so the new filter can never trigger for them
either way. No local Haskell toolchain exists on this machine to
compile-check the change directly -- verification is necessarily via
the next real `ci.yml` run, same as every other Haskell change this
session has needed.

**Next step**: push, watch `ci.yml` closely -- if
`test_verbnet_only_action_builds_checked_layers` still fails, it means
depth 2 surfaces a *different*, non-self-referencing new candidate too
(a real, separate finding, not a second bug), and that test's own
golden `preferred=`/`survivors=` strings need updating to the real
value the failure output itself names -- read from the actual CI
output, never guessed. Once green, ask the user for the real
`contextual-tower-evaluation.yml` run this whole depth experiment has
been building toward.

## The `expandFiber` fix cleared that failure -- and immediately found the same bug's twin

The next `ci.yml` run confirmed the `expandFiber` fix worked --
`test_verbnet_only_action_builds_checked_layers` passed. But the run
failed differently: `contextual-corpus-test` (the `Makefile` target
running `evaluation/contextual-multidomain/silver-inputs.jsonl` through
`run_contextual_corpus.py` *without* `--allow-failures`) reported
`instances=69 failures=2`.

That fixture (`silver-inputs.jsonl`, small and checked into the repo,
safe to read directly -- not licensed real-corpus text) is dominated by
a `"location-for-institution"` family: 15 place sources ("Stavropol
signed the agreement", ..., the same "Waterloo" entity from the earlier
bug), several paired with a `"direction":"contract"` counterpart, a few
of those marked `"expected_status":"rejected"` -- deliberate safety
tests confirming a specific institution must *not* validate as a
metonymic contraction of a given place (e.g. "IFFHS signed the
agreement" from source "Bonn" must be rejected). `max_bridge_depth`
feeds *both* directions identically via `data/contextual-language-
rules.json`, and `contractTarget`'s own `incomingPaths` walk has the
exact same missing check `expandFiber` just got fixed for -- just
reversed: at `maxDepth >= 2`, the reverse walk can land back on
`target` itself as the path's own `source`, via the same P131 forward/
inverse pair mechanism. A `reject-contract-*` scenario spuriously
finding `target` as its own valid `source` (a self-referencing
contraction) would flip it from correctly-rejected to incorrectly-
accepted -- exactly matching `run_one`'s own `rejected_by_safety`/
`successful` logic for an `expected_status: rejected` row, and exactly
accounting for "failures" (real engine-level failures, not scoring
misses) appearing at all in a target that only checks pipeline success.

Fixed the same way, in the same function pair: `contractTarget` now
filters `source /= target` alongside its existing proof/path
qualifiers, with a comment citing this exact real CI failure as the
evidence (not a preemptive guess) -- the earlier round had deliberately
scoped the fix to `expandFiber` alone per the user's own explicit
choice; this round's real CI failure confirmed the twin function needed
the identical treatment, not merely a hypothetical risk. No local
Haskell toolchain exists to compile-check either change directly.

**Next step**: push, watch `ci.yml` -- if `contextual-corpus-test`
still fails, examine which specific silver-fixture id(s) via whatever
detail the failure surfaces (this Makefile target has no
`--allow-failures`/artifact upload, so the exact failing id isn't
directly visible in the log today; may need a follow-up round adding
one). Once green, ask the user for the real
`contextual-tower-evaluation.yml` run.

## Ambiguity confirmed real, not a bug -- the fixture updated to match

`--print-failures` (new, opt-in, only ever wired into the Makefile's
own safe, checked-in fixture runs -- `contextual-tower-evaluation.yml`
never passes it) named the exact two ids:
`contract-sign-generic-q159`/`contract-sign-commercial-q159` ("VAZ
signed [the/the commercial] agreement" contracting from source
"Russia"), both rejected with `unsafe-contextual-contraction-non-
singleton-fiber`. The new QID-carrying error message (this round's own
addition to `finishContraction`) named the actual ambiguous fiber:
`[Q5281,Q2309,Q6686]` for the generic case. Looked up directly in
`data/wikidata-openalex-snapshot/aliases.jsonl`: Q2309 is VAZ itself
(the expected answer), but **Q5281 is Yandex and Q6686 is Renault** --
two entirely different, real companies, both now reachable from Russia
within 2 hops (Yandex plausibly as another `InstitutionOf`-linked
Russian company; Renault plausibly via VAZ's own real-world corporate
affiliation, a genuine second hop). This is not a bug: at
`max_bridge_depth=1` only VAZ was reachable at all; at 2, the search
correctly finds several real institutions and -- just as correctly --
refuses to silently pick one, exactly the safety property this whole
mechanism exists to enforce.

Updated the fixture to match this new, real, and correct behavior
rather than treating it as something to route around:
`evaluation/contextual-multidomain/silver-inputs.jsonl` now marks both
ids `"expected_status": "rejected"` (matching how every other
genuinely-ambiguous `reject-contract-*` id in the same file is already
marked); `silver-gold.jsonl`'s own `gold_qids` for both changed from
`["Q159"]` to `[]`, matching the same already-established convention
every other `reject-contract-*` id already uses (an empty `gold_qids`
list is scored as a true negative when the fiber is empty, not a missed
positive -- confirmed by reading `score_qid_fibers.py`'s own scoring
loop directly).

**Next step**: push, watch `ci.yml` -- `contextual-corpus-test`'s first
script (`run_contextual_corpus.py`) should now accept both ids as
correctly-rejected, but the *next* two steps
(`score_qid_fibers.py`/`assert_json_equal.py`, comparing against
checked-in `silver-summary.json`/`audited-summary.json`) never even ran
while step one kept failing -- if either of those now mismatches
(the real aggregate numbers shifted along with everything else this
depth experiment has touched), read the exact new values directly from
that failure and update the checked-in summary JSON to match, the same
"read the real value, never guess" discipline as every other step of
this round. Once fully green, ask the user for the real
`contextual-tower-evaluation.yml` run this entire investigation has
been building toward.

## Real recall stays 0.0 even with the depth-2 fix; the real bottleneck is upstream of tree-building

The `max_bridge_depth=2` round above landed and went fully green (commit
`0e2821a`, `ci.yml` run `35295328187`). The real
`contextual-tower-evaluation.yml` run that motivated the whole
investigation (150/150 sample, both Haskell self-reference fixes
applied) then came back: **recall=0.0, precision=0.0, TP=0 on both
WiMCor and ConMeC** -- unchanged from before this depth experiment.
`tree_source_counts` contains no `"stanza"` key at all in either
corpus -- every tree that did get built came from the legacy
`gf-parser` tier or the LLM tier, never the Stanza-UD tree-builder that
several seasons' worth of rounds (nmod-modifier NP, passive, copula,
relative-clause enumeration, embedded-clause dispatch) targeted.

The real, decisive cause is visible in `literal_prediction_reasons`:
`failed:exit1:nested-modifier-unsupported:nmod` alone is 61/150 (41%)
in WiMCor. The metonymic target is structurally a modifier of an NP
("the museum *in Kent*"), not a governing verb's subject/object at
all -- `resolve_action` rejects these *before* `build_gf_tree` is ever
called (the long-documented, deliberately-deferred gap: "requires
widening `engine/src/Metonymy/Elaborator.hs` (`PositiveGFTree`)").
`blockers_per_sentence_histogram` did resolve an old open question
though: most sentences that reach the tree-builder now carry 0 or 1
blocker, not 2+ -- the season's granular sub-bucketing work did
eliminate compounding where it existed; the remaining gap is
architectural (nested-modifier targets), not a pile-up of small fixable
issues.

## Local toolchain unlock: Stanza now runs on this machine, closing the CI round-trip gap

A `python -c "import stanza"` check (previously known to fail here with
a PyTorch DLL error) succeeded outright on 2026-09-18, and a full
`stanza.Pipeline('en', processors='tokenize,mwt,pos,lemma,depparse',
package="ewt")` (after a one-time `stanza.download('en', package="ewt",
...)`, ~1 minute, no auth needed) produces correct UD output locally.
Combined with the already-known local `gf.exe`/pinned `gf-rgl` install
(see the "local GF toolchain" reference), essentially the entire
frontend -- UD parse, dependency-hint classification, GF tree
construction, tree well-formedness -- is now iterable in minutes
locally, not 1-2 hour `contextual-tower-evaluation.yml` CI rounds. Only
the Haskell engine build and Agda `runtimeCheck` still require CI (no
local GHC/Agda toolchain).

Caveat found while using this: `scripts/annotate_dependency_hints.py`'s
own `build_pipeline()` requests the pinned `package="ewt"` model
specifically (not the generic `"default"`/`"combined"` package a bare
`stanza.download('en')` fetches) -- download it explicitly
(`stanza.download('en', package="ewt", processors="tokenize,mwt,pos,
lemma,depparse")`) before running the script, and do so once,
sequentially, before launching parallel annotation jobs: two concurrent
first-time downloads race on writing the same cached model file and one
of them fails with `PermissionError: os.replace(...)`.

## Hand-curated real-sentence pilot: 22 examples, real yield is very low even in-scope

Given real corpus recall stuck at 0.0 despite the whole season's
Stanza-frontend investment, explored a different verification path for
the paper: hand-curate and verify a small set of real WiMCor/ConMeC
sentences end to end (UD role -> GF tree, verified via local `gf.exe`
linearize) instead of relying on the automatic frontend's current
coverage. User-approved scope: only in-scope cases (target is a real
Subject/Object, not a nested-modifier), published with attribution
(WiMCor CC BY-SA 3.0, ConMeC Apache-2.0 both permit quotation).

Locally downloaded both corpora (network access confirmed available
from this environment), ran `annotate_dependency_hints.py` (real local
Stanza) over a seeded 3000-sentence sample from each corpus (WiMCor took
84 minutes, ConMeC 28 minutes -- WiMCor's Wikipedia-style sentences are
longer/more complex on average), then ran `build_gf_tree` locally
against every `dep_status="direct-argument"` row whose governing lemma
is in the known action vocabulary:

```
WiMCor: 1180/3000 direct-argument, 171 with a known lemma, only  4 build cleanly
ConMeC: 2250/3000 direct-argument, 1875 with a known lemma, only 9 build cleanly (1 dropped for a number-agreement defect)
```

**~0.2% yield even restricted to structurally in-scope, lexicon-known
sentences.** Inspecting real near-miss candidates by hand (not
guessing) found the dominant declines are genuine, unrepresentable
grammar gaps, not automation shortcuts a human curator could route
around: bare mass/plural common nouns with zero determiner (largest
single bucket, ~21% of the in-scope pool -- see the `BareCN` attempt
below), first/second-person pronouns ("I"/"we"/"you" -- see the
`IPN`/`WePN`/`YouPn` fix below), and complex embedded-clause/gerund
coordination on the subject (`subject-count:advcl`/`xcomp` -- real
examples inspected turned out to be gerund coordination like "filling
and emptying the fuel tank," not simple "A and B did X," so not a quick
win).

Hand-extended the pool to 22 total (13 auto-built + 9 hand-written,
reusing only already-existing grammar constructors -- `EveryCN`,
`PassCompl0`, and the same String-splicing idiom `OpenPN`/`OpenIndefCN`
already use, e.g. folding a UD `compound` child directly into the noun
literal: `EveryCN "milk carton" "milk cartons"` linearizes correctly as
"every milk carton" since GF's String category has no problem holding
multiple words when constructed directly rather than parsed from raw
text). Every one of the 22 trees was verified via local `gf.exe -run`
linearize, not just eyeballed. Gold-label balance in the resulting 22
is skewed (16 literal / 6 metonymic) -- traced to the hand-curation
step specifically, not the corpus: the 13 auto-built examples alone are
6 metonymic / 7 literal (a healthy, representative split), but the 9
hand-added ones were picked by "which near-miss is easiest to fix" with
no gold-label filter at all, and happened to land on 9/9 literal by
chance. Not yet wired into an evaluation harness or pushed -- exists
only in this local investigation as of this writing
(`build/local-curation/pilot-curated.jsonl`, gitignored).

## `IPN`/`WePN`/`YouPN` landed; `BareSingularCN`/`BarePluralCN` attempted and reverted -- a real parse-ambiguity finding, not a formal-correctness risk

Motivated directly by the pilot above, attempted two grammar extensions
in the same round: first/second-person pronouns, and bare
(determiner-less) common-noun NPs for the ~21%-of-in-scope
`zero-determiners` bucket.

**`IPN`/`WePN`/`YouPN` : NP** -- landed. Exact same idiom as the
existing `HePN`/`ShePN`/`ItPN`/`TheyPN` (RGL's closed `Pron` vocabulary
-- `i_Pron`/`we_Pron`/`youSg_Pron`, confirmed present in the pinned
`gf-rgl` commit -- through `mkNP`'s already-open `Pron -> NP` overload).
Verified locally: `Pred IPN (Compl VN_Hear (OpenIndefCN "owl" "owl"))`
linearizes as "I hear a owl" -- correct person/number agreement. An
earlier same-session attempt to represent "I" via a hand-rolled
`OpenPN "I"` instead produced the ungrammatical "I **hears**", because
`OpenPN` is hardcoded to third-person-singular agreement regardless of
the literal string given to it -- confirming this needed the real
`Pron`-based construction, not a workaround. Re-ran the full existing
`test_gf_parse_diagnostic_matrix.py` sentence battery locally (`gf.exe
-run`, comparing parse-derivation counts before/after) with only this
addition: zero regressions, no sentence's derivation count changed
(expected -- a 0-argument constant can only match its own fixed word,
never spuriously match an unrelated token). `_KNOWN_ZERO_ARITY_CONSTRUCTORS`
in `contextual_rule_compiler.py` extended to match, and
`CompileGfConstraintsPronounTests.test_pronoun_subjects_walk_safely`
now covers all seven pronoun constructors instead of four.

**`BareSingularCN`/`BarePluralCN` : String -> NP** -- attempted, then
reverted. Unlike `OpenIndefCN`/`OpenDefCN`/`EveryCN` (which always
splice in a fixed anchor word -- "a"/"the"/"every"), a truly bare NP has
*no* fixed word at all: `lin NP {s = \_ => noun.s; a = R.agrP3 R.Pl}`.
Confirmed locally via `gf.exe -run` against real sentences that this
creates severe combinatorial parse ambiguity for GF's raw-text parser:
"Waterloo announces a general in Hitchin of Hertfordshire" went from a
handful of derivations to 96, and re-running the full
`test_gf_parse_diagnostic_matrix.py` battery showed two
previously-clean sentences now failing outright ("Because Napoleon
announces...", "On 18 May 2010, Waterloo announces..." -- both later
confirmed to be a *different*, pre-existing artifact of testing via bare
`gf.exe -run` instead of through the engine's own `spaceBeforeCommas`/
`spaceAroundParens` preprocessing, not a real regression from this
change; re-tested with a manually inserted space before each comma and
both parsed cleanly again, 16 and 4 derivations respectively).

The combinatorial-ambiguity finding itself is real and specific to
`BareSingularCN`/`BarePluralCN`, though, confirmed independently of that
comma artifact. Worth stating precisely what kind of risk this is and
isn't, since it came up directly in conversation: this can **never**
turn into an incorrect *accepted* metonymy detection -- Agda's
`runtimeCheck` independently re-verifies every candidate tree regardless
of which (possibly wrong) derivation the untrusted GF-parser proposer
picked first, exactly the same trust boundary that already protects
every other tier (Stanza/LLM/legacy) from a bad candidate. The entire
cost of this ambiguity is on **recall**: a wrong first-choice derivation
degrades to the same `abstain`/`exit4` outcome as any other malformed
proposer output, never to a wrong-but-accepted result. That said, the
legacy `gf-parser` tier is *currently the dominant source of real
successes* in `contextual-tower-evaluation.yml` runs (64/150 and
105/150 in the most recent real run), so a recall-only regression there
isn't free either, and 96-way ambiguity for a single sentence is a large
effect to accept without measuring it for real. Reverted pending a
design that doesn't add an unanchored `String`-based NP to the same
shared PGF that `engine parse` searches -- e.g. reachable only from the
Stanza/hand-built tree-*construction* path (which never calls GF's own
parser at all, so can't be affected by this class of ambiguity), not
from raw-text parsing. `grammar/Metonymy.gf` keeps a dated comment
recording exactly this reasoning at the point where the two functions
would go, so a future attempt starts from the measured finding instead
of re-discovering it.

## Automatic (lemma, tree-relation) -> constraint derivation, and its dictionary grown from real WiMCor sentences one at a time

The `evaluation/pilot-decode-wimcor/` Valparaiso/Haifa narrowing result
(both real sentences narrowed to their single correct QID once a
second, real "degree"-derived constraint was added) was built by hand
-- a human reading the sentence, spotting "degree", and hand-writing a
low-level scenario TSV row, bypassing `compile_gf_constraints` and the
GF tree entirely. The user asked for this to work automatically: every
significant content word in a sentence should be able to narrow the
fiber on its own, discovered from the GF tree's own structure, not from
a person re-deriving it per example.

`scripts/contextual_rule_compiler.py`'s `compile_gf_constraints` now
supports a new, generalized mechanism, keyed on **(lemma, structural
relation to the metonymy target)** -- deliberately not a bare
word->requirement table. A flat lemma-only lookup was the first design
proposed and was rejected during design review: the same word can
appear elsewhere in a sentence referring to something else entirely
("He interviewed the dean, who had a degree from Yale, about
Valparaiso's admissions policy" -- "degree" there is about the dean and
Yale, not Valparaiso), so the lookup has to be keyed on *how* the word
attaches, the same discipline the pre-existing `context_templates`
(`ModifyNP+InPP` etc.) already uses for entity-resolving modifiers.

Two construction/relation types, both implemented as pure tree-shape
checks over hand-built (never yet auto-produced, see below) GF tree
text:
- **`ConjClauseObject`**: the object of the OTHER VP in a
  `PredConjVP`/`PredOrConjVP` coordination -- "shares the target's
  subject" is guaranteed by that constructor's own shape (one NP
  argument for both VPs), nothing extra to verify.
- **`ModifyNPObject`**: a `ModifyNP`+preposition modifier whose object
  is a common noun rather than the existing QID-resolving proper-noun
  case.

New `data/contextual-context-triggers.json` holds the actual
`(lemma, construction) -> requirement` table, deliberately seeded only
with entries individually found and verified against real corpus text,
not invented at VerbNet-import scale ahead of time.

**A real bug caught before it reached CI**: the first `ConjClauseObject`
implementation searched the whole tree for any `Compl`/`PassCompl`,
which matched one buried inside an unrelated `ModifyRelVP` relative
clause in a negative test built specifically to probe this risk --
fixed by restricting the search to direct VP children of
`PredConjVP`/`PredOrConjVP` only.

**A second real risk, found via real corpus search, not a hypothetical**:
searching WiMCor for the "attended/studied at X and
received/earned/obtained a `<noun>`" shape that produced the Valparaiso/
Haifa examples turned up 14 real candidates -- most had to be rejected
because the noun explicitly names a *different* institution than the
metonymy target ("received a degree **at** the University of Maryland"
for a Gettysburg mention, "earned his MBA **from** San Diego State
University" for an Oklahoma City mention, similarly for Webster/Yale/
Deep Springs/Kingston). The original `ConjClauseObject` code called
`lexical_head` first, which strips a `ModifyNP` wrapper before checking
the lemma -- meaning a future tree that represented "degree at the
University of Maryland" as `ModifyNP(degree, AtPP(...))` would still
have matched and wrongly attached `Requires HasSort University` to the
wrong target. Fixed: the object must now be a completely bare
`OpenIndefCN`/`OpenDefCN`/`OpenAdjDefCN`/`OpenAdjIndefCN` node, no
wrapper at all -- any modifier, benign or institution-redirecting alike,
safely declines.

**Dictionary growth, one real sentence at a time** (all verified via
local Stanza structure + local `gf.exe` tree validity, then run through
the real, shipped `compile_gf_constraints`/`data/*.json`, not a test
double):

| lemma | construction | requirement | strength | real sentence |
|---|---|---|---|---|
| degree | ConjClauseObject | HasSort University | requires (individually Wikidata-verified for Valparaiso/Haifa) | "He attended Valparaiso ... and received his bachelor's degree ..." |
| doctorate | ConjClauseObject | HasSort University | prefers | "In 1697, he studied at Pisa and obtained his doctorate of law in 1719." |
| fraternity | ConjClauseObject | HasSort University | prefers | "He enrolled at UCLA and joined the Delta Sigma Phi fraternity." (a US fraternity is specifically a university/college social organization) |

`strength: prefers` (not `requires`) is the honest default for every
entry except `degree`: only `degree`'s implication has been individually
checked against live Wikidata P31/P279 chains the way the Valparaiso/
Haifa result required; the others are real, structurally-clean sentences
but their specific implied institution hasn't been checked yet, so they
stay at the safer, never-wrongly-eliminating strength.

`ModifyNPObject` still has no real corpus example after a deliberate
search (campus/faculty/professor/alumnus/scholarship/tuition/fellowship
near attend/study/enroll, both WiMCor and ConMeC, zero matches) -- a
real, not-yet-explained finding: a bare proper-noun metonymy target
rarely takes an in-place PP modifier directly in this genre of
biographical text; when a "with/at/from X" phrase appears near the
target, in every real example found so far it attaches to the *verb*
instead (an oblique adjunct, not an NP-internal modifier) -- see the
`PassComplRetained` finding below, which is exactly this pattern.

**A genuine grammar gap, closed with a new `V3` category**: "He
attended Ankara and **was awarded** a PhD degree in Pharmacy" -- a
retained-object passive (the recipient is promoted to subject, but the
theme/object is *retained*, not dropped, and there is no "by"-agent).
None of the three existing VP-building rules fit: `Compl` needs active
voice; `PassCompl`'s NP argument is specifically a "by"-agent (a
different semantic role, confirmed by its own doc comment); `PassCompl0`
takes no further NP at all. The retained object is inherently a
ditransitive phenomenon -- confirmed by reading the pinned `gf-rgl-src`'s
actual abstract `Verb.gf`, not guessed: `Slash2V3 : V3 -> NP -> VPSlash`
("give it (to her)") leaves exactly the recipient slot open, and
`ExtendEng.PassVPSlash : VPSlash -> VP` promotes that open slot to
subject -- composing the two gives "NP was awarded object" with no
agent, exactly this construction. Added `cat V3` and
`PassComplRetained : V3 -> NP -> VP` to `grammar/Metonymy.gf`, one
lexicon entry `Award : V3` (`mkV3 "award"`, `ParadigmsEng`, already
open), and `PassComplRetained verb object = ExtendEng.PassVPSlash
(Slash2V3 verb object)` in `MetonymyEng.gf` (`ExtendEng` qualifier
needed for the same reason `PassAgentVPSlash` already needs it: `ExtraEng`,
already open for VP-coordination, independently redeclares its own
`PassVPSlash` with an identical signature -- checked directly against
the pinned source, not guessed a second time). Compiled and linearized
locally (`He announces Ankara and is awarded a degree`) before being
written into any test. The round-trip parse surfaced the pre-existing
`OpenPN2 "a" "degree"`-style ambiguity that any `OpenIndefCN` object
already carries (confirmed on an unrelated pre-existing sentence,
"Anna announces a degree", with no `PassComplRetained` involved at all)
-- not a new risk this addition introduced.

`ConjClauseObject`'s tree-shape checks (both the primary-action
`first_node` lookup and the coordinated-sibling search) now also
recognize `PassComplRetained` alongside `Compl`/`PassCompl`. The
existing `degree` trigger fires automatically on the hand-built Ankara
tree with no new dictionary entry -- this round grew the *grammar*, not
the dictionary.

**Still true, unchanged from the mechanism's first round**: no automatic
tree-builder (`scripts/build_gf_tree_from_dependencies.py`, "Coordination
(UD conj/cc) is deferred") produces a `PredConjVP`/`PredOrConjVP` shape
from a real UD parse today, so none of this fires on a real corpus run
yet -- every example above is hand-built and gf.exe-verified, testing
the consuming side (`compile_gf_constraints`) and now also the grammar,
not the producing side. Teaching the tree-builder to actually emit these
shapes from real UD `conj`/`cc` parses (reusing these already-verified,
already-compiled grammar constructors -- zero further grammar risk) is
the next, separate round.

## Two more real gaps closed (`ComplOblique`, `ModifyRelAtVP`); one real gap found and deliberately deferred (agentive retained-object passive); cross-sentence discourse ruled out entirely

Asked to assess what further grammar extensions the trigger-dictionary
mechanism above would need, then to implement as many as possible. Four
candidates were on the table, found by continuing the same real-corpus
search:

**1. `ComplOblique : V -> PP -> VP` -- implemented.** The single most
frequent blocker found while searching for more `ConjClauseObject`
examples: "graduated **WITH** a diploma", "enrolled **AS** a doctoral
student", "worked **AS** ship's surgeon" -- an intransitive verb plus
exactly one oblique PP adjunct, which `Compl` cannot represent (it needs
a direct object, not an oblique). Deliberately narrower than the general
"attach any PP to any VP" mechanism this file already documents as *not*
attempted (risked silently reinterpreting which constituent a PP
modifies) -- `ComplOblique` is one new, closed VP shape (`V` + `PP`
together, both from this project's own closed lexicon/preposition set),
confirmed against the pinned `gf-rgl-src`'s own `Constructors.gf`:
`mkVP : V -> VP` ("sleep") composed with the separate `mkVP : VP -> Adv
-> VP` ("sleep here") overload is exactly this shape. Added `cat V`
(this project had only `V2`/`V3` before), a new preposition `AsPP`, and
lexicon entries `Graduate`/`Work`/`Enroll`. New dictionary entry:
`diploma -> Prefers HasSort University`, from the real Berklee sentence
("He later attended Berklee and graduated with a diploma..."). Python
side: `coordinated_object_lemma` (renamed from an inline lambda,
factored out so `RelativeClauseObject` below could reuse it) reads one
level deeper for `ComplOblique` -- the PP's own NP argument -- while
keeping the same no-`lexical_head` safety guarantee: a modifier on the
PP's object, benign or institution-redirecting, still safely declines.

**2. `ModifyRelAtVP : NP -> NP -> VP -> NP` -- implemented, the deepest
RGL dig of this whole investigation.** Real shape: "He studied at
Padgate Training College, **where** he was awarded a Certificate in
Education." -- a second clause attached to the *target's own NP* via a
relative pronoun, describing an event ("was awarded...") that happened
there. Checked directly, not guessed: this pinned commit's RGL has no
locative "where" relative pronoun at all (`Structural.gf`/
`ExtraEngAbs.gf` declare only `which_who_RP`/`that_RP`/`which_RP`/
`who_RP`) -- built instead from the real, grammatical alternative
phrasing "at which", composing three abstract functions found by reading
`Verb.gf`/`Sentence.gf`/`Extend.gf` directly: `VPSlashPrep : VP -> Prep
-> VPSlash` ("live in (it)") opens a prepositional gap *on top of an
already-complete VP* (so the embedded clause's own retained object, e.g.
"a certificate", stays intact -- only the locative "at ___" is left
open); `SlashVP : NP -> VPSlash -> ClSlash` ("(whom) he sees") supplies
the embedded clause's own subject ("he"); `PiedPipingRelSlash : RP ->
ClSlash -> RCl` ("with whom John lives") fronts the gap's preposition
together with the relative pronoun. `SlashVP` needed a new `open
SentenceEng` -- checked the real compiler output (not assumed clean)
after adding it: no new conflict warnings beyond the same benign
lincat-name-shadowing pattern every category in this grammar already
shows. Verified locally: `Pred (OpenPN "He") (Compl Announce
(ModifyRelAtVP (OpenPN "Padgate") (OpenPN "He") (PassComplRetained Award
(OpenIndefCN "certificate" "certificates"))))` linearizes to "He
announces Padgate , at which He is awarded a certificate".

New relation type `RelativeClauseObject` in `compile_gf_constraints`:
the trigger word is inside the VP embedded in a `ModifyRelAtVP` that
modifies the *primary complement's own object* (the target NP itself) --
distinct from `ConjClauseObject`'s coordinated-sibling relation. Reuses
`coordinated_object_lemma` for the embedded VP, so the same safety
guarantee applies one relation deeper: a "certificate **from**
Cambridge" inside the relative clause declines just as readily as a
"degree **at** the University of Maryland" does for the coordinated
case. New dictionary entry: `certificate -> Prefers HasSort University`
(the Padgate sentence -- noted honestly: the source surface "Padgate
Training College" already contains "College", a milder version of the
Yale/Harvard self-describing-name caveat from the mechanism's first
round).

**3. Agentive retained-object passive ("X was granted Y **by**
TARGET") -- found, deliberately deferred, not implemented.** A real
sentence surfaced ("In 2000, Fielding was granted his doctorate by
Irvine") where the *metonymy target itself* would sit in the *agent*
position of a ditransitive passive, not as an object anywhere in a
coordinated or embedded clause. This is a fundamentally different
problem from 1/2 above: it's not a new tree-shape for
`compile_gf_constraints` to recognize, because the target's *hole role*
itself would need a third value -- an "agent hole" -- alongside this
project's existing `SubjectHole`/`ObjectHole` (`engine/src/Metonymy/
Types.hs`'s `HoleRole`). That reaches into the Haskell type the whole
formal core is built on, not just the Python/GF frontend layer,
correctly out of scope for a grammar-extension round. Also: the one
supporting example is unconfirmed as genuine metonymy (no wider check
that "Irvine" there is really the ambiguous place-standing-for-
institution this project's fixtures target, rather than e.g. a surname)
-- low enough confidence, combined with the real architectural cost,
that this was not worth pursuing without first finding a second,
independently-verified example.

**4. Cross-sentence discourse connections -- ruled out, not a grammar
question at all.** One real candidate ("He went to St Andrew ... The
very same day he defended seven theses on medicine and was awarded the
doctorate") turned out to have the trigger word in a *different
sentence* than the target mention. Every part of this pipeline
(`gf_sentence`, `compile_gf_constraints`, the TSV scenario format) is
scoped to one sentence by design; aggregating context across sentences
would need genuinely new infrastructure, not a grammar or relation-type
addition -- not attempted.

Dictionary after this round (six entries total, `data/contextual-
context-triggers.json`): `degree`/`doctorate`/`fraternity`/`diploma` via
`ConjClauseObject`, `certificate` via `RelativeClauseObject`. Only
`degree` is at `requires` strength (individually Wikidata-verified for
Valparaiso/Haifa); every other entry stays at `prefers` -- real,
structurally-clean sentences, but their specific implied institution
hasn't been individually checked yet, so they can narrow a fiber but can
never wrongly eliminate the correct answer on their own.

## `data/predicates.tsv`'s local:selectional-lexicon table was half-built -- found while chasing a container-for-content/causer-for-result dead end

Investigating why ConMeC's container-for-content/causer-for-result
families (flute/extinguisher/orchestra -- "is heard", "was activated")
gave no useful second signal for the context-trigger mechanism above led
somewhere more fundamental: their *primary* action itself resolves too
weakly. Checked directly, not guessed: VerbNet's own class for "hear"
(`see-30.1`, shared with feel/perceive/see/smell/taste) has a literally
empty `<SELRESTRS/>` for its Stimulus role in the pinned commit's own
`see-30.1.xml` -- not a mapping gap (unlike `region`->`Place` in the
original VerbNet-import round), a genuine absence of restriction data in
VerbNet itself. Checked `data/framenet-role-capabilities.json`'s
generator (`scripts/generate_framenet_capabilities.py`, SemLink VerbNet
x FrameNet aggregation) too: "hear" maps to FrameNet's
`Perception_experience` frame, but aggregating every compiled VerbNet row
across all six sibling verbs in that frame still gives `HasSort Entity`
19 times out of 20 -- the whole frame is equally generic, so
cross-verb agreement recovers nothing.

Asked about "read" as a comparison point (`читать Достоевского`,
"reading Dostoevsky" -- author-for-work metonymy) -- turns out `read`
has the *exact same* disease in VerbNet's own compiled
rows (generic `Entity`), but it's already fixed: `data/predicates.tsv`, a
small hand-curated table independent of VerbNet entirely
(`provenance: local:selectional-lexicon`, `strength: HardRequirement`),
already carries `read -> Readable`, and `resolve_action`'s own documented
policy (`contextual-language-rules.json`'s
`"prefer-hard-else-disjoin-compiled-preferences"`) makes this hard
override win over VerbNet's weaker compiled rows for the same lemma --
confirmed directly, not assumed, by loading both and calling
`resolve_action` on a real sentence.

But `data/predicates.tsv` turned out to be half-built: of its 10 rows
(read/study/review/translate/drink/eat/listen-to/watch/wear/sign), only
3 (`Read`/`Drink`/`Sign`) had a matching V2 constructor in
`grammar/Metonymy.gf`/`MetonymyEng.gf` -- the other 7 named a GF function
in their `gf_expression` column that simply didn't exist, making them
unreachable for real tree-building despite `resolve_action` already
knowing the intended Sort. Added the missing 7
(`Study`/`Review`/`Translate`/`Eat`/`ListenTo`/`Watch`/`Wear`, all
`mkV2 "..."` except `ListenTo = mkV2 (mkV "listen") to_Prep` -- the
phrasal-V2 shape `data/predicates.tsv`'s own `gf_expression` column
already specified, confirmed against the pinned `gf-rgl-src`'s
`ParadigmsEng.gf` overload set) plus a new 8th, `hear -> Audible`
(the lemma this investigation started from), same proven
`Read`/`Drink`/`Sign` pattern, each linearization checked via local
`gf.exe` before being written into any test.

Along the way, found (and fixed the same way `wear`'s `"wore"` already
was) three more real gaps: `action_forms()`'s own regular-suffix guessing
never produces `studied` (gives `studyed`), `ate`, or `heard` -- all
three needed a `morphology_overrides` entry
(`data/contextual-language-rules.json`) the same way `wear`/`announce`/
`read`/`sign` already have one. Without it, `resolve_action` would never
match these verbs' most common past-tense surface form in real text at
all (`hear`'s own real ConMeC candidate sentences are all past tense --
"is heard" already passive-inflected via `heard`, so this wasn't a
hypothetical).

Also confirmed, not swept under the rug: `resolve_action`'s *no-hint*
fallback path (used whenever a real dependency hint isn't available --
already documented elsewhere in this file as the actual, common case in
real CI, since Stanza isn't installed there) mis-assigns passive-voice
subjects to `SubjectHole` instead of `ObjectHole` for verbs like
this -- "A bass flute is heard..." resolves to `SubjectHole -> HasSort
Human` (wrong; should be `ObjectHole -> HasSort Audible`). Verified this
is a **pre-existing, general** limitation, not something this round's
work introduced: the exact same sentence shape already mishandles the
long-working `read` the identical way ("The book is read by millions"
also resolves to `SubjectHole -> HasSort Human`). Left alone,
out of scope for this round -- the real production pipeline always
supplies a genuine dependency hint (which does track passive voice
correctly via `annotate_dependency_hints.py`'s own `voice` field); this
finding is recorded here so a future round chasing ConMeC's
container-for-content/causer-for-result examples through the no-hint
path specifically doesn't have to rediscover it.

**Correction, caught by real CI, not by local verification**: the "half-
built" framing above was wrong in its own diagnosis. The first push of
this round (hand-adding `Study`/`Review`/`Translate`/`Eat`/`ListenTo`/
`Watch`/`Wear`/`Hear` as `V2` declarations directly to
`grammar/Metonymy.gf`/`MetonymyEng.gf`) failed real CI:
```
grammar/GeneratedMetonymy.gf:
   cannot unify the information
       fun Eat : Metonymy.V2 ;
   in module Metonymy with
       fun Eat : V2 ;
   in module GeneratedMetonymy
```
Reading `scripts/generate_gf_lexicon.py` (only after the failure, which
is the actual mistake here -- this should have been read, or the
generator actually run, *before* concluding anything was "missing")
showed the real mechanism: it already emits a `fun X : V2` declaration
(and the matching `mkV2 "..."` linearization, straight from
`data/predicates.tsv`'s own `gf_expression` column) into
`grammar/GeneratedMetonymy.gf`/`GeneratedMetonymyEng.gf` for **every**
`predicates.tsv` row except three hardcoded exceptions
(`base_predicates = {"Read", "Drink", "Sign"}` in that script -- plus
`Announce`, handled separately). Confirmed by actually running the
generator locally (pure Python, no Haskell needed) *before* editing
anything a second time: `Study`/`Review`/`Translate`/`Eat`/`ListenTo`/
`Watch`/`Wear` were **already** being generated correctly, every single
time, since long before this round started -- the grammar was never
half-built at all. The only genuinely new thing this round needed was
the `hear` row in `data/predicates.tsv` itself; adding it alone (no
`Metonymy.gf`/`MetonymyEng.gf` edit at all) makes the generator produce
`fun Hear : V2 ;`/`Hear = mkV2 "hear" ;` automatically, confirmed by
regenerating locally and compiling `GeneratedMetonymyEng.gf` (not just
`MetonymyEng.gf` alone, which is what the first, failed local check had
compiled -- the real gap in that verification, now fixed for future
grammar rounds too: always compile the *generated* companion file
locally, not just the hand-written one, since that is what CI actually
builds). The 8 hand-declared `V2` lines were reverted; only the
`predicates.tsv`/`morphology_overrides` data changes and the `hear`
finding itself stood.

## Synthetic multi-domain trigger dictionary (17 families, 78 new entries)

**Honest framing first, since this section is different in kind from
everything above it**: every entry added in this round is *constructed*,
not corpus-derived. A full real-corpus search (WiMCor's complete 41200-row
test split, ConMeC's complete 5999-row set) for `ConjClauseObject`-style
material using the newly-completed verbs (`wear`/`drink`/`eat`/`watch`/
`listen to`) as the primary action found almost nothing usable outside the
University domain, and -- more importantly -- **no real sentence in either
corpus ever combines two independent context-trigger signals**. Every real
example this project has built this season (Valparaiso, Haifa, Pisa, UCLA,
Berklee, Padgate) is exactly "one weak base-action constraint + one
trigger" -- two stages, never a genuine multi-layer tower. This section is
the deliberate counter-demonstration, not an attempt to raise real recall:
it shows (1) the `(construction, lemma) -> requirement` mechanism
generalizes far past University using only Sort constants that already
exist in `engine/src/Metonymy/Types.hs` (zero Haskell/Agda risk, the same
"Ярус 1" discipline as the VerbNet selectional-preference expansion
earlier in this file), and (2) the mechanism already supports a genuine
2-independent-signal tower today, it just never had real material to
exercise it on.

**A fact found while designing this, worth calling out because it revises
an earlier pessimistic note in this file**: none of `ConjClauseObject`,
`ModifyNPObject`, or `RelativeClauseObject` actually gate on `SubjectHole`
vs `ObjectHole` in `scripts/contextual_rule_compiler.py` -- traced all
three call sites of `_lookup_context_trigger` directly, none reference
`proposal["role"]` at all. The "SubjectHole-variant honestly deferred"
language elsewhere in this document is about a *different*, unrelated gap
(an agentive retained-object passive shape needing a third `HoleRole`
constructor in Haskell), not about these three constructions. SubjectHole-
targeted synthetic examples are still not built in this round (the
grammar's closed vocabulary makes building target-as-subject trees a
separate exercise), but the code is not the blocker anymore.

**17 families, 78 new entries** (`data/contextual-context-triggers.json`,
83 total triggers including the 5 pre-existing University-domain ones),
`strength` deliberately kept at `"prefers"` throughout (never `"requires"`
-- honest, since none of these were checked against any real corpus or
live Wikidata, unlike `degree`/`doctorate`/`fraternity`/`diploma`/
`certificate` above them in the same file):

| Sort | new entries |
|---|---|
| `University` (extension) | 8 |
| `ResearchInstitution` | 4 |
| `ScientificDiscipline` | 4 |
| `Government` | 4 |
| `PoliticalOrganization` | 4 |
| `BusinessOrganization` | 6 |
| `LiteraryWork` | 6 |
| `MusicalWork` | 5 |
| `Film` | 4 |
| `Brand` | 4 |
| `Producer` | 3 |
| `Product` | 2 |
| `Clothing` | 6 |
| `Food` | 4 |
| `Drinkable` | 6 |
| `CommunicationContent` | 6 |
| `Programme` | 2 |

Every trigger lemma is a plain string matched inside `OpenIndefCN`/
`OpenDefCN` (GF's open common-noun constructors) -- confirmed by reading
`_noun_lemma` directly: it extracts the lemma from the tree text itself,
never through `data/wordnet-context-rules.json`/`data/contextual-gf-
nouns.json`. This means new trigger words needed **zero** WordNet/noun-
dictionary additions, only new JSON rows. The only real constraint was
that the sentence's *verb* has to exist as a compiled GF `V2` -- every
sentence in this round reuses only the 12 already-stable, already-
gf.exe-verified verbs from earlier this session (`Announce`/`Read`/
`Drink`/`Sign` plus the 8 `data/predicates.tsv` verbs), so no new
`CTX_*`/`WN_*` hash-name lookups were needed either.

One real grammatical snag found and fixed while drafting: `OpenIndefCN`
always emits the article `"a"`, never `"an"` (it is a hand-written
literal-string constructor, not RGL's phonology-aware article machinery)
-- confirmed by batch-linearizing all 78 candidate lemmas through local
`gf.exe` before committing to any of them, which caught `"a alumnus"`/
`"a electorate"`/`"a atelier"`/`"a overture"`/`"a album"`/
`"a advertisement"`/`"a assembly"`/`"a epilogue"` as ungrammatical. Fixed
by substituting consonant-initial synonyms (`graduate`/`ballot`/
`boutique`/`concerto`/`record`/`billboard`/`conveyor`/`glossary`) rather
than touching the grammar -- this is a pre-existing, project-wide
characteristic of `OpenIndefCN` (not something this round introduced),
and every other vowel-initial noun already in the lexicon has the same
latent issue.

**Flagship towers** (`MultiConstraintTowerTests` in the new test file):
five sentences, each combining two *independent* trigger signals on the
same target from two different tree positions, narrowing across two
different Sorts in one sentence -- verified via local `gf.exe` before
being written into the test file:

1. `"He announces Ashford on a campus and announces a grant"` --
   `ModifyNPObject`(campus → `University`) + `ConjClauseObject`(grant →
   `ResearchInstitution`).
2. `"He announces Ashford from a boutique and announces a trademark"` --
   `ModifyNPObject`(boutique → `Clothing`) + `ConjClauseObject`(trademark
   → `Brand`).
3. `"He announces Ashford, at which He is awarded a contract, and
   announces a fellowship"` -- `RelativeClauseObject`(contract →
   `BusinessOrganization`) + `ConjClauseObject`(fellowship →
   `ResearchInstitution`) -- the first test in this project combining
   `RelativeClauseObject` and `ConjClauseObject` in one tree (a
   `PredConjVP` whose first VP's own object is a `ModifyRelAtVP`).
4. `"He announces Ashford from a vineyard and announces a menu"` --
   `ModifyNPObject`(vineyard → `Drinkable`) + `ConjClauseObject`(menu →
   `Food`).
5. `"He announces Ashford from a broadcast and announces a segment"` --
   `ModifyNPObject`(broadcast → `CommunicationContent`) +
   `ConjClauseObject`(segment → `Programme`).

New test file: `tests/evaluation/test_compile_gf_constraints_synthetic_
multidomain_triggers.py` (32 tests) -- a `SortVocabularyCoverageTests`
class that parses every `requirement` string in the real shipped JSON
file against a hand-maintained mirror of the 47-constructor `Sort` enum
(catches a typo across all 83 entries at once, since nothing on the
Python side validates this at runtime otherwise -- `compile_gf_
constraints` copies a trigger's `requirement` string through completely
unexamined, confirmed by reading `_context_trigger_constraint` directly),
a `TriggerDictionaryHygieneTests` class enforcing the closed `construction`
vocabulary and the "synthetic entries are never `requires`" rule
programmatically, one test class per family (`subTest`-parametrized over
that family's lemmas, reusing one verified tree shape per construction),
the five tower tests above, and a repeat of the existing negative-clause
guard on two new-family lemmas.

**Explicitly not done in this round** (see the plan file's own "Дальше"
section): no live pipeline run against a real Wikidata snapshot for these
invented entities (there is nowhere for names like "Ashford" to have a
QID) -- this round is dictionary-and-unit-test-level only, the same scope
as every other "Ярус 1" round this session. SubjectHole-targeted examples
are not built despite the code allowing them (see the fact above).
Container-for-content with a real container noun as the *head* (not just
as a trigger word) would need new `data/wordnet-context-rules.json`
entries -- not needed here since trigger lemmas are matched structurally,
but would be needed for a real `ModifyNP`+QID-alias path later.

## A real, pre-existing CI regression found while pushing the round above,
## unrelated to it -- a duplicate GF function for "hear"

Pushing the synthetic-trigger commit hit a real CI failure that had
nothing to do with it: `engine/test/Main.hs`'s "VerbNet auditory
preference activates musical works" (`"Alice hears Mozart"`, expected
automatic-expansion count 2) had already been failing for the **previous
two commits** (`ec5a05e`, `01950ed`) without anyone noticing -- confirmed
by checking each commit's own CI run directly (`a964f0c`, the commit
before `hear` was added to `data/predicates.tsv`, was green; every commit
since has been red on this exact test).

**Root cause, found by reading code, not guessing**: `data/predicates.tsv`
(manually curated, `HardRequirement`) and `data/verbnet-predicates.tsv`
(VerbNet-imported, `SelectionalPreference`) are architecturally meant to
be *complementary* (`docs/architecture.md`: "The production predicate
table combines manually audited `data/predicates.tsv` entries with
generated `data/verbnet-predicates.tsv` entries") -- and `scripts/
import_verbnet.py`'s own `extract()` function is explicitly designed to
exclude any lemma already present in `data/predicates.tsv` from being
written into `data/verbnet-predicates.tsv` (`existing_lemmas(arguments.
base_predicates)`, passed straight into `extract`'s `excluded` set). But
`data/verbnet-predicates.tsv` was last regenerated on 2026-08-28, weeks
before this session added a `hear` row to `data/predicates.tsv` -- so its
own `verbnet-hear` row (`VN_Hear`, `Human`/`Audible`, `SelectionalPreference`)
was never re-excluded and went stale. Confirmed by direct comparison:
`hear` was the *only* lemma present in both files (checked programmatically,
not by inspection alone).

`scripts/generate_gf_lexicon.py` compiles **every** row from *both* files
into its own `V2` GF function (`predicates = read_rows(predicates.tsv) +
read_rows(verbnet_predicates.tsv)`, one `fun`/`lin` pair per row, no
lemma-level deduplication) -- so once both `Hear` (from `data/
predicates.tsv`) and `VN_Hear` (from the stale `data/verbnet-predicates.tsv`
row) existed as separate compiled `V2`s both linearizing `"hear"`/`"hears"`,
`"Alice hears Mozart"` became genuinely ambiguous at parse time. Confirmed
directly with the local GF toolchain (`p -lang=GeneratedMetonymyEng "Alice
hears Mozart"`) before touching anything: the ambiguity was real, not a
guess. `engine/test/Main.hs`'s `requireParseTrees` returns *every*
ambiguous parse tree (`Right trees` is a list), and `automaticExpand` is
run via `concatMap` over all of them -- so the test's hardcoded expected
count of 2 (written when only `VN_Hear` existed) silently stopped matching
once a second, redundant `Hear`-driven parse entered the mix.

**Fix**: removed the stale `verbnet-hear` row from `data/
verbnet-predicates.tsv` (the one-line change `scripts/import_verbnet.py`
would already have made itself had it been re-run after `hear` was added
to `data/predicates.tsv`), then regenerated `grammar/GeneratedMetonymy.gf`/
`GeneratedMetonymyEng.gf`/`data/contextual-gf-actions.json` via `scripts/
generate_gf_lexicon.py` locally -- the diff is exactly the expected three
lines (`VN_Hear : V2 ;` and its linearization removed, `hear`'s entry in
`contextual-gf-actions.json` retargeted from `VN_Hear` to `Hear`).
Re-verified via local `gf.exe` that `"Alice hears Mozart"` no longer has
any `VN_Hear`-driven parse. High confidence this restores the test's
original passing behavior exactly (not just "some" passing behavior):
the old `VN_Hear` row and the new `Hear` row have **identical**
`subject_sort`/`object_sort` (`Human`/`Audible`) -- only `strength` and
the function name differed, and `Metonymy.Automatic.applyStrength` only
scales `candidateScore`, never the candidate *count* -- so the actual
requirement-driven candidate search `automaticExpand` performs is
unchanged from what it always was; only the spurious duplicate parse
path is gone. `hear` was confirmed to be the *only* lemma ever present in
both predicate tables -- this class of bug cannot recur for any other
lemma today, though it could if `data/predicates.tsv` and `data/
verbnet-predicates.tsv` are edited independently again without
re-running `import_verbnet.py`'s exclusion step.
but would be needed for a real `ModifyNP`+QID-alias path later.
