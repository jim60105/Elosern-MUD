## Context

Part **B5** (showcase wave; depends on B2, B3, B4). The last showcase change: it completes the component
set, asserts the deferred surfaces are absent, and freezes the manifest — establishing the "showcase
complete before wiring" gate.

## Goals / Non-Goals

**Goals** — the four full overlays as documented, offline, component-tested SFCs; the manifest frozen;
deferred surfaces asserted absent.
**Non-Goals** — no wiring (C waves); no building of Party/intimate/full-inventory/event-log surfaces.

## Decisions

- **D1 — Creation gate rejects both age fields.** The wizard rejects `age < 18` **and** `apparent_age <
  18` before activation (mirrors the import invariant). This is the one security-relevant behavior in B5.
- **D2 — Deferred surfaces asserted absent.** The coverage assertion lists Party/intimate/full-bag/
  event-log as not present and not mocked; a later OOB change adds each with its own `MODIFIED` to this
  capability.
- **D3 — Freeze the manifest.** B5 sets the manifest to the complete set and stops extending it; the gate
  then enforces the frozen set until a deferred surface is formally added.

## Risks / Trade-offs

- **Creation overlay is the largest single component** → sub-states (preset pick, custom fields, concept,
  gate, activate) as separate story cases to keep it testable.
- **Deferred surface creep** → the absent-surface assertion is a hard test; adding one requires a spec
  `MODIFIED`, so it can't sneak in.

## Migration Plan

Offline/Storybook only; rollback = delete the overlays + unfreeze the manifest. All prior B changes and
gates unaffected.

## Open Questions

- None.
