# Proposal

## Why

Long wilderness journeys need repeated whole-party camps without separate sleep, dream-answer and recovery clicks. The approved camping design makes each camp one wake-target decision while retaining deterministic sleep safety and owner-only dream consent.

## What Changes

- Add `until-dawn` using the next configured dawn anchor capped by maximum sleep, with text/browser parity and the 睡到天亮 / 天亮 tokens.
- **BREAKING**: permit explicit dream opt-in in accepted sleep entry. Camp supplies an explicit decline when unchecked; ordinary absent/false flags preserve the existing question policy.
- Add read-only `explore.camp_preview` with per-mode eligibility and transactional `explore.camp`, sharing existing party entry, dream answer and interruptible per-body continuation through the selected party's latest retained wake target.
- Add the camp card and skippable campfire beat, replace only the existing `openTravelCamp()` destination, and prepend the forced-walking-sleep handoff shortcut.
- Add text `camp [<mode>] [dream]` through the same camp operation. Update both command documents, operational traces and discoverable mechanism tests.

## Capabilities

### New Capabilities

- `wilderness-camping`: authoritative camp preview/action contracts, camp result publication and browser interaction state machine.

### Modified Capabilities

- `time-skip-commands`: dawn-target sleep and transport syntax including `camp`.
- `dream-sleep-surface`: explicit entry-time answer and guarded atomic owner opt-in; retain separate dream enter/decline.

## Impact

Implementation touches existing sleep rules/receipts, `server/dream_service.py`, text commands/cmdsets, exploration action validation/dispatch, matching browser protocol, AppClient travel/sleep integration and focused tests. No schema migration, compatibility transport or new clock stage is needed. One engineer-day vertical slice reuses party sleep, guarded dream answers, continuation, card framing and the travel log emitter contract; it does not redesign these owners.

Human review against `docs/superpowers/specs/2026-10-30-wilderness-camping-design.md` and `docs/design/wilderness-travel/` covers prose, medallion composition and visual fidelity. Tests establish mechanisms and transitions rather than shipped copy, art or markup snapshots.

Out of scope: night ambushes, watch rolls, ambient respawn cooldown, illustration production, sight/reveal/planning rules, and all sub-project 1/2 UI construction.

## Batch:

Camping rules have no dependency on sub-project 1. End-to-end browser integration consumes already-proposed sub-project 2 seams; this change does not implement those siblings.

```text
depends-on: wilderness-travel-leg-ui
depends-on: wilderness-travel-log-ui
```

| Active change | Dependency / code-conflict notes |
| --- | --- |
| wilderness-travel-interface | Transitive through leg/log; AppClient, travel view/store, protocol fixtures and browser manifests conflict. |
| wilderness-travel-map-ui | No direct dependency; medallion styling and AppClient shared. Use committed travel medallions without changing map behavior. |
| wilderness-travel-walking-ui | Transitive through leg; stop/cancel queue before opening camp, no queue redesign. |
| wilderness-travel-log-ui | Direct dependency for its closed `camp_result {summary}` event producer/consumer contract; serialize travel_events and coordinator integration. |
| wilderness-travel-leg-ui | Direct dependency for `openTravelCamp()` and the leg button; replace destination only. |
| wilderness-travel-window-ui | No dependency; AppClient, protocol/audit fixtures and manifests conflict. |
| wilderness-travel-planning-ui | No dependency; choices/input ownership and store conflict. |
| wilderness-travel-route-ui | No dependency; choices/input ownership and queue stop hook conflict. |
| wilderness-ground-reveal | No dependency; explicit skip commit hooks and clock-related tests conflict. Reuse landed hooks unchanged. |
| wilderness-map-disclosure | No dependency; exploration dispatcher/protocol fixtures conflict. Preserve anti-peek. |
| wilderness-area-map-reveal | No dependency; browser manifests/shared store integration conflict. |
| wilderness-travel-planning | No dependency; exploration action registry/validators conflict. |
| wilderness-travel-interrupts | No dependency; publication grouping/result completion and exploration adapters conflict. |

Serialize shared-file edits with their owners. Do not absorb, modify or replace sibling planning artifacts. Rules work can proceed in parallel with sight/reveal; apply the complete browser slice after the listed seams land.
