# Tasks: Public-Act Social Events (被觀看 / 露出 / 公開性行為)

> Implementation order note: this change SHALL be implemented and archived **after**
> `sexual-intercourse-acts` — both edit `world/rules/action.py` event handling and the
> `_act_family()` effects shape. The delta requirement blocks below are written against the
> post-`sexual-intercourse-acts` main specs.

## 1. Engine — actor-scoped event channel

- [ ] 1.1 Add `_ACTOR_SCOPED_EVENTS = frozenset({"self_exposure", "public_exposure",
      "watched_during_activity", "public_sexual_activity"})` to
      `world/skills/sexual_acts/_builder.py` beside `_FORBIDDEN_SEXUAL_EVENTS`.
- [ ] 1.2 Extend `_act_family()`'s effect emission: a declared event name in `_ACTOR_SCOPED_EVENTS`
      emits `sexual_event_actor:<name>`, any other name emits `sexual_event:<name>`, preserving
      declaration order.
- [ ] 1.3 Add `world/skills/effects.py` `parse_effect` support for the `sexual_event_actor` prefix
      with a single-argument payload, mapping to a new typed effect (e.g.
      `ActorSexualEventEffect`).
- [ ] 1.4 Add `_handle_actor_sexual_event` in `world/rules/action.py`: stage one `PendingEffect`
      calling `apply_event(actor, event_name, **sexual_context)` — never for any target — with the
      shared `sexual_transition` description kind; register the `sexual_event_actor` prefix
      (surfaces `frozenset({"sexual"})`, no required event context).

## 2. Engine — observer presence and gating

- [ ] 2.1 Inject `event_context["room"]` in `RoomActionContext.__init__`
      (`world/rules/targeting.py`), overwriting any caller-supplied value.
- [ ] 2.2 Add `observers_present(actor, targets, event_context) -> bool` to
      `world/rules/sexual_act_effects.py` per design D-2 (non-actor target → observed; battlefield
      roster or `LivingEntity` room occupants otherwise; missing context → `False`).
- [ ] 2.3 Add `_OBSERVER_GATED_EVENTS = frozenset({"watched_during_activity"})` and
      `_OBSERVER_GATED_COUNTERS = frozenset({"watched_count"})` to `world/rules/sexual_act_effects.py`.
- [ ] 2.4 Gate `watched_during_activity` in the actor-scoped event handler: skip the event when
      `observers_present()` is false.
- [ ] 2.5 Gate `watched_count` in `_handle_sexual_counter_effect`
      (`world/rules/action.py`): skip the counter name when `observers_present()` is false, staging
      every other declared counter.

## 3. Catalog — shame line event declarations

- [ ] 3.1 `shame_hem_lift`, `shame_half_expose_chest`, `shame_half_expose_lower`,
      `shame_loosen_collar`, `shame_full_expose`: `sexual_events=("self_exposure",
      "public_exposure")`.
- [ ] 3.2 `shame_public_masturbation`: `sexual_events=("self_exposure", "public_exposure",
      "public_sexual_activity", "masturbation_climax", "watched_during_activity")`.
- [ ] 3.3 `shame_public_performance`: `sexual_events=("self_exposure", "public_exposure",
      "public_sexual_activity", "watched_during_activity")`.
- [ ] 3.4 `shame_devoted_pose`: `sexual_events=("self_exposure", "public_exposure",
      "watched_during_activity")` (no `public_sexual_activity`).
- [ ] 3.5 `shame_shameless_declaration`: `sexual_events=("self_exposure", "public_exposure",
      "public_sexual_activity", "watched_during_activity")`.
- [ ] 3.6 `shame_provocative_gaze`: unchanged (`sexual_events=()`).

## 4. Tests

- [ ] 4.1 Structural tests: channel classification (each declared event resolves to exactly one
      channel, in order; `_ACTOR_SCOPED_EVENTS` members are real `sexual.yaml` events),
      `_OBSERVER_GATED_EVENTS ⊆ _ACTOR_SCOPED_EVENTS`, and
      `_OBSERVER_GATED_COUNTERS ⊆ _COUNTER_MUTATORS` keys (annotate with `covers_requirement`).
- [ ] 4.2 `observers_present` unit tests: AREA target list, SELF alone/occupied room, empty
      battlefield, missing context (annotate).
- [ ] 4.3 Gating tests: an unobserved cast skips `watched_during_activity` and `watched_count`
      while staging all other events/counters; an observed cast fires both (annotate).
- [ ] 4.4 Actor-channel tests: `sexual_event_actor:self_exposure` reaches the actor and never a
      target; the AREA `self_exposure` scenario flips to the performer (annotate).
- [ ] 4.5 Shame catalog tests (annotate): every shame act's declared event tuple per tasks 3.x;
      公開自慰 alone-vs-observed counter/experience outcomes; 公開表演 performer experiences; the
      public-vocabulary scenarios.
- [ ] 4.6 `RoomActionContext` injection tests (annotate): constructed context carries `"room"`,
      caller-supplied key overwritten.
- [ ] 4.7 Run `uv run --locked python -m tools.spec_traceability check` and the affected package
      tests (`world.rules.test_sexual_act_effects`, `world.skills.sexual_acts.tests`,
      `world.rules.tests.test_cast_settlement`, `world.rules.tests.test_combat_session_flow`).

## 5. Spec sync and validation

- [ ] 5.1 Run `openspec validate --change sexual-public-act-events --strict` and resolve any
      delta-spec or traceability failures.
- [ ] 5.2 Confirm `git diff --check` is clean.
