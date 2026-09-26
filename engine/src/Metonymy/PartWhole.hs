-- | The first real, corpus-attested Part-for-whole (synecdoche) example:
-- "Egyptian artillery shelled the Israeli bridge over the canal on the
-- morning of October 17, scoring several hits" (real ConMeC METONYMIC/
-- POSSESSED-category sentence, target word "artillery" -- the weapon
-- type standing for the military branch/unit that operates it),
-- simplified to "artillery shelled a bridge".
--
-- A third distinct transfer mechanism, structurally different from both
-- location-for-institution (Waterloo/Molde/Eswatini, via InstitutionOf/
-- GovernedBy) and container-for-content/producer-for-product
-- (Metonymy.ContainerContent, via Contains/Produces): here the source
-- (the part/instrument) is affiliated with, not contained by or a
-- producer of, the whole it stands for -- reuses the already-defined
-- but previously unused AffiliatedWith relation, walked forward from
-- the part to the whole. Like the ContainerContent sources, "artillery"
-- and "the Egyptian military" are not independently Wikidata-linkable
-- as the specific referents of this one sentence (there is no distinct
-- QID for "the Egyptian artillery corps that shelled this bridge on
-- this day"), so this is a small, hand-built local graph in
-- data/container-content-snapshot, the same honesty tier as the
-- existing container/producer examples there, just grounded in this
-- real sentence rather than invented. Exactly one real affiliation edge
-- (no decoys), so the tower narrows to a unique candidate through the
-- graph walk alone, with no extra Requires signal needed -- the same
-- "zero extra constraints, the graph topology alone already
-- disambiguates" shape as glassContext/cartonContext/packContext.
module Metonymy.PartWhole
  ( artilleryContext
  , artillerySource
  , egyptianMilitary
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

artilleryContext :: Snapshot -> Context
artilleryContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "Noun" "artillery" "artillery" 0 9) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "shell" "shelled" 10 17)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" "bridge" "bridge" 22 28) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = artillerySource
    , contextAction = "shell"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "shell" "shelled" 10 17)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

artillerySource, egyptianMilitary :: EntityId
artillerySource = EntityId "LOCAL_ARTILLERY"
egyptianMilitary = EntityId "LOCAL_EGYPTIAN_MILITARY"
