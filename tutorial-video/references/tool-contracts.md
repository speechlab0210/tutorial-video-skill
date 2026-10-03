# Local helper contracts

All paths in commands below are examples. Run them from the skill directory or use the script's full path. Helpers require Python 3.10 or later and use only its standard library. They make no network requests and do not send, upload, or synthesize anything.

## Planning, captions, and integrity

`python scripts/project.py init my-lesson` creates a **new** directory with `project.json` and brief, claims, revision, and review templates. It refuses an existing target. The JSON starts incomplete by design; `check` must fail until required teaching content is filled.

`python scripts/project.py check my-lesson/project.json` checks IDs, required fields, scene-to-section/objective/claim references, coverage, claim source fields, and beat structure. It does not judge truth, pedagogical relevance, the adequacy of a citation, or whether a claim marked verified really was verified. Exit 0 means no structural errors; warnings remain visible.

`python scripts/project.py outline my-lesson/project.json` prints the scene narration and transition in course order for the transition-strip review. The order of `scenes` is playback order; IDs remain stable when order changes.

The JSON schema is illustrated by [the worked example](../assets/examples/weighted-averages.json), included in the installable skill. Optional scene `beats` have globally unique `id`, `spoken`, `visual`, and `cue` strings. Claims have `id`, `text`, `kind` (`source`, `demonstration`, `illustration`, or `interpretation`) and `status`; `source` and `interpretation` additionally require nonempty `source`, `location`, and `conditions`. Put version/date in the source field or the CSV ledger.

`python scripts/project.py captions my-lesson/captions.srt --duration 120` checks standard single-track SRT cue numbering, valid increasing non-overlapping intervals, nonempty text, and cue ends against **measured** video duration. It accepts UTF-8/BOM and Windows line endings. It warns about more than two text lines. It does not support intentional overlapping captions, rich SRT timing extensions, VTT, audio alignment, or language-specific reading-speed evaluation. Those require a suitable editor and review.

`python scripts/project.py manifest my-lesson/deliverables --out my-lesson/manifest.json` records relative paths, bytes, and SHA-256 hashes. The output must be outside the hashed directory and must not exist. Symlinks are rejected. Hash equality establishes byte identity only.

## Still-scene assembler

Copy [render.json](../assets/templates/render.json) to your project and replace its asset paths with real local slides and authorized audio. Asset paths resolve relative to that JSON file and must remain within its directory tree. Neither images nor narration are supplied by the template.

```text
python scripts/assemble.py my-lesson/render.json --out my-lesson/video.mp4
```

Install FFmpeg and FFprobe through your normal trusted method and ensure they are on PATH, or pass `--ffmpeg PATH --ffprobe PATH`. Required encoder: `libx264`; required audio encoder: AAC. No automatic installation occurs.

The assembler accepts positive even dimensions within the documented code limits, integer frame rates, and unique scene IDs. Each scene has a still image, an audio file with a measurable duration, and optional `hold_after` seconds (0–60). It preserves aspect ratio with letterboxing, produces H.264/yuv420p and 48 kHz stereo AAC, pads audio to the intended hold, and measures the rendered clips before joining them.

It writes a new MP4 and a sibling `.timeline.json`, and refuses to overwrite either. It decodes the entire result and records measured duration and scene offsets. Container timestamps and AAC priming can introduce small join differences; inspect the actual joins and align final captions to the final audio. Do not interpret this timeline as word-level alignment.

It does not normalize loudness, generate speech, verify voice rights, create captions, render presentation animations, review visuals, or prove audibility. The receipt explicitly leaves listening and visual review unperformed. Use the production and review references for those tasks.

## Error behavior

Validation errors do not modify source material. Rendering takes place in a temporary directory beside the output; that temporary directory is cleaned by the standard library. Existing outputs are never overwritten. An OS failure during final file copying can leave a partial output; inspect it and choose a new path for a subsequent run. A failure writing the timeline after copying the movie can leave a movie without a receipt. Never infer successful completion from an output filename alone.
