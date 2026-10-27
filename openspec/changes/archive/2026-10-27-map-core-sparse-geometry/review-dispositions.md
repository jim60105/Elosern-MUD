# Whole-batch rubber-duck review dispositions

One blocking review inspected both authoritative written source documents and all twenty actual proposal/design/spec/task sets. The review was planning-only and ran no implementation checks. Its verdict required targeted amendments, with no dependency cycle, viewer-only reduction or invented implementation approval found.

| Finding | Severity | Disposition | Artifact remedy |
| --- | --- | --- | --- |
| Document creation/deletion and undo cannot fit replace-only writer | Blocking | Adopted | map-editor-document-commands defines typed internal create/replace/remove effects, explicit absent/hash expectations, no-overwrite create, guarded unlink, whole-result validation, durability uncertainty and history across presence/absence; substantive stale/create/remove/undo/redo scenarios and tasks were added. Layout cleanup stays a separate operation. |
| Context freshness lacks destructive execution checkpoint | Non-blocking | Adopted | reference export, writer and relationship contracts require fresh external dependency membership/hashes immediately before object-removing commands/inverses; unchanged index/browser state cannot authorize deletion after an external source edit. Added service-effect scenarios and tasks. |
| Service watcher notifications may be mistaken for external edits | Non-blocking | Adopted | turn/recovery compares fresh disk presence/content to committed writer fingerprints; delayed/coalesced expected self-events preserve manual history and actual external replacement pauses writing. Added real-filesystem regression scenario/task. |
| Retained capital geometry scenario pins shipped coordinates | Non-blocking | Adopted | wilderness-gateway delta now specifies a synthetic irregular mask with independently known anchor and approach cells; shipped preservation stays temporary conversion evidence. |

No finding was rejected or deferred. The single final reviewer was not asked to run implementation checks or grant implementation approval. Shared worker contracts now have one canonical copy in this change, referenced by the other nineteen sets, so lifecycle/freshness amendments cannot leave contradictory copied versions behind.

## Requirement shape after remedies

The persistence requirement states one short document-effect mechanism, with lifecycle edge cases moved into scenarios. New watcher/freshness cases extend the existing mechanism requirements rather than adding evidence-only requirements. Final integrated acceptance still uses skip_specs=true. Human visual/copy/fidelity review remains the future specialist deliverable docs/design/map-editor-review.md; the approved design documents are unchanged.
