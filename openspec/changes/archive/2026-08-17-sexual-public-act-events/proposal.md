# Proposal: Public-Act Social Events (被觀看 / 露出 / 公開性行為)

## Why

Three shipped `sexual.yaml` rules still have no production emitter after the act catalog landed:
`watched_during_activity` (experience 被觀看 + `shame_up_on_watched`), `public_exposure`
(experience 露出), and `public_sexual_activity` (`shame_up_on_public_sexual_activity`). The shame
catalog emits only `self_exposure`, and two documented engine gaps stand in the way of fixing it:
acts' events never reach the performing actor (shame design.md D-6's disclosed gap — the AREA
performer never accrues the exposure cost), and `watched_count` credits unconditionally instead of
"when observed" (shame design.md D-4's documented deferral of a room-occupancy read). The 被觀看/露出
experience types can therefore never be granted and the shame-cascade rules for watched/public
activity never fire.

## What Changes

- **Actor-scoped event channel**: a new `sexual_event_actor:<name>` effect prefix whose handler
  applies the named event to the **actor only**. Performer-scoped events (`self_exposure`,
  `public_exposure`, `watched_during_activity`, `public_sexual_activity`) move to this channel;
  participant-scoped events (`breast_sex_performed`, `masturbation_climax`,
  `sexual_activity_with_nonhuman`) stay on `sexual_event:<name>`.
- **Observer presence read**: a deterministic `observers_present()` helper in
  `world/rules/sexual_act_effects.py` — AREA casts are observed by construction (their targets are
  the audience); SELF casts are observed when a co-located entity other than the actor exists
  (battlefield roster members, or room occupants when out of combat). `RoomActionContext` injects
  `event_context["room"]` so the out-of-combat read works without a new handler surface.
- **Observer-gated application**: `watched_during_activity` and the `watched_count` counter fire
  only when `observers_present()` is true (module constants `_OBSERVER_GATED_EVENTS` and
  `_OBSERVER_GATED_COUNTERS` in the effects module). This restores the source design's "when
  observed" semantics for both the experience event and the 被觀看次數 unlock ladder.
- **Catalog**: the shame acts gain the public events — every shame act emits `public_exposure`
  (the exposure axis, mirroring the unconditional 露出次數 counter); 公開自慰, 公開表演, 無恥宣言 and
  獻身姿態 additionally emit `watched_during_activity` when observed; the three explicitly sexual
  public acts (公開自慰, 公開表演, 無恥宣言) emit `public_sexual_activity`. `self_exposure` moves to the
  actor-scoped channel, fixing the shame D-6 performer gap.
- Fixes, in one place, the shame D-4 and D-6 documented deferrals; no `sexual.yaml` changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `sexual-act-effects`: the actor-scoped `sexual_event_actor:<name>` handler; the
  `observers_present()` presence read; observer-gated application of `watched_during_activity` and
  `watched_count`.
- `sexual-act-registry`: `_act_family()` effect-shape contract gains the actor-scoped event entry;
  acts declaring actor-scoped events are structurally constrained.
- `sexual-catalog-shame`: the ten shame acts' event declarations — `self_exposure` re-scoped to the
  actor, `public_exposure` on every shame act, `watched_during_activity` (observed) and
  `public_sexual_activity` on the four public acts.
- `targeting-validation`: `RoomActionContext` guarantees an `event_context["room"]` entry.

## Impact

- `world/rules/targeting.py` — `RoomActionContext` room injection (one line).
- `world/skills/sexual_acts/_builder.py` — actor-scoped event effect emission; validation.
- `world/skills/sexual_acts/shame.py` — event declarations per act.
- `world/rules/sexual_act_effects.py` — `observers_present()` and the observer-gated name tables.
- `world/rules/action.py` — `sexual_event_actor:` handler; observer gating in the event and counter
  handlers.
- `world/skills/effects.py` — typed parse for the new prefix.
- Tests: presence helper unit tests, gating tests (observed/unobserved casts), shame catalog
  event-scope tests.
- Spec deltas: `sexual-act-effects`, `sexual-act-registry`, `sexual-catalog-shame`,
  `targeting-validation`.
