---
name: tutorial-video
description: Plan, produce, review, or revise a lecture, tutorial, workshop recording, or course video with a coherent learning progression and synchronized editable slides, narration, captions, and media. Use for any subject and for existing instructor materials; a request for slides alone does not require producing a video.
license: MIT
metadata:
  version: 1.0.0
---

# Tutorial Video

Help an instructor turn knowledge into something a particular audience can understand and use. Choose the teaching structure before choosing the production tools. Work from the user's existing materials and accepted decisions; scale this workflow to the requested scope.

## Start with the actual assignment

Determine the mode: **new lesson**, **adapt existing materials**, **targeted revision**, or **read-only audit**. An audit returns findings with scene/page/time references; it does not change the materials. A slide-only or script-only task stops at that deliverable.

Read existing status, accepted source files, instructor comments, hidden-slide state, and delivery requirements before generating anything. “Latest” means the latest accepted edition, verified against the authoritative destination when one exists, rather than the newest local filename. Record that baseline.

Infer from the brief what you can: audience and prerequisites; what learners should be able to do; language; duration and whether it is a hard limit; format; required sources; editable deliverables; voice rights and preference; tools and budget; accessibility; destination and visibility. Ask only about consequential unknowns. Keep reversible assumptions visible and continue independent work.

Use [the brief template](assets/templates/brief.md) if a project has no equivalent. A short lesson need not have a large project structure. For a substantial course, `python scripts/project.py init PATH` creates a small editable planning package without overwriting an existing directory.

## Build the lesson around understanding

Read [teaching design](references/teaching-design.md) and the relevant [format adaptation](references/formats.md).

1. Write the learner's destination as an observable ability and a central question.
2. Organize sections around concepts, decisions, or abilities. Use papers, tools, events, and examples to answer those questions; do not let their names become the default outline.
3. Map prerequisites. Introduce a term or distinction before relying on it. A correct explanation can still arrive too early.
4. Give each difficult concept a concrete situation: **who acts, what they see, what they do, what changes, and how we know**. Follow an analogy with the actual mechanism and where the analogy stops working.
5. Link sections by a reason: the previous answer creates a new question, limitation, or application. Read all transitions in sequence; check that each section's opening promise covers every scene in it.
6. Include a prediction, worked example, explanation prompt, or transfer exercise appropriate to the format. Use the answer to diagnose a misconception, not merely to repeat a definition.
7. End by answering the whole lesson's opening question. Do not let the final section stand in for the whole course.

When a user says a diagram or section is confusing, diagnose the missing relationship before polishing prose. Preserve instructor-approved ordering and examples unless changing them is within scope. Propose structural changes concretely when necessary.

## Establish evidence before polishing claims

Read [evidence and explanations](references/evidence-and-explanations.md) for research, numbers, demonstrations, or contested claims.

Maintain a claim-to-source map with the source version, location, conditions, and permitted conclusion. Verify the claim itself, including denominators, filters, baselines, uncertainty, and measurement definitions. Distinguish evidence from interpretation, illustrative numbers, and open questions. A confident instructor suggestion still deserves respectful verification.

A simplification must preserve the proposition. Never silently turn a score into an accuracy percentage, a correlation into a cause, a filtered subset into a population result, or a successful demonstration into a general guarantee. Put usable citations where the viewer can find them.

## Design the visible and spoken explanation together

Read [visual storytelling](references/visual-storytelling.md) and [narration and pacing](references/narration-and-pacing.md).

Use stable scene and beat IDs. For each beat, connect a spoken idea to the visible object, its reveal or highlight, and its teaching purpose. Multiple beats may share a slide; one idea may need multiple scenes. Do not impose a universal one-slide/one-audio-file rule.

Prefer editable text, charts, tables, and diagrams for teaching content that will be revised. Choose illustration, real screen capture, animation, physical demonstration, or a presenter shot when it clarifies the idea. Keep labels, quantities, and scientific plots exact. Preserve existing click order and instructor highlights when requested.

Write for the ear. Define unfamiliar terms when first needed; make pronouns and actors explicit. Explain what to notice in a figure. Reveal the relevant object when its explanation begins, and leave time to inspect it. Measure a representative narration sample before setting a duration budget. A hard time limit requires selection and compression of scope; speeding speech is not the default remedy.

For a full new production, make one representative segment spanning a difficult explanation, a transition, captions, and visual cues before scaling expensive generation. Existing authorization remains valid; do not add an approval stop when the user already asked you to proceed.

## Produce and keep the package synchronized

Read [media production](references/media-production.md). Use available authorized tools; this skill does not require a particular model, cloud service, operating system, or speaker identity.

Keep the display script, pronunciation form, actual recording, and caption text related but distinct. Use only a voice that is authorized for this use. Do not silently substitute a speaker or upload private scripts to an unapproved service. Record tool versions, settings, input hashes, and accepted takes so unchanged material can be reused.

Calculate the timeline from measured rendered media durations. Align captions against actual speech; do not spread text uniformly across a slide and call it word alignment. Verify the exported movie, including its end, rather than only checking inputs.

For changes, read [revision and delivery](references/revision-and-delivery.md). Follow the dependency chain:

**claim / teaching decision → visible content and notes → spoken script → audio → beat timing → video → captions → chapters / catalog / downloads.**

Regenerate only affected dependencies. Compare untouched scenes to the accepted baseline. If some layers remain old, label them with their actual edition and mark the update partial.

## Review on three independent dimensions

Read [quality review](references/quality-review.md), and record evidence in [the review template](assets/templates/review.md).

- **Correctness:** claims, conditions, units, names, pronunciation, negation, citations, and examples.
- **Comprehension:** can the target audience follow the reasoning, identify the actors, predict the next step, and apply the idea? Inspect the story across scenes, not only individual pages.
- **Technical integrity:** inspect every final slide, exercise consequential reveal states, decode the complete export, hear actual audio, check timing/captions and the final frame, and open the editable deliverables.

Automated scores are diagnostic evidence. High ASR similarity, valid files, and clean layout do not prove semantic fidelity or learning. If playback/listening, native editing, source access, or learner testing was unavailable, say exactly what remains unverified. Use a fresh review perspective or an independent reviewer when authorized and useful; distinguish simulated learner review from real learner evidence.

Optional local helpers (Python 3.10+, standard library):

```text
python scripts/project.py check PATH/project.json
python scripts/project.py outline PATH/project.json
python scripts/project.py captions PATH/captions.srt --duration 120
python scripts/project.py manifest PATH/deliverables --out PATH/manifest.json
python scripts/assemble.py PATH/render.json --out PATH/video.mp4
```

The assembler additionally needs FFmpeg and FFprobe and supports narrated still scenes. Use a suitable editor for animation, live demos, multiple tracks, and interactive reveals. Read [tool contracts](references/tool-contracts.md) before using helpers. A passing helper check is not a release approval.

## Deliver the requested result

Deliver the agreed subset: editable source, accessible video, captions, transcript, citations, chapter times, thumbnail if useful, and concise change/verification notes. State measured duration, version, limitations, and where each file is.

Honor already-given publishing or email authorization. Otherwise creation alone does not authorize publication, wider sharing, or sending. For an authorized remote action, verify account, audience, final content, and destination; submit once and read back the resulting object. Reconcile uncertain outcomes before any retry. Retain publication and delivery receipts separately from public source material.

For the rationale behind these practices and their origins, see [collaboration lessons](references/collaboration-lessons.md). These lessons are transferable decision criteria, not a requirement to imitate a particular instructor or topic.
