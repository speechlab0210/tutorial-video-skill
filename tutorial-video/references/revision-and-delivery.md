# Revision and delivery

## Start from accepted reality

Record the authoritative edition, source commit or hash, publication version where applicable, and scope. If the owner identifies an accepted website or deck as the baseline, verify that exact edition before editing. An older local folder with a more recent modification time can still be rejected work.

Read the supplied instructor file itself. Comments, handwritten marks, notes, highlighting, and click order can carry instructions that a text extraction misses. Respect explicit visibility scope: an audit of visible slides does not silently count hidden slides or speaker notes as visible coverage.

Use [the revision template](../assets/templates/revision.md) to map each request to scene IDs and acceptance evidence. Distinguish exact wording changes from changes requiring interpretation. Do not add replacement filler when the user requests a precise deletion.

## Track dependencies, not just files

| Change | Likely dependent work |
|---|---|
| Citation only | Visible reference / bibliography / relevant exports |
| Spoken wording | Notes, recording script, audio, timing, video, captions, transcript |
| Visual label | Editable source, rendered slide, video; speech if it names the label |
| Scene order | Transitions, prerequisites, IDs-to-order map, video, captions, chapters |
| Clip duration | All following offsets, captions, highlights, chapters |
| Voice or language | Voice authorization, glossary, recordings, timings, captions, localized visuals |
| Delivery file | Catalog entries, links, checksums, download package |

Use stable IDs independently of order. A scene can retain its identity after reordering. Do not join audio to slides by positional filename assumptions.

Verify untouched materials against the accepted edition: text comparison, file hashes, native object checks, or visual comparison as appropriate. A notes-only change may legitimately modify only notes XML in a presentation; re-render anyway when that affects the export path.

## A partial update must look partial

If the slides are revised but the recording is old, label the recording as the previous edition and explain the difference. Do not label an entire course “updated” merely because the web page or transcript changed. Preserve old immutable download links if they are part of the existing delivery contract.

Choose a new version only after the package is coherent. Keep the accepted baseline and a clear change record so a rejected revision can be set aside without overwriting good work.

## Deliver useful files

Agree on the subset appropriate to the request: editable deck/source, PDF, video, separate captions, readable transcript, source list, chapter times, thumbnail, and change/review report. Validate the actual archive contents and test links/downloads. Include a manifest with hashes when integrity or version matching matters.

The user should be able to tell: what changed, why, what was checked, what remains unverified, and which file is current. Avoid flooding them with internal logs or claiming “all checks passed” when significant checks were unavailable.

## Authorized remote actions

Creation, private sharing, public publication, and email are distinct actions. Reuse explicit authorization the user has already given for this work, destination, and visibility; it does not carry over to another project, destination, or audience. Preserve an existing audience/access setting unless the user asks to change it.

Before a write, verify account, destination, selected files, exact content, synthetic-media disclosure (in the video or description, and the destination's AI or altered-content setting where one exists), and duplicate state. Record a durable attempt identifier and intended content before submission. Submit once, then read back the remote object and compare content, visibility, and relevant file hashes or sizes.

If the result is uncertain, inspect the destination. A search returning nothing can be an indexing delay; it is not automatically evidence that a send or upload failed. Do not repeat a potentially completed external action while its outcome is unresolved. Completion reports distinguish submission acceptance, verified remote presence, recipient receipt, and actual readership.
