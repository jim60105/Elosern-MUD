# Design: Public-Act Social Events (被觀看 / 露出 / 公開性行為)

## Context

Three `sexual.yaml` rules remain without a production emitter after the catalog landed:
`watched_during_activity` (experience 被觀看, `shame_up_on_watched`), `public_exposure` (experience
露出), and `public_sexual_activity` (`shame_up_on_public_sexual_activity`). The shame catalog
(archived 2026-08-16) documented why: acts' events reach targets only, never the performing actor
(D-6: an AREA cast's `self_exposure` lands on the audience, so the performer never accrues the
exposure cost), and `watched_count` credits unconditionally because no room-occupancy read exists
(D-4: "Building the latter would need a new room-occupancy read inside the counter-effect handler —
`sexual-act-effects`'s territory, out of scope here"). Both documents name this follow-up
explicitly; this change is that follow-up.

## Goals / Non-Goals

**Goals:**
- Add an actor-scoped event channel (`sexual_event_actor:<name>`) so performer-scoped events land
  on the actor, and re-scope `self_exposure` to it — fixing the shame D-6 performer gap and
  removing the disclosed audience-receives quirk.
- Add the deterministic `observers_present()` read (battlefield roster, or room occupants via a
  new `RoomActionContext` event-context injection) and gate `watched_during_activity` and
  `watched_count` on it — restoring the source design's "when observed" for both the experience
  event and the 被觀看次數 unlock ladder.
- Wire the three public events onto the shame line: `public_exposure` on every shame act (the
  exposure axis, mirroring the unconditional 露出次數 counter), `watched_during_activity` on the
  four public acts, `public_sexual_activity` on the three explicitly sexual public acts.

**Non-Goals:**
- No `sexual.yaml` rulebook changes.
- No changes to the 露出次數 counter's unconditional crediting (the exposure axis is not
  observer-based by design).
- No room-occupancy gating for any other counter or event; no observer *identity* tracking.
- The stimulus-family events stay without act emitters: `stimulus_applied`,
  `sustained_stimulus_applied`, and `extreme_stimulus_applied` are forbidden to acts by
  `_builder.py`'s `_FORBIDDEN_SEXUAL_EVENTS` (the pleasure handler already applies their effects),
  while `direct_stimulus_applied` and `frequent_stimulation` are simply not declared by any shipped
  act — `frequent_stimulation` (sensitivity training) is reserved for a future proposal. The
  forbidden-set contract itself is unchanged by this proposal.

## Decisions

### D-1: Event scope is a property of the event name, declared once in `_ACTOR_SCOPED_EVENTS`

`_builder.py` gains `_ACTOR_SCOPED_EVENTS = frozenset({"self_exposure", "public_exposure",
"watched_during_activity", "public_sexual_activity"})` beside `_FORBIDDEN_SEXUAL_EVENTS`; the
builder emits `sexual_event_actor:<name>` for names in the set and `sexual_event:<name>` otherwise.
The catalog rows keep the single `sexual_events` tuple — no new per-row field, no row churn, and a
catalog author cannot accidentally mis-scope an event.

**Rejected — a per-act `actor_sexual_events` field.** Two fields carrying the same vocabulary would
create a second source of truth and let rows disagree with the event's semantics; a name-keyed
table makes the scope structural and testable.

### D-2: `observers_present()` is a pure, no-create read over event_context

The helper reads only `event_context["battlefield"]` (combat — already injected by
`BattlefieldActionContext`) or `event_context["room"]` (out of combat — newly injected by
`RoomActionContext`) and the cast's own targets; it never materializes the `sexual` handler and
never writes. The rule: a target list containing a non-actor (an AREA cast's audience, or a SINGLE
cast's partner — the "in someone's presence" reading, matching the pleasure model's third-party
definition closely enough that no shipped SINGLE act is gated) counts as observed; otherwise any
co-located non-actor entity (roster member, or `LivingEntity` room occupant — exits and items are
excluded) counts. An absent context reads `False` (unobserved), so callers that never construct the
new keys behave exactly as before.

**Rejected — computing presence in `ActionResolver.resolve()` and threading it through.** The
event-context injection keeps the read co-located with the balance helpers and avoids a second
contract on the resolver's signature.

### D-3: Gating is name-keyed through `_OBSERVER_GATED_EVENTS` / `_OBSERVER_GATED_COUNTERS`

`watched_during_activity` and `watched_count` are semantically observer-gated by definition; a
module-level frozenset pair in `sexual_act_effects.py` names them, and the actor-scoped event
handler and the counter handler each skip the gated name when `observers_present()` is false. The
skip is silent (other counters/events still stage) and staged at resolution time, before any
snapshot, so an unobserved cast touches no state it shouldn't. A structural test pins both sets as
subsets of `_ACTOR_SCOPED_EVENTS`.

**Rejected — per-act gating flags.** Whether the event fires depends on the event's own semantics,
not on the act that declares it; a name-keyed table cannot drift between acts.

### D-4: `self_exposure` becomes actor-scoped; the AREA audience quirk is removed

The shame D-6 note invited this revisit. With the actor channel, `self_exposure` fires on the
performer only: the performer's `exposure` rises (feeding `shame_up_on_exposure_increase` and, at
high exposure, the shipped `high_exposure_defense_penalty` — the exact cost the note said the
performer "never accumulates"), and the audience no longer receives an exposure bump it was never
designed to receive. The pinned test and delta scenario flip accordingly. For SELF acts the
behavior is unchanged (recipient was already the actor).

### D-5: The public-event mapping

- **`public_exposure`** — every shame act except 挑釁凝視 (the exposure axis; unconditional,
  mirroring 露出次數).
- **`watched_during_activity`** — the four public acts (公開自慰, 公開表演, 獻身姿態, 無恥宣言);
  observer-gated for the SELF casts, always observed for the AREA casts (their audience is the
  target set, guaranteed non-empty by targeting).
- **`public_sexual_activity`** — the three explicitly sexual public acts (公開自慰, 公開表演,
  無恥宣言); 獻身姿態 is a pose, not a sexual activity, and stays out.
- 挑釁凝視 keeps `sexual_events=()`.

The `watched_count` counter stays gated by the same read, so the 被觀看次數 ladder (公開表演 at 10,
無恥宣言 at 30) becomes a genuinely social progression — the source design's "when observed".

## Risks / Trade-offs

- **[Risk] Gating `watched_count` changes the shame ladder's pacing.** A player must now seek
  audiences; solo grinding no longer advances 被觀看次數. This is the source design's intent
  ("any act resolves with a third party present"; 公開自慰 "when observed"), and the delta spec
  pins it — accepted as the designed behavior.
- **[Risk] `observers_present` counts every co-located entity, including hostile ones.** Being
  watched by a monster is still being watched; the pleasure model defines the counter on presence,
  not on goodwill. Accepted.
- **[Risk] `RoomActionContext`'s injected `room` key could collide with a caller's key.** The
  injection overwrites unconditionally (documented; a caller-supplied `"room"` was meaningless
  before), and the delta spec pins the overwrite.
- **[Risk] Serialization with `sexual-intercourse-acts`**: both changes edit `world/rules/action.py`
  event handlers and the `_act_family()` effects shape. This change builds on that change's
  participant semantics — it SHALL be implemented and archived after it, and its delta
  requirement blocks are written against the post-`sexual-intercourse-acts` main specs.
- **[Trade-off] The stimulus-family events stay un-emitted.** Documented in Non-Goals: three of
  them are forbidden in acts by design (`_FORBIDDEN_SEXUAL_EVENTS`), and `frequent_stimulation`
  (sensitivity training) is reserved for a future proposal rather than bolted onto this one.

## Migration Plan

No migration: no released users. Existing saves are unaffected; acts' event declarations change
only in the registry data.

## Open Questions

None.
