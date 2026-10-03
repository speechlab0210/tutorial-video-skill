# Narration and pacing

## Write for a listener who cannot reread instantly

Use short spoken units, explicit actors, and concrete verbs. Explain the operation before leaning on its label. “Global” could mean “one score computed over the entire recording”; the listener needs that meaning at first use.

Read each sentence with only the current visual in view. Check whether “this,” “it,” “the next one,” or “the fifth” has more than one possible referent. Distinguish topic numbering from section numbering.

Speech should guide attention and reasoning, not recite every label. Tell the viewer where to look and what comparison matters. A paragraph written for a paper usually needs restructuring before narration.

Maintain a glossary for pronunciation, abbreviations, translated terms, names, and units. In multilingual work, keep equivalent teaching intent and terminology across versions rather than forcing sentence-by-sentence timing identity. The audience language and required technical vocabulary determine whether to retain a foreign term.

## Separate three text layers

1. **Display/transcript text:** correct spelling and readable notation.
2. **Synthesis text:** pronunciation expansions or phonetic substitutions, if required by the selected voice.
3. **Captions:** readable words corresponding to what was actually said.

Do not let phonetic workarounds leak into scholarly citations or the readable transcript. Do not delete all punctuation as a universal TTS fix; voice systems behave differently. By ear, on the actual selected voice and regardless of any ASR score, test difficult names, abbreviations and acronyms, words with more than one reading (for example Chinese 多音字 such as 重新, 銀行, 長), numbers (years, versions, ranges, decimals), units, symbols, and mixed-language passages.

Keep meaningful context together when synthesizing. Over-fragmenting speech can cause inconsistent intonation and awkward joins. Choose segment sizes experimentally, bounded by tool constraints and revision cost. Save accepted takes with source hashes and settings. A newer take is not automatically better.

## Pauses have functions

Separate breath pauses, visual-search time, prediction time, diagram-reading time, and section transitions. Remove accidental dead air while retaining intentional thinking time. A fixed two-second pause at every highlight can make a course drag; deleting every pause can make the same course incomprehensible.

Play a representative segment at normal speed. Check the interval between naming an object, highlighting it, finishing the explanation, and changing slides. Adjust those relationships rather than simply stretching the entire recording.

Keep speech speed natural unless the user requests otherwise. Estimate runtime from recorded samples in the same language, voice, and content style. Spoken numbers and equations may take much longer than their written character count suggests. Report estimation error once full media exists.

## Listening and ASR

Use transcription to locate omissions, repetitions, pronunciation problems, and wrong takes. Normalize punctuation and equivalent number forms carefully, while preserving negatives, units, and comparison direction. A single missing “not” can reverse a claim despite a high overall similarity.

For Chinese, phonetic comparison can help identify homophone transcription errors, but it must not erase meaningful ambiguity. Transcription and phonetic scores cannot detect a misreading that the recognizer's language model restores to the intended word, which is common for multi-reading words, acronyms, and number formats; check those glossary items by listening to the final audio, or report them as not checked. There is no language-independent similarity threshold that proves correctness. Calibrate a diagnostic threshold on known good and bad samples for the chosen recognizer.

When a score is low, listen to the disputed passage before regenerating it. If the sound is correct and the recognizer is wrong, record that evidence. If the sound is wrong, fix the sound; correct captions do not excuse a false spoken claim. Bound retries and retain the best acceptable take.
