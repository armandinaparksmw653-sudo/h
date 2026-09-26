-- | The first real, corpus-attested Cause-for-effect example: "A trumpet
-- is also heard in the song right after this line is sung" (real ConMeC
-- METONYMIC/CAUSER-category sentence, target word "trumpet" -- the
-- instrument standing for the sound it causes), simplified to "he hears
-- a trumpet".
--
-- A fourth distinct transfer mechanism, structurally different from
-- location-for-institution (InstitutionOf/GovernedBy),
-- container-for-content/producer-for-product (Contains/Produces,
-- Metonymy.ContainerContent), and part-for-whole (AffiliatedWith,
-- Metonymy.PartWhole): here the source (the cause) is not contained by,
-- produced by, nor affiliated with the target, it *causes* it -- reuses
-- the already-defined but previously unused Causes relation. Like the
-- other ContainerContent-family sources, "a trumpet" and "the sound of
-- the trumpet" are not independently Wikidata-linkable as the specific
-- referents of this one sentence, so this is a small, hand-built local
-- graph in data/container-content-snapshot, the same honesty tier as
-- the existing examples there. Exactly one real causal edge (no
-- decoys), so the tower narrows to a unique candidate through the graph
-- walk alone, with no extra Requires signal needed.
module Metonymy.CauseEffect
  ( trumpetContext
  , trumpetSource
  , trumpetSound
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

trumpetContext :: Snapshot -> Context
trumpetContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "hear" "hears" 3 8)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" "trumpet" "trumpet" 11 18) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = trumpetSource
    , contextAction = "hear"
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "hear" "hears" 3 8)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

trumpetSource, trumpetSound :: EntityId
trumpetSource = EntityId "LOCAL_TRUMPET"
trumpetSound = EntityId "LOCAL_TRUMPET_SOUND"
