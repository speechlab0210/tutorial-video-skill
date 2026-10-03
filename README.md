# Tutorial Video Skill

An AI agent skill for helping an instructor create a coherent, accurate, editable course video on **any subject**.

**[繁體中文](README.zh-TW.md) · [Download v1.0.0](https://github.com/speechlab0210/tutorial-video-skill/releases/tag/v1.0.0) · [Skill entrypoint](tutorial-video/SKILL.md)**

The skill covers the whole teaching-production loop: understanding the audience, selecting a learning progression, checking evidence, designing explanations, synchronizing slides and speech, producing media, reviewing the finished lesson, and handling revisions and authorized delivery.

It grew from educational media production and a closely revised Interspeech conference tutorial collaboration. The result generalizes the teaching decisions and engineering lessons instead of distributing the original tutorial, private feedback, voice, or topic-specific rules.

## What makes it useful

- Organize around what learners need to understand or do, with sources serving the explanation.
- Make actors, decisions, comparisons, and timing explicit in difficult diagrams.
- Diagnose weak flow by reading every transition together and checking the opening promise against every scene.
- Coordinate spoken ideas, visible objects, and reveal/highlight events.
- Place pauses according to thinking and viewing needs, rather than applying a fixed gap everywhere.
- Verify claims with their actual conditions, denominators, source versions, and uncertainty.
- Keep editable slides, notes, scripts, takes, video, captions, and downloads aligned during revision.
- Review correctness, comprehension, and technical integrity separately.

These are decision tools, not a fixed presenter persona or slide formula. Research tutorials, software demonstrations, physical-skills lessons, humanities talks, business briefings, and workshops each get a different treatment.

## Download and use

Download `tutorial-video-skill-v1.0.0.zip` from the [release page](https://github.com/speechlab0210/tutorial-video-skill/releases/tag/v1.0.0), or clone this repository:

```text
git clone https://github.com/speechlab0210/tutorial-video-skill.git
```

For an agent with a skill-folder mechanism, place the **entire `tutorial-video/` directory**, including references, assets, and scripts, in its configured skills directory. For a local Codex installation, this can be `~/.codex/skills/tutorial-video/`. Do not copy only `SKILL.md`. Other agents can read that file directly and follow its linked references; host-specific automatic discovery is not guaranteed.

Example request:

> Use the tutorial-video skill to create a 20-minute beginner lesson about urban gardening. The audience has no gardening experience. Start from my notes, use editable slides, and make the examples explain decisions a learner can actually make. Produce the video, captions, and transcript locally.

Existing material:

> Use the tutorial-video skill to revise only section 2 of this lecture. Preserve the accepted sequence and voice. Explain the confusing diagram with one concrete example, and synchronize notes, audio, captions, and video. Leave other sections unchanged.

The skill respects draft-only, read-only, and narrow-revision requests. It does not treat video creation as automatic permission to publish or email.

## Included resources

| Resource | Purpose |
|---|---|
| [SKILL.md](tutorial-video/SKILL.md) | Concise agent instructions and routing |
| [Teaching design](tutorial-video/references/teaching-design.md) | Prerequisites, examples, transitions, transfer, and time budgeting |
| [Evidence](tutorial-video/references/evidence-and-explanations.md) | Claim-source ledger and faithful simplification |
| [Visuals](tutorial-video/references/visual-storytelling.md) | Diagrams, native charts, cue order, accessibility |
| [Narration](tutorial-video/references/narration-and-pacing.md) | Spoken writing, pronunciation, pauses, and ASR limits |
| [Production](tutorial-video/references/media-production.md) | Takes, timelines, audio, captions, and final export |
| [Revision and delivery](tutorial-video/references/revision-and-delivery.md) | Accepted baselines, dependency updates, remote readback |
| [Quality review](tutorial-video/references/quality-review.md) | Correctness, comprehension, and technical review |
| [Formats](tutorial-video/references/formats.md) | Adaptation to different kinds of talks |
| [Collaboration lessons](tutorial-video/references/collaboration-lessons.md) | Existing craft, engineering experience, and instructor feedback |
| [Templates](tutorial-video/assets/templates) | Brief, claims, revision, review, and render configuration |
| [Worked example](tutorial-video/assets/examples/weighted-averages.json) | A complete small plan with explicit beats and synthetic numbers |
| [Cross-domain scenarios](examples/cross-domain.md) | Gardening, history, software, and targeted revision examples |
| [Local helpers](tutorial-video/references/tool-contracts.md) | Plan checks, transition strip, SRT checks, hashes, simple assembly |

## Optional helpers

Python 3.10+ is sufficient for planning, caption structure checks, and manifests. There are no Python package dependencies and no network calls. Run from this repository:

```text
python tutorial-video/scripts/project.py init my-lesson
python tutorial-video/scripts/project.py check tutorial-video/assets/examples/weighted-averages.json
python tutorial-video/scripts/project.py outline tutorial-video/assets/examples/weighted-averages.json
python tutorial-video/scripts/project.py captions my-lesson/captions.srt --duration 120
python tutorial-video/scripts/project.py manifest my-lesson/deliverables --out my-lesson/manifest.json
```

The initialized plan is deliberately incomplete. Fill it before checking it. A structural pass is not an educational quality rating.

For narrated still scenes, install FFmpeg and FFprobe with H.264/AAC support, prepare real images and authorized audio, adapt the included render template, and run:

```text
python tutorial-video/scripts/assemble.py my-lesson/render.json --out my-lesson/video.mp4
```

This produces a new movie and measured timeline receipt. It does not synthesize speech, create slides, normalize loudness, generate captions, or inspect comprehension. Animated slides and live demos need an appropriate editor. See [the contracts and limits](tutorial-video/references/tool-contracts.md).

## Validation and limits

```text
python -m unittest discover -s tests -v
```

Tests exercise malformed plans, coverage and ID errors, Unicode captions, overlap and duration errors, hash integrity, no-overwrite behavior, and rendering path boundaries. An integration test builds two synthetic scenes with different colors and tones, decodes the movie, checks scene order and retained ending silence, and records skips if FFmpeg/FFprobe are unavailable.

The repository also includes [manual behavioral evaluation cases](tests/behavioral-cases.md). Passing automated tests proves these helper behaviors, not cross-agent compatibility, factual accuracy in arbitrary subjects, or learning effectiveness. No controlled learner study is claimed.

## Authorship and license

This package was written by an AI agent and is maintained through the `speechlab0210` account. It synthesizes reusable experience; it is not an official Interspeech resource or a reviewed endorsement by an instructor. It includes no private teaching correspondence or original conference media.

The original instructions, templates, examples, and code in this package are provided under the [MIT license](LICENSE). Third-party tools and material used in future lessons retain their own licenses and permissions.
