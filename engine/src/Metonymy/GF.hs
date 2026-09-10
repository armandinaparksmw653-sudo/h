module Metonymy.GF
  ( linearize
  , parseEnglish
  , spaceBeforeCommas
  ) where

import Data.Char (isSpace)
import System.Exit (ExitCode (..))
import System.Process (readProcessWithExitCode)

linearize :: FilePath -> String -> IO (Either String String)
linearize pgfPath expression = do
  (exitCode, stdoutText, stderrText) <-
    readProcessWithExitCode
      "gf"
      ["--run", pgfPath]
      ("l -lang=GeneratedMetonymyEng " <> expression <> "\n")
  pure $
    case exitCode of
      ExitSuccess -> Right (trim stdoutText)
      ExitFailure _ -> Left (trim stderrText)

parseEnglish :: FilePath -> String -> IO (Either String [String])
parseEnglish pgfPath sentence = do
  (exitCode, stdoutText, stderrText) <-
    readProcessWithExitCode
      "gf"
      ["--run", pgfPath]
      ("p -lang=GeneratedMetonymyEng \"" <> spaceBeforeCommas sentence <> "\"\n")
  pure $
    case exitCode of
      ExitSuccess -> Right (filter (not . null) (map trim (lines stdoutText)))
      ExitFailure _ -> Left (trim stderrText)

-- GF's parser uses a whitespace-only tokenizer by default: a comma with
-- no preceding space ("programme,") is one indivisible token, not two,
-- and no grammar-level device (BIND/SOFT_BIND included -- confirmed by
-- direct local testing against a real gf.exe build, not guessed) can
-- retroactively split an already-fused input token at parse time. Every
-- comma-using grammar construct (BecauseS/SBecauseS-family,
-- ApposCommaPN1/ApposCommaPN2 in grammar/MetonymyEng.gf) needs its
-- comma to arrive as its own token, exactly like natural English commas
-- already are once a space precedes them. This inserts that space only
-- when one isn't already there, so it's a no-op for every sentence that
-- doesn't reach a comma-using construct -- which, before this session's
-- comma-based grammar additions, was every sentence this engine ever
-- parsed.
spaceBeforeCommas :: String -> String
spaceBeforeCommas (a : b : rest)
  | b == ',' && a /= ' ' = a : ' ' : b : spaceBeforeCommas rest
  | otherwise = a : spaceBeforeCommas (b : rest)
spaceBeforeCommas other = other

trim :: String -> String
trim = dropWhileEnd isSpace . dropWhile isSpace
  where
    dropWhileEnd predicate = reverse . dropWhile predicate . reverse
