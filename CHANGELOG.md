# Changelog

## 1.2.0 — 2026-10-03

Checking synthesized or recorded speech with a recognizer, made explicit.

- New helper `project.py speech`: compares a recognizer's plain-text transcript with a scene's narration and transition (or any script file). It reports token similarity; missing, extra, and replaced passages as written, with the script text before each; the numbers on each side, with written and spoken forms treated as equal (Arabic digits with separators, decimals, and mixed Chinese scales such as 5萬7千; Chinese numerals such as 一千六 and 三點五萬; years read digit by digit; clock times; English number words and ordinals); percent and minus signs; and negation words, with Simplified forms and English contractions folded. Ranges such as 兩三 stay two numbers (except two numerals directly before 年, read as a year), one percent sign covers both ends of a range, the determiner 一 in 這一題 is not counted as a number, decimals keep their written digits (3.10 ≠ 3.1; an all-zero fraction is dropped, 2.0 = 2), and bracketed non-speech tags such as [Music] are ignored. It exits 1 when numbers, signs, or negations differ, the transcript is empty, or similarity is below a calibrated `--min-similarity`; it warns about digit-by-digit readings of quantities and about Simplified characters aligned against a Traditional script, and refuses caption or JSON files as input. It does not run a recognizer, listen, or compare phonetically.
- Calibrated before release on 1,397 accepted Chinese and 103 English narration segments from finished videos (three recognizers): 4.4% of Chinese and 2.9% of English segments are flagged for a number difference and 0.9% of Chinese segments for a negation, nearly all recognizer homophones or dropped words; every planted digit, numeral, dropped number, and dropped or replaced negation was caught. A first draft flagged 9% of Chinese segments; the fixes came from reading those false alarms.
- Guidance: a score ranks takes but does not say what the chosen take says, so read its transcript; compare numbers, signs, and negations as sets; re-run the checks on the exported audio scene by scene, because post-processing can change speech that passed as a take; re-baseline accepted takes when the recognizer or its settings change; convert script variants before judging differences.
- Review template and a behavioral case for speech that changed after it passed. Text-file arguments now name the flag when a file is a directory or not UTF-8.
- 39 tests (28 in 1.1.0).

## 1.1.0 — 2026-10-03

A review of 1.0.0 (six independent review angles, each finding checked by two verifiers, plus a fresh-agent trial run) found the problems below, and a second independent review checked the fixes. All are fixed here.

### Assembler

- **Narration no longer drifts behind the slides.** 1.0.0 encoded audio separately for every scene and joined the clips by stream copy; encoder priming and padding added about 29 ms of delay at every join, and its own duration check could not see it. In a 40-scene synthetic test at 30 fps, measured in the exported MP4, speech started 1.13 s after its slide by the last scene. Scenes now start on the frame grid, narration is decoded, padded, and encoded once as a single continuous track, and the assembler checks decoded audio length against the video frame count before writing the file. The same 40-scene test now measures 0.1 ms at the start, middle, and end (30, 25, and 7 fps).
- Scene length now comes from the decoded audio. VBR MP3 files whose container under-reports their length are no longer cut short.
- Slides are copied into the temporary folder under short names, so a `%` in a file or folder name no longer selects a different image.
- Transparent areas are flattened onto white (they rendered black), and GIF slides work.
- Errors during a scene name the scene ID and its slide and audio paths; a missing asset and an asset outside the render folder get different messages; the missing-FFmpeg message mentions `--ffmpeg` / `--ffprobe`; a relative `--ffmpeg` path keeps working; `schema_version: true` is rejected.
- The `.timeline.json` receipt keeps `schema_version` 1 and adds `video_duration`, `decoded_audio_duration`, `fps`, and per-scene `frames`; `start` and `clip_duration` are frame-grid values and `audio_duration` is the decoded length.
- Intermediate files are deleted as each scene is finished, and the final audio check has a timeout.

### Planning, caption, and integrity helpers

- Reports are written as UTF-8, so Chinese, emoji, and symbols no longer crash `check` / `outline` when output is piped or redirected under a legacy Windows code page. An explicit `PYTHONIOENCODING` is respected, with unencodable characters escaped.
- `captions` accepts more than one blank line between cues, reports whether the duration check was performed, and rejects a non-positive or non-finite `--duration` as a usage error.
- `manifest` rejects Windows junctions as well as symlinks (it could hash files outside the folder) and lists files in the same order on every platform.
- Clearer messages for an invalid claim `kind`, a missing beat ID, and a directory passed instead of `project.json`.

### Guidance

- Measure A/V sync in the exported file: at the start, middle, and end, compare each scene's speech onset after its slide change with the take's own leading silence. Avoid stream-copying separately encoded audio clips.
- Disclose synthesized or cloned narration and realistic generated imagery to viewers and in the destination's settings.
- Check heteronyms, acronyms, and number formats by listening; recognizer scores cannot catch misreadings that the language model "corrects".
- Scope of reused publishing authorization (this work, destination, and visibility), with the stricter rule reachable from SKILL.md and stated the same way in both READMEs.
- Accessibility: text contrast in final viewing conditions and describing on-screen-only information.
- Loudness per take as well as per chapter; how to produce captions and validate them with the helper; which JSON fields are spoken; how the JSON claim ledger relates to `claims.csv`.
- Helper commands are run from the user's project folder with full script paths (`<skill-dir>/scripts/…`); Claude Code and Codex install paths; the release ZIP layout.

### Tests

- 28 tests (17 in 1.0.0). New media tests measure the shipped MP4: a 12-scene sync test at 30 and 7 fps comparing every slide change with its speech onset, a VBR MP3 ending, awkward slide files (including a JPEG with a `.png` name), and scene-named errors. On Windows, each new test fails against the 1.0.0 scripts.

## 1.0.0 — 2026-10-03

First public release.
