module Main where

import Control.Monad (unless)
import Data.List (find, isPrefixOf, sort)
import Metonymy.Contextual
import Metonymy.ContextualChecked
import Metonymy.ContextSpec
import Metonymy.Cathedrals
import Metonymy.ContainerContent
import Metonymy.Elaborator
import Metonymy.GF
import Metonymy.MoldeFK
import Metonymy.Snapshot
import Metonymy.SyntheticTowers
import Metonymy.Types
import Metonymy.Waterloo
import System.Exit (exitFailure)

main :: IO ()
main = do
  (waterlooSnapshot, waterlooRules) <-
    loadSnapshot "data/wikidata-qid-snapshot"
  waterlooAliases <- loadSnapshotAliases "data/wikidata-qid-snapshot"
  (syntheticTowersSnapshot, _) <-
    loadSnapshot "data/synthetic-towers-snapshot"
  (containerSnapshot, _) <-
    loadSnapshot "data/container-content-snapshot"
  loadedContextScenarios <-
    loadContextScenarios waterlooSnapshot "data/contextual-scenarios.tsv"
  let waterlooContext = waterlooContextFor waterlooSnapshot
      moldeContext = moldeContextFor waterlooSnapshot

  -- spaceBeforeCommas (Metonymy/GF.hs): confirmed by direct testing
  -- against a real gf.exe build (the official Windows release of GF
  -- 3.12, against this project's own pinned gf-rgl commit) that GF's
  -- default whitespace-only tokenizer treats "word," as one indivisible
  -- token, and no grammar-level device (BIND/SOFT_BIND included) can
  -- split it back apart at parse time -- every comma-using construct in
  -- grammar/MetonymyEng.gf (BecauseS/SBecauseS-family,
  -- ApposCommaPN1/ApposCommaPN2) needs the comma to already be its own
  -- token by the time it reaches GF's parser, exactly like real English
  -- commas already are whenever they happen to be preceded by a space.
  assert
    "spaceBeforeCommas inserts a space before a comma that lacks one"
    (spaceBeforeCommas "Waterloo, Ontario" == "Waterloo , Ontario")
  assert
    "spaceBeforeCommas is a no-op when a space already precedes the comma"
    (spaceBeforeCommas "Waterloo , Ontario" == "Waterloo , Ontario")
  assert
    "spaceBeforeCommas handles multiple commas in one sentence"
    ( spaceBeforeCommas "Because X, Y announces Z, W"
        == "Because X , Y announces Z , W"
    )
  assert
    "spaceBeforeCommas is a no-op on a sentence with no comma at all"
    (spaceBeforeCommas "Waterloo announces a programme" == "Waterloo announces a programme")
  assert
    "spaceBeforeCommas handles a comma as the very first character"
    (spaceBeforeCommas ",Waterloo" == ",Waterloo")

  -- spaceAroundParens (Metonymy/GF.hs): same tokenizer limitation as
  -- spaceBeforeCommas, confirmed the same way (a real local gf.exe
  -- build) -- "(HOLA)" with no spacing is one indivisible token that an
  -- unrelated existing rule (OpenPN3) silently absorbed instead of
  -- grammar/Metonymy.gf's own ParenNP ever matching it.
  assert
    "spaceAroundParens inserts a space before an unspaced opening paren"
    (spaceAroundParens "Foundation(HOLA)" == "Foundation (HOLA)")
  assert
    "spaceAroundParens inserts a space after an unspaced closing paren"
    (spaceAroundParens "(HOLA)based" == "(HOLA) based")
  assert
    "spaceAroundParens is a no-op when both sides are already spaced"
    (spaceAroundParens "Foundation ( HOLA ) based" == "Foundation ( HOLA ) based")
  assert
    "spaceAroundParens is a no-op on a sentence with no parens at all"
    (spaceAroundParens "Waterloo announces a programme" == "Waterloo announces a programme")

  assert
    "Waterloo tree elaborates with ordered lexical origins"
    ( case
        elaborateContext
          (snapshotHash waterlooSnapshot)
          (contextSource waterlooContext)
          "announce"
          SubjectHole
          waterlooTree of
        Right context ->
          map
            (\constraint -> (constraintOrigin constraint, constraintPayload constraint))
            (contextConstraints context)
            == map
              (\constraint -> (constraintOrigin constraint, constraintPayload constraint))
              (contextConstraints waterlooContext)
        Left _ -> False
    )
  assert
    "unsupported lexical construction fails closed"
    ( case
        elaborateContext
          (snapshotHash waterlooSnapshot)
          (contextSource waterlooContext)
          "announce"
          SubjectHole
          (LexicalApply "UnsupportedGFNode" []) of
        Left (UnsupportedConstruction _) -> True
        _ -> False
    )
  assert
    "GF application tree is lexicalized with concrete source spans"
    ( case
        lexicalizeGFTree
          "Waterloo announced programme"
          [ LexicalBinding "WaterlooGF" "waterloo" "Waterloo" []
          , LexicalBinding
              "AnnounceGF"
              "announce"
              "announced"
              [Requires (AnyOf [HasSort Animate, HasSort Organization])]
          , LexicalBinding "ProgrammeGF" "programme" "programme" []
          ]
          "Pred WaterlooGF (Compl AnnounceGF ProgrammeGF)" of
        Right tree ->
          case
              elaborateContext
                (snapshotHash waterlooSnapshot)
                (EntityId "Q639408")
                "announce"
                SubjectHole
                tree of
            Right context ->
              map
                (anchorStart . constraintOrigin)
                (contextConstraints context)
                == [9]
            Left _ -> False
        Left _ -> False
    )
  assert
    "GF quantified lexical constructor retains its noun and span"
    ( case
        lexicalizeGFTree
          "every student reads Tolstoy"
          [ LexicalBinding
              "EveryCN"
              "student"
              "student"
              [Requires (HasSort Human)]
          , LexicalBinding "Read" "read" "reads" []
          , LexicalBinding "Tolstoy" "tolstoy" "Tolstoy" []
          ]
          "Pred (EveryCN \"student\" \"students\") (Compl Read Tolstoy)" of
        Right tree ->
          case
              elaborateContext
                (snapshotHash waterlooSnapshot)
                (EntityId "Q639408")
                "read"
                SubjectHole
                tree of
            Right context ->
              case contextConstraints context of
                [constraint] ->
                  anchorStart (constraintOrigin constraint) == 6
                    && anchorSurface (constraintOrigin constraint) == "student"
                _ -> False
            Left _ -> False
        Left _ -> False
    )
  assert
    "snapshot rules include inverse institution projection"
    ( any
        ( \projection ->
            projectionRelation projection == InstitutionOf
              && projectionInverse projection
        )
        (relationProjections waterlooRules)
    )
  assert
    "snapshot alias layer resolves Waterloo to its QID"
    (lookup "Waterloo" waterlooAliases == Just (EntityId "Q639408"))
  assert
    "contextual scenario file has exactly the waterloo and molde rows"
    (length loadedContextScenarios == 2)
  assert
    "Waterloo contextual scenario is loaded from versioned data"
    ( case find ((== "waterloo") . contextScenarioName) loadedContextScenarios of
        Just scenario ->
          contextSource (contextScenarioContext scenario) == contextSource waterlooContext
            && contextAction (contextScenarioContext scenario) == contextAction waterlooContext
            && contextConstraints (contextScenarioContext scenario) == contextConstraints waterlooContext
        Nothing -> False
    )
  assert
    "Molde contextual scenario is loaded from versioned data"
    ( case find ((== "molde") . contextScenarioName) loadedContextScenarios of
        Just scenario ->
          contextSource (contextScenarioContext scenario) == contextSource moldeContext
            && contextAction (contextScenarioContext scenario) == contextAction moldeContext
            && contextConstraints (contextScenarioContext scenario) == contextConstraints moldeContext
        Nothing -> False
    )
  assert
    "tower rejects a context bound to another snapshot"
    ( contextualFiber
        waterlooSnapshot
        [InstitutionOf]
        1
        (waterlooContext {contextSnapshotHash = "forged"})
        == Left "snapshot-hash-mismatch"
    )

  case
      contextualFiber
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext of
    Left errorMessage -> do
      putStrLn ("FAIL: Waterloo contextual fiber: " <> errorMessage)
      exitFailure
    Right stages -> do
      assert "Waterloo fiber has one initial and two lexical stages" (length stages == 3)
      assert
        "Waterloo graph layer preserves all institution candidates"
        ( stageTargets (stages !! 0)
            == map EntityId ["Q1049470", "Q2004561", "Q7974219"]
        )
      assert
        "announce layer retains organization candidates"
        (stageTargets (stages !! 1) == stageTargets (stages !! 0))
      assert
        "physics layer retains only positively witnessed institutions"
        (stageTargets (stages !! 2) == map EntityId ["Q1049470", "Q2004561"])
      assert
        "contextual fiber is monotonically restricted"
        ( all
            (`elem` stageTargets (stages !! 0))
            (stageTargets (stages !! 1))
            && all
              (`elem` stageTargets (stages !! 1))
              (stageTargets (stages !! 2))
        )
      assert
        "Waterloo council has a precise missing-relation obstruction"
        ( case stageObstructions (stages !! 2) of
            [MissingRelation _ candidate Conducts target] ->
              candidate == EntityId "Q7974219" && target == EntityId "Q413"
            _ -> False
        )

  case
      contextualFiberChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext of
    Left errorMessage -> do
      putStrLn ("FAIL: Agda-checked Waterloo fiber: " <> errorMessage)
      exitFailure
    Right stages ->
      assert
        "Agda-checked Waterloo fiber matches the executable tower"
        (stageTargets (stages !! 2) == map EntityId ["Q1049470", "Q2004561"])

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext
        (EntityId "Q1049470") of
    Left message
      | "unsafe-contextual-contraction-non-singleton-fiber" `isPrefixOf` message ->
          assert "ambiguous Waterloo contraction is rejected" True
    other -> do
      putStrLn ("FAIL: expected unsafe Waterloo contraction, got " <> show other)
      exitFailure

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        waterlooContext
        (EntityId "Q7974219") of
    Left "explicit-target-not-in-final-fiber" ->
      assert "obstructed Waterloo council cannot contract" True
    other -> do
      putStrLn ("FAIL: expected missing council contraction, got " <> show other)
      exitFailure

  let uniqueWaterlooContext =
        waterlooContext
          { contextConstraints =
              contextConstraints waterlooContext
                <> [ ContextConstraint
                      (LexicalAnchor "Noun" "university" "university" 46 56)
                      (Requires (HasSort University))
                      "test:unique-university"
                   ]
          , contextRuleProvenance =
              contextRuleProvenance waterlooContext
                <> ["test:unique-university"]
          }
  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        uniqueWaterlooContext
        (EntityId "Q1049470") of
    Right result ->
      assert
        "unique Waterloo university fiber contracts to the source place"
        ( contractionSource result == EntityId "Q639408"
            && contractionTarget result == EntityId "Q1049470"
            && contractionSafety result == "unique-contextual-fiber"
        )
    Left errorMessage -> do
      putStrLn ("FAIL: unique Waterloo contraction: " <> errorMessage)
      exitFailure

  -- Real, three-signal tower: "Molde announced ... signed Kamara on loan
  -- for the ... season" (real WiMCor sentence, live-Wikidata-verified,
  -- see Metonymy.MoldeFK's module docstring). Unlike Waterloo, one
  -- signal (announce) and two signals (announce+season) both stay
  -- genuinely ambiguous between Molde FK and the real decoy Bjørset FK
  -- -- only the third (on loan, RequiresSome PlaysInLeague) narrows to
  -- the single correct candidate.
  case contextualFiber waterlooSnapshot [InstitutionOf] 1 moldeContext of
    Left errorMessage -> do
      putStrLn ("FAIL: Molde contextual fiber: " <> errorMessage)
      exitFailure
    Right stages -> do
      assert
        "Molde fiber has one initial and three constraint stages"
        (length stages == 4)
      assert
        "Molde graph layer finds both real Molde football clubs"
        ( sort (map unEntityId (stageTargets (stages !! 0)))
            == sort (map unEntityId [moldeFK, bjorsetFK])
        )
      assert
        "announce alone does not disambiguate (both are organizations)"
        (sort (map unEntityId (stageTargets (stages !! 1))) == sort (map unEntityId [moldeFK, bjorsetFK]))
      assert
        "season alone does not disambiguate (both are football clubs)"
        (sort (map unEntityId (stageTargets (stages !! 2))) == sort (map unEntityId [moldeFK, bjorsetFK]))
      assert
        "on loan narrows to the one club with a real league claim"
        (map unEntityId (stageTargets (stages !! 3)) == [unEntityId moldeFK])

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        moldeContext
        moldeFK of
    Right result ->
      assert
        "unique Molde FK fiber contracts to the source place (Agda-checked)"
        ( contractionSource result == moldeSource
            && contractionTarget result == moldeFK
            && contractionSafety result == "unique-contextual-fiber"
        )
    Left errorMessage -> do
      putStrLn ("FAIL: unique Molde FK contraction: " <> errorMessage)
      exitFailure

  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        moldeContext
        bjorsetFK of
    Left message
      | "explicit-target-not-in-final-fiber" `isPrefixOf` message ->
          assert "the real decoy Bjørset FK is correctly rejected" True
    other -> do
      putStrLn ("FAIL: expected Bjørset FK to be rejected, got " <> show other)
      exitFailure

  -- Two real, single-signal location-for-artifact examples: "Gloucester
  -- has a Norman nave..." and "the lady chapel of Ely..." (see
  -- Metonymy.Cathedrals). A live SPARQL check found no real ambiguity
  -- here (unlike Molde): each place has exactly one Q56242250-typed
  -- entity, so one Requires (HasSort Artifact) signal already narrows
  -- to the unique cathedral.
  mapM_
    ( \(label, context, expected) ->
        case
            contextualContractionChecked
              waterlooSnapshot
              [InstitutionOf]
              1
              context
              expected of
          Right result ->
            assert
              (label <> " contracts uniquely to its cathedral (Agda-checked)")
              (contractionTarget result == expected && contractionSafety result == "unique-contextual-fiber")
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("Gloucester -> Gloucester Cathedral", gloucesterContext waterlooSnapshot, gloucesterCathedral)
    , ("Ely -> Ely Cathedral", elyContext waterlooSnapshot, elyCathedral)
    ]

  -- Three real, corpus-attested container-for-content examples (ConMeC
  -- CONTAINER category -- see Metonymy.ContainerContent's module
  -- docstring). A different transfer mechanism from location-for-
  -- institution: each container has exactly one real content edge, so
  -- the tower narrows to a unique, Agda-checked candidate through the
  -- graph walk alone, with no extra Requires signal needed.
  mapM_
    ( \(label, context, expected) ->
        case contextualFiberChecked containerSnapshot [Contains] 1 context of
          Right stages ->
            assert
              (label <> " narrows to its one real content, Agda-checked")
              (map unEntityId (stageTargets (last stages)) == [unEntityId expected])
          Left errorMessage -> do
            putStrLn ("FAIL: " <> label <> ": " <> errorMessage)
            exitFailure
    )
    [ ("glass -> rum", glassContext containerSnapshot, rumEntity)
    , ("carton -> milk", cartonContext containerSnapshot, milkEntity)
    , ("pack -> beer", packContext containerSnapshot, beerEntity)
    ]

  mapM_ (assertSyntheticTower syntheticTowersSnapshot) towers

  putStrLn "all tests passed"

assert :: String -> Bool -> IO ()
assert label condition =
  unless condition $ do
    putStrLn ("FAIL: " <> label)
    exitFailure

-- | Runs one fictional tower (data/synthetic-towers-snapshot,
-- Metonymy.SyntheticTowers) through the real Agda-checked contextual
-- pipeline (Metonymy.ContextualChecked), the same functions the real
-- Waterloo tests above exercise. Five assertions, all through the
-- compiled Agda checker where a fiber is actually computed:
--   1/2. each of the tower's two Sorts ALONE is genuinely ambiguous
--        (two survivors) -- so a later unique narrowing is a real
--        conjunction, not one signal that already sufficed alone.
--   3. both Sorts as Prefers (data/contextual-context-triggers.json's
--      actual, shipped strength for all 78 new entries) does NOT narrow
--      the fiber -- Prefers ranks, never filters
--      (Metonymy.Contextual.applyConstraints).
--   4. both Sorts as Requires (an explicitly hypothetical "if
--      individually verified and promoted" variant, not today's
--      dictionary) narrows to exactly the one candidate sharing both
--      Sorts, and Agda-checked contraction reports
--      "unique-contextual-fiber".
--   5. under that same Requires-both context, a candidate with only ONE
--      of the two Sorts is correctly rejected as a contraction target.
assertSyntheticTower :: Snapshot -> TowerFixture -> IO ()
assertSyntheticTower snapshot fixture = do
  assertFiberTargets
    (label <> ": " <> show firstSort <> " alone is ambiguous")
    (towerContextSingle snapshot fixture firstSort)
    [towerBothCandidate fixture, towerFirstOnlyCandidate fixture]

  assertFiberTargets
    (label <> ": " <> show secondSort <> " alone is ambiguous")
    (towerContextSingle snapshot fixture secondSort)
    [towerBothCandidate fixture, towerSecondOnlyCandidate fixture]

  assertFiberTargets
    (label <> ": prefers-both does not narrow (matches shipped dictionary strength)")
    (towerContextPreferring snapshot fixture)
    [ towerBothCandidate fixture
    , towerFirstOnlyCandidate fixture
    , towerSecondOnlyCandidate fixture
    , towerDecoyCandidate fixture
    ]

  case
      contextualContractionChecked
        snapshot
        [InstitutionOf]
        1
        (towerContextRequiring snapshot fixture)
        (towerBothCandidate fixture) of
    Right result ->
      assert
        (label <> ": requires-both narrows uniquely to the shared-sort candidate (Agda-checked)")
        ( contractionSource result == towerSource fixture
            && contractionTarget result == towerBothCandidate fixture
            && contractionSafety result == "unique-contextual-fiber"
        )
    Left errorMessage -> do
      putStrLn ("FAIL: " <> label <> " requires-both unique contraction: " <> errorMessage)
      exitFailure

  case
      contextualContractionChecked
        snapshot
        [InstitutionOf]
        1
        (towerContextRequiring snapshot fixture)
        (towerFirstOnlyCandidate fixture) of
    Left message
      | "explicit-target-not-in-final-fiber" `isPrefixOf` message ->
          assert (label <> ": requires-both correctly rejects a single-sort candidate") True
    other -> do
      putStrLn
        ( "FAIL: "
            <> label
            <> " expected rejection of the single-sort candidate, got "
            <> show other
        )
      exitFailure
  where
    label = towerLabel fixture
    firstSort = towerFirstSort fixture
    secondSort = towerSecondSort fixture

    assertFiberTargets :: String -> Context -> [EntityId] -> IO ()
    assertFiberTargets assertionLabel context expected =
      case contextualFiberChecked snapshot [InstitutionOf] 1 context of
        Right stages ->
          assert
            assertionLabel
            (sortEntityIds (stageTargets (last stages)) == sortEntityIds expected)
        Left errorMessage -> do
          putStrLn ("FAIL: " <> assertionLabel <> ": " <> errorMessage)
          exitFailure

    sortEntityIds :: [EntityId] -> [String]
    sortEntityIds = sort . map unEntityId

