module Main where

import Control.Monad (unless)
import Data.List (find, isPrefixOf, sort)
import Metonymy.Contextual
import Metonymy.ContextualChecked
import Metonymy.ContextSpec
import Metonymy.Cathedrals
import Metonymy.Eswatini
import Metonymy.Rijeka
import Metonymy.Busan
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
    "contextual scenario file has the expected number of rows"
    (length loadedContextScenarios == 8)
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

  -- Six real, single-signal WiMCor University-of-X examples, loaded
  -- straight from data/contextual-scenarios.tsv rather than individual
  -- Haskell modules -- the scale tier: minimal curated snapshot (the one
  -- real InstitutionOf edge each, no per-city decoy search the way
  -- Molde/Rijeka got), so uniqueness here reflects that curation choice,
  -- not a claim that no other organization exists in that city on real
  -- Wikidata. Two of the six needed their real P31 values registered as
  -- University (Q875538 "public university", Q38723 "higher education
  -- institution") rather than assuming Q3918 -- checked via live
  -- wbgetentities, not assumed uniform across all six.
  mapM_
    ( \(name, university) ->
        case find ((== name) . contextScenarioName) loadedContextScenarios of
          Nothing -> do
            putStrLn ("FAIL: scenario not loaded: " <> name)
            exitFailure
          Just scenario ->
            case
                contextualFiberChecked
                  waterlooSnapshot
                  (contextScenarioRelations scenario)
                  (contextScenarioMaxDepth scenario)
                  (contextScenarioContext scenario) of
              Right stages ->
                assert
                  (name <> " contracts uniquely to its real university, Agda-checked")
                  (map unEntityId (stageTargets (last stages)) == [university])
              Left errorMessage -> do
                putStrLn ("FAIL: " <> name <> ": " <> errorMessage)
                exitFailure
    )
    [ ("houston-university", "Q1472358")
    , ("exeter-university", "Q1414861")
    , ("rochester-university", "Q149990")
    , ("durham-university", "Q458393")
    , ("bath-university", "Q1422458")
    , ("derby-university", "Q3183295")
    ]

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

  -- Real two-hop walk (maxDepth=2), genuinely untested at that depth
  -- until now: Waterloo -InstitutionOf(inverse P131)-> University of
  -- Waterloo -InstitutionOf(inverse P361, newly registered)-> Institute
  -- for Quantum Computing (Q3799227, real P361 "part of" claim, already
  -- P31=Q31855 ResearchInstitution -- the same QID already registered
  -- from Perimeter Institute). Reuses InstitutionOf rather than the
  -- existing AffiliatedWith projection: P361/P749's own AffiliatedWith
  -- registration is forward (keeps the claim's own child->parent
  -- direction, IQC->UWaterloo), the opposite of what a source->target
  -- graph walk here needs (UWaterloo->IQC) -- caught by a real CI
  -- failure on the first attempt, not assumed correct in advance. The
  -- initial graph layer at depth 2 finds this fourth, more-distant real
  -- candidate that depth 1 cannot reach; the existing physics/Conducts
  -- constraint still correctly excludes it in the end (it has no P101
  -- claim at all), so going deeper finds more raw candidates without
  -- losing precision.
  case
      contextualFiberChecked
        waterlooSnapshot
        [InstitutionOf]
        2
        waterlooContext of
    Left errorMessage -> do
      putStrLn ("FAIL: depth-2 Waterloo fiber: " <> errorMessage)
      exitFailure
    Right stages -> do
      assert
        "depth-2 graph layer reaches the real second-hop candidate that depth 1 cannot"
        ( sort (map unEntityId (stageTargets (stages !! 0)))
            == sort (map unEntityId [EntityId "Q1049470", EntityId "Q2004561", EntityId "Q3799227", EntityId "Q7974219"])
        )
      assert
        "the existing physics constraint still excludes the deeper candidate correctly"
        (stageTargets (last stages) == map EntityId ["Q1049470", "Q2004561"])

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

  -- Real, single-signal location-for-event example (see Metonymy.Busan):
  -- the WiMCor EVENT medium had by far the fewest usable subject-position
  -- candidates this session (422 rows, almost none subject-position or
  -- reachable by a verb the grammar already had) -- this is the one real
  -- example found and verified in that domain.
  case
      contextualContractionChecked
        waterlooSnapshot
        [InstitutionOf]
        1
        (busanContext waterlooSnapshot)
        busanFilmFestival of
    Right result ->
      assert
        "Busan contracts uniquely to its film festival (Agda-checked)"
        (contractionTarget result == busanFilmFestival && contractionSafety result == "unique-contextual-fiber")
    Left errorMessage -> do
      putStrLn ("FAIL: Busan contraction: " <> errorMessage)
      exitFailure

  -- Real Government-domain example: "The cabinet of eSwatini was placed
  -- in quarantine..." (see Metonymy.Eswatini). Requires (HasSort
  -- Government) narrows the real 88-entity P1001 neighborhood down to
  -- the two real cabinet formations on record; unlike Molde, no further
  -- lexical signal in this sentence distinguishes which one (the real
  -- distinguishing fact is a date, not a word), so this stays an honest
  -- two-candidate result, the same shape as Waterloo.
  case contextualFiberChecked waterlooSnapshot [GovernedBy] 1 (eswatiniContext waterlooSnapshot) of
    Right stages ->
      assert
        "Eswatini's cabinet narrows to the two real cabinet formations, Agda-checked"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [ambroseMandvuloDlaminiCabinet, russellDlaminiCabinet])
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Eswatini cabinet fiber: " <> errorMessage)
      exitFailure

  -- Second real TEAM tower (see Metonymy.Rijeka): unlike Molde, no
  -- lexical signal here distinguishes HNK Rijeka from the real decoy NK
  -- Orijent, so this stays an honest two-candidate result too.
  case contextualFiberChecked waterlooSnapshot [InstitutionOf] 1 (rijekaContext waterlooSnapshot) of
    Right stages ->
      assert
        "Rijeka's season signal narrows to the two real football clubs, Agda-checked"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [hnkRijeka, nkOrijent])
        )
    Left errorMessage -> do
      putStrLn ("FAIL: Rijeka fiber: " <> errorMessage)
      exitFailure

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

  case contextualFiberChecked containerSnapshot [Produces] 1 (orchestraContext containerSnapshot) of
    Right stages ->
      assert
        "orchestra -> symphony narrows to its one real product, Agda-checked"
        (map unEntityId (stageTargets (last stages)) == [unEntityId symphonyEntity])
    Left errorMessage -> do
      putStrLn ("FAIL: orchestra -> symphony: " <> errorMessage)
      exitFailure

  -- Honest reject tests for the three newer, non-location-for-
  -- institution mechanisms (Container, Producer, Government): each
  -- graph only has the one real edge from its own source, so asking the
  -- tower to contract to an entity from a DIFFERENT source's graph is
  -- correctly refused, the same "explicit-target-not-in-final-fiber"
  -- shape already exercised for Bjørset FK and Waterloo City Council.
  mapM_
    ( \(label, snapshot, relations, context, wrongTarget) ->
        case contextualContractionChecked snapshot relations 1 context wrongTarget of
          Left message
            | "explicit-target-not-in-final-fiber" `isPrefixOf` message ->
                assert label True
          other -> do
            putStrLn ("FAIL: " <> label <> ": expected rejection, got " <> show other)
            exitFailure
    )
    [ ( "glass correctly rejects milk (belongs to carton, not glass)"
      , containerSnapshot
      , [Contains]
      , glassContext containerSnapshot
      , milkEntity
      )
    , ( "orchestra correctly rejects rum (belongs to a glass, not the orchestra)"
      , containerSnapshot
      , [Produces]
      , orchestraContext containerSnapshot
      , rumEntity
      )
    , ( "Eswatini's cabinet correctly rejects an unrelated entity (Gloucester Cathedral)"
      , waterlooSnapshot
      , [GovernedBy]
      , eswatiniContext waterlooSnapshot
      , gloucesterCathedral
      )
    ]

  -- Compositionality: two different transfer mechanisms, drawing on two
  -- different snapshots (Rijeka's location-for-institution via
  -- waterlooSnapshot, "glass" 's container-for-content via
  -- containerSnapshot), each independently and correctly resolved from
  -- ONE real combined sentence: "Rijeka announces a season and he drinks
  -- the glass". Nothing in the tower shares state across a Context
  -- value (each is a pure record), so this mainly documents that two
  -- lexical anchors sitting in the same real sentence text do not
  -- interfere -- but it is the first time two mechanisms have actually
  -- been run from a single shared sentence rather than two unrelated
  -- ones.
  let compositionRijekaContext =
        Context
          { contextTree =
              LexicalApply
                "AndS"
                [ LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "OpenPN" "rijeka" "Rijeka" 0 6) []
                    , LexicalApply
                        "Compl"
                        [ LexicalLeaf
                            (LexicalAnchor "Verb" "announce" "announces" 7 16)
                            [Requires (AnyOf [HasSort Animate, HasSort Organization])]
                        , LexicalLeaf (LexicalAnchor "Noun" "season" "season" 19 25) []
                        ]
                    ]
                , LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "HePN" "he" "he" 30 32) []
                    , LexicalApply
                        "Compl"
                        [LexicalLeaf (LexicalAnchor "Verb" "drink" "drinks" 33 39) [], LexicalLeaf (LexicalAnchor "Noun" "glass" "glass" 44 49) []]
                    ]
                ]
          , contextSnapshotHash = snapshotHash waterlooSnapshot
          , contextSource = rijekaSource
          , contextAction = "announce"
          , contextRole = SubjectHole
          , contextConstraints =
              [ ContextConstraint
                  (LexicalAnchor "Verb" "announce" "announces" 7 16)
                  (Requires (AnyOf [HasSort Animate, HasSort Organization]))
                  "VerbNet:say-37.7"
              ]
          , contextRuleProvenance = ["VerbNet:say-37.7"]
          }
      compositionGlassContext =
        Context
          { contextTree =
              LexicalApply
                "AndS"
                [ LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "OpenPN" "rijeka" "Rijeka" 0 6) []
                    , LexicalApply
                        "Compl"
                        [LexicalLeaf (LexicalAnchor "Verb" "announce" "announces" 7 16) [], LexicalLeaf (LexicalAnchor "Noun" "season" "season" 19 25) []]
                    ]
                , LexicalApply
                    "Pred"
                    [ LexicalLeaf (LexicalAnchor "HePN" "he" "he" 30 32) []
                    , LexicalApply
                        "Compl"
                        [ LexicalLeaf (LexicalAnchor "Verb" "drink" "drinks" 33 39) [Prefers (HasSort Entity)]
                        , LexicalLeaf (LexicalAnchor "Noun" "glass" "glass" 44 49) []
                        ]
                    ]
                ]
          , contextSnapshotHash = snapshotHash containerSnapshot
          , contextSource = glassEntity
          , contextAction = "drink"
          , contextRole = ObjectHole
          , contextConstraints =
              [ ContextConstraint
                  (LexicalAnchor "Verb" "drink" "drinks" 33 39)
                  (Prefers (HasSort Entity))
                  "local:selectional-lexicon"
              ]
          , contextRuleProvenance = ["local:selectional-lexicon"]
          }
  case contextualFiberChecked waterlooSnapshot [InstitutionOf] 1 compositionRijekaContext of
    Right stages ->
      assert
        "composed sentence: Rijeka half still resolves to its two real clubs"
        ( sort (map unEntityId (stageTargets (last stages)))
            == sort (map unEntityId [hnkRijeka, nkOrijent])
        )
    Left errorMessage -> do
      putStrLn ("FAIL: composed Rijeka half: " <> errorMessage)
      exitFailure
  case contextualFiberChecked containerSnapshot [Contains] 1 compositionGlassContext of
    Right stages ->
      assert
        "composed sentence: glass half still resolves to its one real content"
        (map unEntityId (stageTargets (last stages)) == [unEntityId rumEntity])
    Left errorMessage -> do
      putStrLn ("FAIL: composed glass half: " <> errorMessage)
      exitFailure

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

