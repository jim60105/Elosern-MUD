# Tasks: Sexual Intercourse Acts (交合 / 深度交合)

## 1. Engine — SexualActDef pair_events

- [ ] 1.1 Add `pair_events: tuple[tuple[tuple[str, str], str], ...] = ()` to `SexualActDef` in
      `world/skills/sexual_acts/_builder.py` and pass it through from `_act_family()` rows.
- [ ] 1.2 Extend `_act_family()`'s row unpacking to accept exactly 13 or 14 fields (14th =
      `pair_events`, default `()`), raising `ValueError` naming the row for any other length.
- [ ] 1.3 Add `_act_family()` validation for a non-empty `pair_events`: `target_spec` must be
      `TargetSpec.SINGLE`; every entry must be a sorted two-member sex tuple drawn from
      `world.lore.sex.SEX_VALUES` with no repeated pair; every event name must be outside
      `_FORBIDDEN_SEXUAL_EVENTS`. Fail closed naming the offending key.
- [ ] 1.4 Emit `f"act_pair_event:{key}"` as the trailing effect entry exactly when the row declares
      a non-empty `pair_events`.
- [ ] 1.5 Add `world/skills/effects.py` `parse_effect` support for the `act_pair_event` prefix with
      a single-argument payload, mapping to a new typed effect (e.g. `PairEventEffect`).
- [ ] 1.6 Add `_LEGACY_TARGET_SCOPED_EVENTS = frozenset({"stimulus_applied"})` to
      `world/skills/sexual_acts/_builder.py`, documented as distinct from `_FORBIDDEN_SEXUAL_EVENTS`.

## 2. Engine — event recipient semantics

- [ ] 2.1 Change `_handle_sexual_event` in `world/rules/action.py` to iterate
      `participants(actor, targets)` for event names outside `_LEGACY_TARGET_SCOPED_EVENTS`, keeping
      the historic target-scoped iteration for names inside it; document the legacy exception (D-9)
      in the handler docstring.
- [ ] 2.2 Add `pair_event_name(actor, targets, act) -> str | None` to
      `world/rules/sexual_act_effects.py` (reads `sex` per participant with
      `DEFAULT_SEX` fallback, sorts the pair, first exact match, `None` otherwise).
- [ ] 2.3 Add `_handle_act_pair_event` to `world/rules/action.py`: resolve the act by the payload
      key (reusing `_resolve_act`), reject an absent act, resolve the event, stage no effect when
      `None`, otherwise stage one `PendingEffect` per participant of `participants(actor, targets)`
      applying `apply_event(participant, event)` with the shared `sexual_transition` description
      kind.
- [ ] 2.4 Register the `act_pair_event` prefix in `world/rules/action.py` (surfaces
      `frozenset({"sexual"})`, no required event context).

## 3. Catalog — 交合 and 深度交合

- [ ] 3.1 Add `partner_vaginal_sex` (交合) to `world/skills/sexual_acts/partner.py` as a Tier-3 row:
      `unlock={"duo_act_count": 30, "climax_count": 10}`, part 私處/私處, `base_pleasure=28`,
      `actor_pleasure_ratio=0.6`, `duo_act_count` on both sides, `resistible=True`, no
      `sexual_events`, and the canonical three-pair `pair_events` table.
- [ ] 3.2 Add `partner_deep_vaginal_sex` (深度交合) identically except `base_pleasure=34` and
      `actor_pleasure_ratio=0.9`.

## 4. Tests

- [ ] 4.1 Structural registry tests: `pair_events` validation failures (non-SINGLE, unsorted/unknown
      sex pair, forbidden event, repeated pair) and the assembled-registry event-existence check
      covering `pair_events` event names (annotate with `covers_requirement`).
- [ ] 4.2 `_act_family()` effect-shape tests: trailing `act_pair_event:<key>` entry present exactly
      for pair-event rows, and 13/14-field row-length guard.
- [ ] 4.3 `_handle_sexual_event` recipient tests: a two-party act's declared event reaches the actor
      and the target; the legacy `divine_sexual_arts` cast reaches the target only; a structural test
      asserts `_LEGACY_TARGET_SCOPED_EVENTS` is disjoint from every act's declared event names.
- [ ] 4.4 `pair_event_name` unit tests: opposite / both-female / both-male / other-or-unknown
      (including a `Monster` target) resolutions; `None` for unmatched.
- [ ] 4.5 Full D-12 acceptance tests (annotated): opposite-sex cast breaks `virgin` on both parties
      and credits `陰道性交` to both; same-sex casts never break `virgin` and credit the matching
      experience; `other`/unknown and monster casts emit no event and break nothing.
- [ ] 4.6 Catalog tests: both acts unlock at the compound gate, credit `duo_act_count` on both
      sides, are resistible, and the baseline gain-gap scenario (深度交合 actor-side gap strictly
      larger than its target-side gap).
- [ ] 4.7 Run `uv run --locked python -m tools.spec_traceability check` and the affected package
      tests (`world.skills.sexual_acts`, `world.rules.test_sexual_act_effects`,
      `world.rules.test_sexual_resist_cast_wiring`).

## 5. Spec sync and validation

- [ ] 5.1 Run `openspec validate --change sexual-intercourse-acts --strict` and resolve any
      delta-spec or traceability failures.
- [ ] 5.2 Confirm `git diff --check` is clean.
