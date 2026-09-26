-- | The main-workflow entry point: runs the curated example database
-- through the real, Agda-checked formal apparatus and prints the
-- per-layer tower breakdown for every example, one after another.
--
-- Covers 122 of the 123 curated examples individually: the 51
-- Haskell-module-driven ones from Metonymy.ExampleDatabase (14
-- flagship + 37 scale-tier -- see that module's docstring for the one
-- entry, the Rijeka+glass composition example, deliberately left out)
-- plus the 72 TSV-driven scale-tier scenarios from
-- tower/data/contextual-scenarios.tsv, loaded exactly as the
-- `contextual-fiber` CLI command already does via Metonymy.ContextSpec.
--
-- Usage: metonymy-report [--output FILE]
-- With --output, the report is written to FILE (and a one-line
-- "wrote N examples to FILE" note is still printed to stdout); without
-- it, the whole report goes to stdout.
module Main where

import Control.Monad (forM_)
import Metonymy.ContextSpec
import Metonymy.Contextual
import Metonymy.ContextualChecked
import Metonymy.ExampleDatabase
import Metonymy.Report (renderFiberReport)
import Metonymy.Snapshot
import System.Environment (getArgs)
import System.IO (IOMode (WriteMode), hPutStrLn, withFile)

main :: IO ()
main = do
  arguments <- getArgs
  (qidSnapshot, _) <- loadSnapshot "tower/data/wikidata-qid-snapshot"
  (containerSnapshot, _) <- loadSnapshot "tower/data/container-content-snapshot"
  scenarios <-
    loadContextScenarios qidSnapshot "tower/data/contextual-scenarios.tsv"
  let haskellReports = map (renderExample qidSnapshot containerSnapshot) exampleDatabase
      tsvReports = map (renderScenario qidSnapshot) scenarios
      allReports = haskellReports <> tsvReports
      totalCount = length allReports
  case outputPath arguments of
    Nothing -> forM_ allReports putStrLn
    Just path -> do
      withFile path WriteMode $ \handle ->
        forM_ allReports (hPutStrLn handle)
      putStrLn
        ( "wrote "
            <> show totalCount
            <> " examples to "
            <> path
        )

renderExample :: Snapshot -> Snapshot -> ExampleEntry -> String
renderExample qidSnapshot containerSnapshot entryValue =
  unlines
    ( ("=== " <> exampleName entryValue <> " (" <> exampleTier entryValue <> ") ===")
        : case result of
          Left message -> ["ERROR: " <> message]
          Right lines_ -> lines_
    )
  where
    snapshot = exampleSnapshotOf qidSnapshot containerSnapshot entryValue
    context = exampleContextOf entryValue snapshot
    relations = exampleRelations entryValue
    depth = exampleMaxDepth entryValue

    result =
      case exampleContractionTarget entryValue of
        Nothing ->
          renderFiberReport True context
            <$> contextualFiberChecked snapshot relations depth context
        Just target ->
          case contextualContractionChecked snapshot relations depth context target of
            Left message ->
              Right
                [ "attempted contraction to " <> show target <> ": REJECTED (" <> message <> ")"
                ]
            Right _ ->
              Right
                [ "attempted contraction to " <> show target <> ": unexpectedly ACCEPTED"
                ]

renderScenario :: Snapshot -> ContextScenario -> String
renderScenario snapshot scenario =
  unlines
    ( ("=== " <> contextScenarioName scenario <> " (scale, TSV) ===")
        : case result of
          Left message -> ["ERROR: " <> message]
          Right lines_ -> lines_
    )
  where
    context = contextScenarioContext scenario
    result =
      renderFiberReport True context
        <$> contextualFiberChecked
          snapshot
          (contextScenarioRelations scenario)
          (contextScenarioMaxDepth scenario)
          context

outputPath :: [String] -> Maybe String
outputPath ("--output" : path : _) = Just path
outputPath (_ : rest) = outputPath rest
outputPath [] = Nothing
