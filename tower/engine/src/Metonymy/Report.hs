-- | Pure rendering of a contextual-fiber/contraction result into the
-- same line-oriented, per-layer text format the `contextual-fiber`/
-- `contextual-contract` CLI commands (engine/app/Main.hs) have always
-- printed. Factored out so both that CLI and the whole-database report
-- tool (engine/app/Report.hs) share one rendering, rather than the tool
-- re-implementing a second, possibly drifting copy.
module Metonymy.Report
  ( renderFiberReport
  , renderContractionReport
  ) where

import Metonymy.Contextual
import Metonymy.ContextualChecked (ContextualContraction (..))
import Metonymy.Types

renderFiberReport :: Bool -> Context -> [FiberStage] -> [String]
renderFiberReport formalFiltering context stages =
  [ "source="
      <> show (contextSource context)
      <> " action="
      <> contextAction context
      <> " role="
      <> show (contextRole context)
  ]
    <> concatMap (renderStage formalFiltering) stages

renderStage :: Bool -> FiberStage -> [String]
renderStage formalFiltering stage =
  [ "stage="
      <> show (stageIndex stage)
      <> " constraint="
      <> maybe "graph-related" renderConstraint (stageConstraint stage)
  , "  survivors="
      <> show (map (fineTarget . contextualFineMeaning) (stageCandidates stage))
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
                      (fineTarget . contextualFineMeaning)
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

renderContractionReport :: Bool -> ContextualContraction -> [String]
renderContractionReport formalFiltering result =
  [ "contract="
      <> show (contractionTarget result)
      <> " -> "
      <> show (contractionSource result)
      <> " safety="
      <> contractionSafety result
  ]
    <> concatMap (renderContractionStage formalFiltering) (contractionStages result)

renderContractionStage :: Bool -> FiberStage -> [String]
renderContractionStage formalFiltering stage =
  [ "stage="
      <> show (stageIndex stage)
      <> " constraint="
      <> maybe "graph-related" renderConstraint (stageConstraint stage)
  , "  survivors="
      <> show (stageTargets stage)
  , "  agda-layer-check="
      <> if formalFiltering then "true" else "disabled"
  ]
    <> case stageConstraint stage of
      Just constraint
        | payloadIsPreference (constraintPayload constraint) ->
            [ "  preferred="
                <> show
                  ( map
                      (fineTarget . contextualFineMeaning)
                      (stagePreferredCandidates stage)
                  )
            ]
      _ -> []
