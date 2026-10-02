## Why

Gallery actions refresh only the gallery panel while stage portraits consume roster and art, so changes such as setting a default remain invisible until login or F5. Worker settlement refreshes only art, leaving gallery pending rows and roster portraits stale; both publication gaps must close in one backend change.

## What Changes

- **BREAKING** All six gallery `ui_action` adapters declare the uniform `affected_panels: ("gallery", "art", "roster")` on success and domain rejection, through one renamed shared constant. Uniformity is a fixed decision, including selection and generation, rather than per-action dependency optimization.
- Each adapter completion publishes one newer affected-panel update containing freshly rendered gallery, art, and roster values through the existing dispatcher. Payload admission rejection and request-cache deduplication keep their existing behavior.
- Extend the existing `asset_completed` subscriber to independently re-render and gate art, gallery, and roster for every eligible live webclient session, publishing all matching panels together in one newer update. A gallery-only or roster-only match must not depend on an art match.
- Gate art by its current scene/catalog references, gallery by its rendered `selected` subject, and roster by every rendered character portrait's subject key. Re-derive from canonical state and the current session-owned selection; preserve late-completion safety, session isolation, read-only rendering, and the subject-key-only worker notification.
- No frontend implementation, polling, new notification protocol, compatibility layer, or migration. Existing computed stage portraits and URL crossfades consume committed panel replacements.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-management-actions`: uniform three-panel declarations and publication on all six actions' success/domain-rejection paths; selection remains presentation-state-only.
- `webclient-art-panel`: extend the existing worker-completion requirement to independent art/gallery/roster matching and a single combined publication per session.
- `webclient-gallery-panel`: clarify the selection contract's three-panel publication to match the management actions; retain its state ownership and retirement rules.

## Impact

- Implementation: `web/webclient/actions/gallery_actions.py`, `web/webclient/presentation/art_push.py`; reconcile the obsolete helper-level single-panel hint in `gallery_selection.py` without creating a second declaration owner. Registered panel names are exactly `gallery`, `art`, and `roster`; the dispatcher silently recovers unknown affected names with a full snapshot, so regression tests must assert `ui_update`, not merely fresh content.
- Extend existing `web/webclient/actions/tests/test_gallery_actions.py` and `web/webclient/presentation/tests/test_art_push.py`. Replace the stale tuple assertion at line 412 and the gallery-only `panel()` helper assertion at line 195; do not retain the obsolete contract as a parallel test. Keep existing module shard ownership and literal canonical `covers_requirement` IDs.
- `webclient-character-roster` owns portrait resolution, not completion delivery. Its contract and renderer remain unchanged; completion publication belongs in `webclient-art-panel`, which already owns the subscriber boundary.
- At implementation/sync time update the gallery-management main spec's Purpose, which currently promises only a gallery update, along with the delta requirements. No architectural design-document amendment is needed.
- These are `ui_action` surfaces, not typed player commands. `docs/game/commands.md` and `docs/game/command-reference.md` do not document gallery refresh behavior (the latter's staff `art status` entry is unrelated), so neither command document changes.
- Scope fits one engineer-day: two backend publication seams and focused existing-module regressions, with no worker settlement, portrait-resolution, schema, or frontend redesign.

## Batch:

```text
depends-on: none
code-conflict: square-face-rect-contract | web/webclient/actions/gallery_actions.py; web/webclient/actions/tests/test_gallery_actions.py; openspec/specs/webclient-gallery-management-actions/spec.md | shared files, distinct requirements; preserve square-validation deltas when integrating
code-conflict: configurable-http-user-agent | none | no overlapping planned implementation files or capability requirements
```

This is one self-contained change, not an implementation dependency on either active proposal. Artifacts are created only in this change directory; other workers' files remain untouched.
