# Proposal

## Why

The first combat update can commit participants without a fresh art catalog, so a foe's portrait reference has no matching entry. The shared stage renderer still draws a deprecated humanoid SVG when no fallback URL exists, despite the server already supporting `monster_anon`.

## What Changes

- Publish the fresh combat art catalog in the same authoritative revision as the initial combat participants. Cover UI engage, text command refresh, opening field casts, reconnect and later action/round updates without a client-generated species key or URL.
- **BREAKING** Remove the legacy standing humanoid SVG and its dead styling from every portrait fallback surface. No carried fallback or a failed fallback mask leaves truthful name/state text without an invented figure.
- Preserve the server-carried monster silhouette during missing/pending/failed imagery and image-load failure. Real species images remain visible when available and can arrive through the existing completion push.
- Replace overlapping lineup/silhouette assertions in existing suites and extend one real managed-browser engage/round journey, rather than adding cloned regressions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-art-panel`: first-combat reference/catalog coherence and explicit no-SVG degradation through the shared artwork component.
- `webclient-exploration-menu`: successful engage publishes art with participants in the same revision.
- `webclient-contextual-hud`: absent or failed mask renders identity/state text only; stage contours and accessible state remain unchanged.

## Impact

`web/webclient/actions/{exploration_actions,registry}.py`, existing coordinator/dispatcher publication tests, `world/rules/art_view.py` and art serialization tests, `ReferenceArtwork.vue`, FoeLineup/StageActor and their shared consumers/stories where old fallback behavior is asserted, and existing managed-browser combat/silhouette tests. Keep the art panel wire shape/version and OOB transaction mechanism. Any registry/adapter affected-panel declarations must agree.

## Non-goals

No inferred browser-side monster taxonomy, client-built fallback URL, new OOB channel, global snapshot rewrite, combat animation redesign, new gameplay mutation or image service dependency. No runtime payload inspection is claimed by this proposal.

## Batch:

```text
depends-on: fix-monster-species-portraits
code-conflicts: fix-monster-species-portraits (webclient-art-panel spec and test_art_panel.py; disjoint requirement blocks, serialize apply)
code-conflicts: exploration-presence-rail (AppClient.vue and shared exploration/browser helpers if integration requires edits)
code-conflicts: exploration-room-actions (AppClient.vue and shared exploration/browser helpers if integration requires edits)
```

No art-specific dependency on the three active resource-skill changes. The identity change must land first so the final acceptance exercises actual goblin provenance and species-specific cards. This publication/renderer slice is at most one engineer-day. Together the two changes deliver the entire reported fix; each remains independently reviewable.
