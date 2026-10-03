# Local helper contracts

All paths in commands below are examples; `<skill-dir>` is this skill's installed folder. Run the helpers from the user's project directory and call each script by its full path. Relative arguments such as `my-lesson` resolve against the current directory, so never run them from inside the installed skill folder; projects, renders, and manifests belong in the user's workspace. `python` means any Python 3.10+ interpreter (often `python3` on macOS/Linux, `python` or `py -3` on Windows). Helpers use only the standard library, make no network requests, and do not send, upload, or synthesize anything.

Helpers write UTF-8 to stdout and stderr unless `PYTHONIOENCODING` chooses another encoding, in which case characters it cannot represent are written as `\u` escapes. Windows PowerShell 5.1 decodes captured output with the console code page; run `[Console]::OutputEncoding = [Text.Encoding]::UTF8` first when capturing or piping helper output there.

## Planning, captions, and integrity

`python <skill-dir>/scripts/project.py init my-lesson` creates a **new** directory with `project.json` and brief, claims, revision, and review templates. It refuses an existing target. The JSON starts incomplete by design; `check` must fail until required teaching content is filled.

`python <skill-dir>/scripts/project.py check my-lesson/project.json` checks IDs, required fields, scene-to-section/objective/claim references, coverage, claim source fields, and beat structure. It does not judge truth, pedagogical relevance, the adequacy of a citation, or whether a claim marked verified really was verified. Exit 0 means no structural errors; warnings remain visible.

`python <skill-dir>/scripts/project.py outline my-lesson/project.json` runs the same structural check first; if any structural error exists it prints that report and exits 1. Otherwise it prints each scene's ID, section, title, full narration, and transition in playback order. Use it as source material for the [transition-strip review](teaching-design.md#the-transition-strip-diagnostic): take each scene's first and last teaching sentences into one list and read that list without the rest of the script. The order of `scenes` is playback order; IDs remain stable when order changes.

The JSON schema is illustrated by [the worked example](../assets/examples/weighted-averages.json), included in the installable skill. A scene's spoken script is `narration` followed by `transition`; record and caption both, in that order. The final scene's `transition` carries the closing answer to the central question. Optional scene `beats` have globally unique `id`, `spoken`, `visual`, and `cue` strings; `spoken` summarizes the idea a beat covers and need not quote the narration. Take cue and caption timing from the recorded audio, not from these strings.

Claims have `id`, `text`, `kind` (`source`, `demonstration`, `illustration`, or `interpretation`) and `status`; `source` and `interpretation` additionally require nonempty `source`, `location`, and `conditions`. `project.json` `claims` is the ledger `check` validates; it may also hold optional `source_version` and `permitted_conclusion` keys (not checked). Record unresolved or contested assertions with their underlying `kind` and a `status` other than `verified`, which `check` reports as a warning. [claims.csv](../assets/templates/claims.csv) is an optional human-readable companion that `check` does not read; keep each `claim_id` identical to the JSON `id` (`proposition` ↔ `text`, `source_location` ↔ `location`). Scene links are checked only through `scenes[].claim_ids`.

`python <skill-dir>/scripts/project.py captions my-lesson/captions.srt --duration 120` checks standard single-track SRT cue numbering, valid increasing non-overlapping intervals, nonempty text, and cue ends against **measured** video duration. Without `--duration` the end check is skipped and the report says `"duration_check": "not performed (pass --duration)"`. It accepts UTF-8/BOM, Windows line endings, and extra blank lines between cues. It warns about more than two text lines. It does not support intentional overlapping captions, rich SRT timing extensions, VTT, audio alignment, or language-specific reading-speed evaluation. Those require a suitable editor and review.

`python <skill-dir>/scripts/project.py manifest my-lesson/deliverables --out my-lesson/manifest.json` records relative paths, bytes, and SHA-256 hashes. The output must be outside the hashed directory and must not exist. Symlinks and Windows junctions (any linked path) are rejected. Files are listed in code-point order of their relative paths on every platform. Hash equality establishes byte identity only.

## Still-scene assembler

Copy [render.json](../assets/templates/render.json) to your project and replace its asset paths with real local slides and authorized audio. Asset paths resolve relative to that JSON file and must remain within its directory tree. Neither images nor narration are supplied by the template.

```text
python <skill-dir>/scripts/assemble.py my-lesson/render.json --out my-lesson/video.mp4
```

Install FFmpeg and FFprobe through your normal trusted method and ensure they are on the PATH environment variable, or pass `--ffmpeg <path-to-ffmpeg> --ffprobe <path-to-ffprobe>`. Required encoder: `libx264`; required audio encoder: AAC. No automatic installation occurs.

The assembler accepts even integer width 16–7680 and height 16–4320, an integer frame rate of 1–120 (default 1280×720 at 30 fps), and unique scene IDs. Each scene has a still image, an audio file that decodes to at least one sample, and optional `hold_after` seconds (0–60). It preserves aspect ratio with letterboxing and produces H.264/yuv420p and 48 kHz stereo AAC. Transparent image areas are flattened onto white; letterbox bars are black; animated images use their first frame. Inputs are copied into a temporary folder under short names, so file names containing `%` are read as ordinary files.

Each scene's duration is its decoded audio length plus `hold_after`, rounded up to whole frames. The assembler pads each scene's decoded audio to its frame-grid length and encodes one continuous audio track, so scene joins do not accumulate audio delay. It writes a new MP4 and a sibling `.timeline.json`, and refuses to overwrite either. It decodes the entire result, checks the video frame count and that decoded audio length matches video length within one frame plus one audio packet, and records scene offsets in `start` (frame-grid seconds). The receipt keeps `schema_version` 1 and records `duration`, `video_duration`, `decoded_audio_duration`, `fps`, and for each scene `id`, `start`, `clip_duration`, `frames`, `audio_duration`, and `requested_hold_after`. Still inspect joins in final playback and align final captions to the final audio. Do not interpret this timeline as word-level alignment. Per-scene errors name the scene ID and its slide and audio paths.

It does not normalize loudness, generate speech, verify voice rights, create captions, render presentation animations, review visuals, or prove audibility. The receipt explicitly leaves listening and visual review unperformed. Use the production and review references for those tasks.

## Error behavior

Errors print `ERROR: …` to stderr with exit status 2; `check`, `outline`, and `captions` exit 1 when they find structural or caption errors. Validation errors do not modify source material. Rendering takes place in a temporary directory beside the output; that temporary directory is cleaned by the standard library. Existing outputs are never overwritten. An OS failure during final file copying can leave a partial output; inspect it and choose a new path for a subsequent run. A failure writing the timeline after copying the movie can leave a movie without a receipt. Never infer successful completion from an output filename alone.
