# Repository structure

Three folders, each with one job.

## `formal-verification/`

The machine-checked mathematical core: 25 Cubical Agda modules, the
executable checker the engine links against, and the manifest/check
script that guard against silent regression (no `postulate`, `--safe`
mode). Start at `formal-verification/OVERVIEW.md` for a clean,
non-chronological summary of what's proven, or
`formal-verification/Metonymy/THEOREMS.md` for the exact statement and
Agda witness of every claim.

## `tower/`

The main workflow: the Haskell engine (`tower/engine/`) implementing the
lexicalized contextual-fiber tower, the curated 123-example database it
resolves against (`tower/data/`), and `metonymy-report` — the tool that
runs every example through the real, Agda-checked apparatus and prints
its per-layer resolution. See `tower/README.md`.

## `auxiliary/`

Everything that supports the two folders above without being part of
the publication-critical path: the Python data-preparation pipeline
(`auxiliary/scripts/` — VerbNet/WordNet/FrameNet import, GF lexicon
generation, the Stanza-based automatic scenario proposer), the GF
grammar sources (`auxiliary/grammar/`), the broader data files the
pipeline consumes (`auxiliary/data/`), small real-corpus regression
fixtures (`auxiliary/evaluation/pilot-*`, `auxiliary/evaluation/
qid-fiber/`), and the Python test suite for all of it
(`auxiliary/tests/`). None of this needs to compile or check for
`formal-verification/` or `tower/` to be valid.

## Root-level orchestration

`Makefile`, `cabal.project`, and `metonymy.agda-lib` tie the three
folders together (their paths point into `formal-verification/` and
`tower/engine/`) rather than living inside either folder, so one
`make verify` or `./scripts/reproduce.sh` can drive the whole pipeline
from one place. `scripts/reproduce.sh` and `scripts/bootstrap.sh` are
the two orchestration entry points CI actually calls; everything else
lives under `auxiliary/scripts/`.

## `trash/`

Retired code and data, kept rather than deleted (git history alone is
not enough — this makes "what did we decide not to keep, and why"
discoverable without spelunking commits). Most recently: `evaluation/
contextual-multidomain/` (a large-scale automatic-pipeline benchmark
that self-documented its own results as "not statistically
meaningful") and the two `Makefile` targets that depended on it,
`contextual-corpus-test`/`contextual-ablations` — removed from the
main CI chain (`scripts/reproduce.sh`) on 2026-09-26. The underlying
`wikidata-openalex-snapshot` and `run_automatic_contextual_pipeline.py`
stayed in `auxiliary/` — that snapshot and pipeline are legitimate,
still-tested infrastructure (used by the small, real `pilot-curated-
evaluation.yml`/`pilot-decode-evaluation.yml` workflows); only the
specific flawed benchmark dataset built on top of them was retired.

## Verification

The only source of truth for whether Haskell/Agda actually compile and
check is real CI (`.github/workflows/ci.yml`) — there is no local
toolchain in this development environment. `ci.yml` runs
`scripts/reproduce.sh`, which now ends with `make report`: every one
of the 123 curated examples is run through the real, Agda-checked
tower and its per-layer breakdown printed, as part of the mandatory
verification chain, not a separate opt-in step.
