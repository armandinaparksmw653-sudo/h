-- | Pure rendering of a contextual-fiber/contraction result into the
-- same line-oriented, per-layer text format the `contextual-fiber`/
-- `contextual-contract` CLI commands (engine/app/Main.hs) have always
-- printed. Factored out so both that CLI and the whole-database report
-- tool (engine/app/Report.hs) share one rendering, rather than the tool
-- re-implementing a second, possibly drifting copy.
--
-- Two additions on top of the original CLI-only rendering, both aimed
-- at making a report self-sufficient for a reader who has not read the
-- rest of the codebase: 'reconstructSentence' rebuilds an approximate
-- English sentence directly from the Context's own LexicalTree (the
-- same lexicalized anchors the formal checker itself verifies against,
-- so this is a faithful rendering of what was actually checked, not a
-- separately-maintained, possibly-drifting transcription); and every
-- EntityId is now rendered with its real label from the snapshot
-- (falling back to the bare id if the snapshot has none), so a reader
-- sees "University of Waterloo (Q1049470)", not just "Q1049470".
module Metonymy.Report
  ( renderFiberReport
  , renderContractionReport
  , reconstructSentence
  ) where

import Data.List (sortOn)
import Metonymy.Contextual
import Metonymy.ContextualChecked (ContextualContraction (..))
import Metonymy.Ontology (KnowledgeBase, entityLabel, lookupEntity)
import Metonymy.Types

-- | Every lexical anchor in a tree, in the order they appear in the
-- source text (by start offset) -- the same anchors validateContext
-- already requires to have valid, non-overlapping-with-nothing spans.
allAnchors :: LexicalTree -> [LexicalAnchor]
allAnchors (LexicalLeaf anchor _) = [anchor]
allAnchors (LexicalApply _ children) = concatMap allAnchors children

-- | An approximate rendering of the sentence a Context's LexicalTree
-- was built from: every anchor's surface form, in source order. Not a
-- guarantee of grammatical, publication-quality English (a hand-built
-- tree can anchor a simplified paraphrase of the real corpus sentence,
-- as most flagship examples' module docstrings already say plainly),
-- but always a faithful rendering of what the tower actually
-- lexicalized and checked -- never invented or looked up separately.
reconstructSentence :: Context -> String
reconstructSentence context =
  unwords (map anchorSurface (sortOn anchorStart (allAnchors (contextTree context))))

labelFor :: KnowledgeBase -> EntityId -> String
labelFor kb identifier =
  case lookupEntity kb identifier of
    Just info -> entityLabel info <> " (" <> unEntityId identifier <> ")"
    Nothing -> unEntityId identifier

renderFiberReport :: Bool -> KnowledgeBase -> Context -> [FiberStage] -> [String]
renderFiberReport formalFiltering kb context stages =
  [ "sentence=" <> show (reconstructSentence context)
  , "source="
      <> labelFor kb (contextSource context)
      <> " action="
      <> contextAction context
      <> " role="
      <> show (contextRole context)
  ]
    <> concatMap (renderStage formalFiltering kb) stages

renderStage :: Bool -> KnowledgeBase -> FiberStage -> [String]
renderStage formalFiltering kb stage =
  [ "stage="
      <> show (stageIndex stage)
      <> " constraint="
      <> maybe "graph-related" renderConstraint (stageConstraint stage)
  , "  survivors="
      <> show (map (labelFor kb . fineTarget . contextualFineMeaning) (stageCandidates stage))
  , "  agda-layer-check="
      <> if formalFiltering then "true" else "disabled"
  ]
    <> map (("  obstruction=" <>) . show) (stageObstructions stage)
    <> case stageConstraint stage of
      Just constraint
        | payloadIsPreference (constraintPayload constraint) ->
            [ "  preferred="
                <> show
                  ( map
                      (labelFor kb . fineTarget . contextualFineMeaning)
                      (stagePreferredCandidates stage)
                  )
            ]
              <> map
                (("  preference-miss=" <>) . show)
                (stagePreferenceMisses stage)
      _ -> []

renderConstraint :: ContextConstraint -> String
renderConstraint constraint =
  show (constraintPayload constraint)
    <> "@"
    <> anchorLemma (constraintOrigin constraint)

renderContractionReport :: Bool -> KnowledgeBase -> ContextualContraction -> [String]
renderContractionReport formalFiltering kb result =
  [ "contract="
      <> labelFor kb (contractionTarget result)
      <> " -> "
      <> labelFor kb (contractionSource result)
      <> " safety="
      <> contractionSafety result
  ]
    <> concatMap (renderContractionStage formalFiltering kb) (contractionStages result)

renderContractionStage :: Bool -> KnowledgeBase -> FiberStage -> [String]
renderContractionStage formalFiltering kb stage =
  [ "stage="
      <> show (stageIndex stage)
      <> " constraint="
      <> maybe "graph-related" renderConstraint (stageConstraint stage)
  , "  survivors="
      <> show (map (labelFor kb) (stageTargets stage))
  , "  agda-layer-check="
      <> if formalFiltering then "true" else "disabled"
  ]
    <> case stageConstraint stage of
      Just constraint
        | payloadIsPreference (constraintPayload constraint) ->
            [ "  preferred="
                <> show
                  ( map
                      (labelFor kb . fineTarget . contextualFineMeaning)
                      (stagePreferredCandidates stage)
                  )
            ]
      _ -> []
