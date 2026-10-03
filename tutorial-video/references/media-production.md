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

Listen for missing speech, clipping, noise, repeated words, truncated consonants, unnatural joins, and mismatched voices. Compare chapter loudness using consistent measurements and listening. Apply a deliberate loudness policy appropriate to the destination; do not confuse sample peak, true peak, integrated loudness, and subjective clarity.

Preserve intended pauses explicitly. Inspect whether a shortest-stream option truncates planned silence or the final spoken word. Derive section offsets from rendered clip durations measured by the actual media tool. Accumulating assumed audio-plus-padding durations can produce growing caption drift.

Ensure each clip has compatible video/audio parameters before stream-copy concatenation. Re-encode or use an editor when that assumption does not hold. Preserve the final frame long enough for closure if required by the teaching design.

The bundled [assembler contract](tool-contracts.md#still-scene-assembler) provides a simple still-image/audio route. It does not replace an editor for progressive builds, live capture, overlays, animation, or interactive exercises.

## Captions and chapters

Start from what was actually spoken. Forced alignment or reviewed ASR timings can support accurate captions; proportional character allocation over an entire slide is only a rough draft. Respect meaningful phrases, reading speed, language-specific line breaks, and caption-safe visual space.

Check starts, middle passages, every changed join, and the ending; inspect drift across the full timeline. Verify names, numbers, units, and negatives against both the recording and intended claim. Read subtitle files with Unicode support.

Offer a separate SRT or VTT track when useful. Burned captions are a destination choice, not a universal requirement, and can obstruct the teaching graphic. Provide a readable transcript and measured chapter start times.

## Evidence from the final artifact

Probe the exported file, decode its full duration, inspect audio loudness/silence, and review frames from the exported movie. Then watch/listen at normal speed, especially the edited regions and their surrounding context. A file with an audio stream can still be silent; a valid video can still show the wrong slides.

Open the editable files and test their important behavior. If an embedded clip or click-triggered audio matters, test it in the intended native player. Record actual playback and review coverage; never claim a full viewing based on a contact sheet or transcriber alone.
