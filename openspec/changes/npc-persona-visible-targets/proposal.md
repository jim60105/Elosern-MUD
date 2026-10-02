## Why

P2-2: co-location alone currently publishes NPC interaction targets and admits persona reads/updates, even if visibility locks deny the actor. Design §8.1 requires a visible target, not merely a guessed room-content id.

## What Changes

- Use the existing Evennia room `filter_visible` policy consistently for bounded interaction publication and shared id-based presence resolution.
- Recheck visibility on every persona read and update; hiding an NPC after opening the editor invalidates saving without exposing private data.
- Preserve activated account-owned puppet authorization, ordinary-player access, exploration/dialogue modes, schedule-independent author editing, and existing failure codes.
- Limit shared changes to candidate filtering and necessary affected consumers; no visibility-system overhaul or privilege bypass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-persona-editor`: visibility revalidation and non-disclosing target rejection.
- `webclient-exploration-menu`: filter interaction targets before sorting/capping and resolve shared id targets through the same policy.

## Impact

One engineer-day: `web/webclient/presentation/exploration.py`, the necessary local-host candidate path in `presentation/affordances.py`, `web/webclient/actions/exploration_actions.py`, persona adapter tests and interaction publication tests. Persona authorization continues to use the dispatcher; no action payload or panel version change. No migrations, companion rewrite, bundle or LLM integration.

## Batch:

depends-on: none

Code-conflict notes: `web/webclient/actions/exploration_actions.py` is shared with `npc-offline-greeting-literal-output`; the common resolution helper and talk-open output are different hunks but must be integrated sequentially. Persona action tests may overlap Unicode/greeting tests; the `npc-persona-editor` deltas add separate requirements. No semantic dependency on the other fixes.
