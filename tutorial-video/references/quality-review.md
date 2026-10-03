# Quality review

## Three reviews, three different claims

| Review | Evidence to collect | What a pass does not establish |
|---|---|---|
| Correctness | Source locations, recomputed values, actual sound and captions, claim conditions | That a novice understands it |
| Comprehension | Transition strip, example walkthrough, predicted misconceptions, transfer prompt, learner feedback if available | That the exported files work |
| Technical integrity | Render inspection, native open/playback, full decode, timeline/caption checks, hashes/readback | That the claims are true |

Keep these separate in [review.md](../assets/templates/review.md). Do not let an aggregate score average away a critical wrong number, reversed negation, or misleading conclusion.

## A novice-view review

Temporarily ignore the author's knowledge. At every difficult passage ask:

- What does the learner know at this exact moment?
- Which visible object and actor does the sentence refer to?
- Is the term defined before it is needed?
- Can the learner reproduce the operation, not merely repeat an analogy?
- Does the comparison hold everything else reasonably fixed?
- Does the conclusion follow from the evidence shown?
- Why is the next scene here?

An independent reviewer can help if available and authorized. Give them the actual brief, skill, and relevant artifact without telling them the intended diagnosis. For self-review, use a separate pass and label it honestly. Role-playing a novice is useful editorial work, not evidence from a real learner.

## Inspect every visual; sample mechanics intelligently

View every final slide at readable size. Exercise consequential animation and media states, and inspect all changed scenes in context. Use automated checks for bounds, broken links, cue order, hashes, duration, and missing files. Watch/listen at normal speed across the finished lesson when feasible; record actual coverage if not.

Check the last seconds and final frame explicitly. A clean first minute does not detect a truncated conclusion. Inspect the stitched full course even if each chapter passed separately.

## Calibrate the checker

When a check flags many known-good artifacts, investigate the measurement rather than immediately rewriting the course. Compare with a known-good baseline using the same tool, settings, and input layer. A recognizer may split a proper name differently; an image detector may count orange content as a highlight; a loudness rule may use the wrong reference segment.

Fix invalid measurements based on evidence, not to make the score green. Keep the original observation, diagnosis, and corrected result. Do not lower a threshold just because a defect is inconvenient.

## Regression and acceptance

For each requested change, record a scene/page/time location, the observed issue, the implemented change, and the check that demonstrates it. Check neighboring transitions and unchanged material for regression. “The script was edited” is insufficient evidence that the final audio now says it correctly.

Statuses should be **pass**, **fail**, **not checked**, or **not applicable with reason**. “Not checked” does not count as a pass. If tools are missing, produce the reviewable work that is possible and report the precise remaining limit.

## When the user says “I still don't understand”

Treat that as new evidence. State the suspected point of confusion and make a concrete repair: define the actor, show input/output, split a multi-step diagram, add a controlled example, clarify the time axis, or replace a section frame that excludes later scenes. Inspect the new explanation at normal speed. Do not answer only with higher production metrics.
