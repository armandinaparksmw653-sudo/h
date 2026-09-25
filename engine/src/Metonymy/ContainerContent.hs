-- | Four real, corpus-attested examples of two different transfer
-- mechanisms -- container-for-content (ConMeC CONTAINER category) and
-- producer-for-product (ConMeC PRODUCER category), METONYMIC label in
-- both -- neither of which is the location-for-institution family
-- (Waterloo/Molde/Cupertino): the source is not a real-world,
-- independently identifiable entity (a glass/carton/six-pack/orchestra
-- in one narrative has no Wikidata QID), so each is a small, hand-built
-- local graph (same honesty tier as Metonymy.SyntheticTowers), just
-- grounded in real sentences rather than invented ones. Each source has
-- exactly one real target edge (no decoys), so the tower narrows to a
-- unique candidate through the graph walk alone, with no extra Requires
-- signal needed -- the same "zero extra constraints, the graph topology
-- alone already disambiguates" shape as the base WiMCor pilot-decode
-- examples (Pomona/Leicester).
--
-- Real source sentences, simplified to the same representative-tree
-- style already used for Molde/Waterloo:
--   "He says 'I've never tasted rum', downs the glass..." -> "he drinks
--   the glass" (glass -> Contains -> rum)
--   "He lands next to some milk... drinks the entire carton." -> "he
--   drinks the carton" (carton -> Contains -> milk)
--   "Detective Rust Cohle... drinks a six pack..." -> "he drinks a pack"
--   (pack -> Contains -> beer)
--   "Duke Ellington made a 1935 visit to hear Wheatley's orchestra." ->
--   "he hears the orchestra" (orchestra -> Produces -> symphony; "Hear"
--   is a real V2, generated from data/predicates.tsv into
--   grammar/GeneratedMetonymyEng.gf, verified there against the local
--   gf.exe/pinned gf-rgl build -- the base grammar/MetonymyEng.gf this
--   module's other three contexts use does not itself declare it)
module Metonymy.ContainerContent
  ( glassContext
  , cartonContext
  , packContext
  , orchestraContext
  , glassEntity
  , rumEntity
  , cartonEntity
  , milkEntity
  , packEntity
  , beerEntity
  , orchestraEntity
  , symphonyEntity
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

containerContext ::
  Snapshot -> EntityId -> String -> Int -> Int -> Context
containerContext snapshot source noun start end =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "drink" "drinks" 3 9)
                  [Prefers (HasSort Entity)]
              , LexicalLeaf (anchor "Noun" noun noun start end) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
    , contextAction = "drink"
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "drink" "drinks" 3 9)
            (Prefers (HasSort Entity))
            "local:selectional-lexicon"
        ]
    , contextRuleProvenance = ["local:selectional-lexicon"]
    }

glassContext, cartonContext, packContext :: Snapshot -> Context
glassContext snapshot = containerContext snapshot glassEntity "glass" 14 19
cartonContext snapshot = containerContext snapshot cartonEntity "carton" 14 20
packContext snapshot = containerContext snapshot packEntity "pack" 12 16

-- "he hears the orchestra": orchestra -> Produces -> symphony
orchestraContext :: Snapshot -> Context
orchestraContext snapshot =
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
              , LexicalLeaf (anchor "Noun" "orchestra" "orchestra" 13 22) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = orchestraEntity
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

glassEntity, rumEntity, cartonEntity, milkEntity, packEntity, beerEntity :: EntityId
glassEntity = EntityId "LOCAL_GLASS"
rumEntity = EntityId "LOCAL_RUM"
cartonEntity = EntityId "LOCAL_CARTON"
milkEntity = EntityId "LOCAL_MILK"
packEntity = EntityId "LOCAL_PACK"
beerEntity = EntityId "LOCAL_BEER"

orchestraEntity, symphonyEntity :: EntityId
orchestraEntity = EntityId "LOCAL_ORCHESTRA"
symphonyEntity = EntityId "LOCAL_SYMPHONY"
