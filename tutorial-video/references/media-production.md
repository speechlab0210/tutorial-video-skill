# Media production

## Establish a small production contract

Record resolution/aspect ratio, frame rate, audio format, target playback devices, subtitle format, editable source format, voice, language, tool versions, and budget. Do not assume that a local voice model, paid API, or presentation renderer is available.

For a new course, validate one difficult representative segment before generating a long batch. Include exact typography, a diagram, a transition, the chosen voice, and captions. For a narrow repair, reproduce the affected segment using the established pipeline rather than replacing the whole toolchain.

Use predictable project-relative paths. Resolve them relative to the project manifest, not the script's installation directory or a convenient current working directory. Otherwise a reusable script can silently render assets from a different course.

## Assets and reproducibility

Keep a manifest connecting scene IDs to slide source, rendered images, narration text hash, pronunciation form, voice/settings, audio take, beat timings, captions, and output hashes. File order and similar filenames are not evidence of identity.

For reuse, match the actual text and provenance. If several takes contain the same words, prefer the take that produced the accepted edition, unless the user requests a change. Do not rerun expensive accepted generations merely to make the folder layout uniform.

Keep credentials outside project files. Exclude private raw recordings, licensed source materials, personal links, and service receipts from any public source export unless separately authorized and appropriate.

## Audio and assembly

Listen for missing speech, clipping, noise, repeated words, truncated consonants, unnatural joins, and mismatched voices. Measure integrated loudness and true peak per scene or take as well as per chapter: separately generated or regenerated takes can jump audibly at joins, and the bundled assembler does not normalize. Record the chosen target and measured values. Check a normalizer's defaults against the destination; FFmpeg's `loudnorm` defaults (−24 LUFS, −2 dBTP) are broadcast-oriented. Measure the final continuous track, not only the inputs. Do not confuse sample peak, true peak, integrated loudness, and subjective clarity.

Preserve intended pauses explicitly. Inspect whether a shortest-stream option truncates planned silence or the final spoken word. Derive section offsets from rendered clip durations measured by the actual media tool. Accumulating assumed audio-plus-padding durations can produce growing caption drift. A timeline computed from the same clip durations as the video cannot validate itself.

Stream-copy concatenation of separately encoded compressed-audio clips adds encoder priming and padding at every join even when all parameters match; narration then falls progressively behind the slides and the ending can be cut off. Encode narration once across the whole timeline (concatenate PCM/WAV first) or use an editor; stream-copy only video-only clips whose codec parameters match, and re-encode when they do not. Preserve the final frame long enough for closure if required by the teaching design.

The bundled [assembler contract](tool-contracts.md#still-scene-assembler) provides a simple still-image/audio route. It does not replace an editor for progressive builds, live capture, overlays, animation, or interactive exercises.

## Captions and chapters

Start from what was actually spoken. Forced alignment or reviewed ASR timings can support accurate captions; proportional character allocation over an entire slide is only a rough draft. Respect meaningful phrases, reading speed, language-specific line breaks, and caption-safe visual space.

The bundled helpers validate but do not author captions. Produce cues from an authorized aligner's or reviewed recognizer's segment/word timestamps for the final audio, if you aligned scene by scene, shift them by each scene's `start` (a frame-grid offset computed by the assembler) in the `.timeline.json` receipt beside the video, split at phrase boundaries, then run `project.py captions … --duration <measured>`. Label any proportional draft as a draft and align it before release.

Check starts, middle passages, every changed join, and the ending; inspect drift across the full timeline. Verify names, numbers, units, and negatives against both the recording and intended claim. Read subtitle files with Unicode support.

Offer a separate SRT or VTT track when useful. Burned captions are a destination choice, not a universal requirement, and can obstruct the teaching graphic. Provide a readable transcript and measured chapter start times. When essential information appears only on screen (for example values that are not read aloud), describe it in narration or add it to the transcript or accompanying description.

## Evidence from the final artifact

Probe the exported file, decode its full duration, compare decoded audio length with video length, and at the start, middle, and end measure how long after its slide change each scene's speech begins. Subtract that take's own leading silence, measured in the source take; the remainder is the sync error a destination-appropriate tolerance applies to, and it must not grow along the video. Locate slide changes by checking frames around the expected scene starts; a scene-change detector's default threshold can miss a low-contrast change. Then inspect audio loudness/silence, and review frames from the exported movie. Then watch/listen at normal speed, especially the edited regions and their surrounding context. A file with an audio stream can still be silent; a valid video can still show the wrong slides.

Open the editable files and test their important behavior. If an embedded clip or click-triggered audio matters, test it in the intended native player. Record actual playback and review coverage; never claim a full viewing based on a contact sheet or transcriber alone.
