## Context

Change 7 (`sexual-state`) built `entity.sexual` — a live, comparable `SexualState` handler — but
authored no rule that moves it. Change 6 (`buffs-rulebook`) built the shared condition grammar
(`Rule`, `load_rules()`, `evaluate_condition()`) `sexual.yaml` is contractually required to reuse,
and left `then` opaque specifically so this table can define its own effect vocabulary. This design
covers exactly that: the ~24 rows of `rulebook/sexual.yaml`, the module that interprets their `then`
clauses against `SexualState`'s public surface, and the test discipline that makes "every rule has a
test" and "every field is reachable" structurally checked rather than merely followed.

Change 7's design doc D-7 already analyzed `tmp/story_settings/variable_rule.md` for ambiguity and
one direct self-contradiction, with resolutions this design inherits verbatim (virginity's trigger
event, `達臨界點`'s interpretation, wetness's `至少提升1級` split, every race-specific exclusion, every
narrative-only field exclusion). This document does not repeat that analysis; it only adds the
handful of additional ambiguities D-7 did not cover, because they concern fields or transitions D-7
was not scoped to walk line-by-line.

## Goals / Non-Goals

**Goals:**
- `world/rules/rulebook/sexual.yaml`: ~24 rules, each with a unique `id`, transcribing every
  behaviourally-meaningful line of `variable_rule.md`'s `性狀態.*` section not already excluded by
  D-7 or by this document's own additional resolutions (below).
- `world/rules/sexual_transitions.py`: `FIELD_KINDS`, `_parse_delta()`, `_apply_then()`,
  `_build_context()`, and `apply_event(entity, event, **event_context)` — the interpreter for
  `sexual.yaml`'s `then` vocabulary, built entirely on `SexualState`'s public property surface and
  change 6's `evaluate_condition()`. No second condition evaluator.
- `apply_event()`'s fixed-point loop: one call can trigger a short cascade (e.g. `arousal_up_on_
  stimulus` raises `arousal` to `極限`, which `climax_gate` then reacts to in the same call) without
  re-firing a rule for a field-change that already fully propagated, and without looping forever.
- One `test_rule_<id>()` per rule ID (structurally enforced — `test_every_rule_id_has_a_test()`),
  plus `test_field_kinds_covers_every_targetable_field()`, plus direct tests of both irreversibility
  guarantees (`virgin`, `experience_types`) and of `climax_phase`'s guard-routing discipline.

**Non-Goals:**
- No re-derivation of D-7's resolutions. Every resolution D-7 already states is used as-is.
- No race-specific rule (elf rapid recovery, elf sensitivity floors, elf 餘韻→接近 re-entry) — per
  D-7, these are a future `buffs.yaml` entry's job, not a row in this table.
- No narrative-only field (身體感受, 興奮要素, 被注視感受, 最後性活動, 基本資訊.狀態) — per D-7,
  Narrator/PersonaStore material, not a `SexualState` field.
- No `ActionResolver`, targeting, or command wiring (change 8) — `apply_event()` is a plain callable
  this design hands to change 8 to call; no player command is bound to any event name here.
- No combat resolution (change 9) and no settlement order (change 11) — `decay_tick()`/
  `reset_daily_counters()` remain change 7's exposed callables, invoked at change 11's own chosen
  point; nothing here calls them, competes with them, or re-derives their ordering.
- No sexual-magic buff instance or SP/exhaustion coupling — those are change 6's `buffs.yaml` and
  change 8's resource-deduction step respectively, per change 7's design doc Non-Goals, which this
  design does not revisit.

## Decisions

### D-1. The `then` effect vocabulary: `field` + one of `delta` / `set` / `add`, dispatched by
`FIELD_KINDS`.

Six field *kinds* exist, each with a different legal effect shape and a different write path onto
`SexualState`'s public surface:

```python
# world/rules/sexual_transitions.py
FIELD_KINDS = {
    "arousal":          "ordered_level",
    "wetness":          "ordered_level",
    "shame":             "ordered_level",
    "exposure":         "ordered_level",
    "climax_phase":     "ordered_level_cyclic",   # routes through _apply_climax_phase_set() only
    "sensitivity":      "ordered_level_dict",     # part-keyed; needs context["part"]
    "climax_today":     "counter",                # plain int; see D-5 for its write-path gap
    "virgin":           "flag_one_way",           # entity.sexual.virgin = False only
    "experience_types": "append_only_set",        # entity.sexual.add_experience_type(key) only
}
```

- **`ordered_level`** (`arousal`/`wetness`/`shame`/`exposure`): `then` carries either `delta` (a
  string parsed by `_parse_delta()` — see D-2) or `set` (an absolute vocabulary string). Both write
  through the trait object the field's own property returns
  (`entity.sexual.arousal.value = ...`) — this is the object the public property hands back, not a
  reach into `SexualState._traits`; mutating an object you were legitimately given is not the
  private-handler bypass D-2 of change 7 warns against. `set` resolves the target string via the
  trait's own public `.levels` tuple (`trait.levels.index(target)`), which raises `ValueError` on a
  typo — the same "loud, not silent" contract change 7's `ordered-level-trait` capability already
  requires of every comparison; this design does not add a second, quieter path.
- **`ordered_level_cyclic`** (`climax_phase` only): `then` carries only `set`. `_apply_then()`
  special-cases this one field kind to call `_apply_climax_phase_set(entity, target)` — change 7's
  sole permitted write path — never writing `entity.sexual.climax_phase.value` directly, satisfying
  hard requirement 3. Because the guard itself already no-ops an invalid or repeated transition
  (change 7's D-4), a rule whose condition remains true across several fixed-point passes (e.g.
  `climax_gate`'s `{field: arousal, equals: 極限}`) cannot walk `climax_phase` backwards or loop —
  the second and later calls simply no-op. No rule in this table conditions on `climax_phase`'s
  `field_changed` direction, since "up"/"down" is undefined for a cyclic field (change 7's D-4
  states this plainly); every `climax_phase` read in a `when` block uses `equals` or `gte` only.
- **`ordered_level_dict`** (`sensitivity`): `then` carries `delta` only (no `set` rule exists in
  `variable_rule.md` for sensitivity — every trigger is "frequent stimulation raises it," never "set
  to a specific level"). The target part is not in the rule at all; it comes from the *event*, via
  `context["part"]`, populated from `apply_event()`'s `**event_context` kwargs. `_apply_then()`
  raises (loud, not silent) if a `sensitivity`-kind rule fires with no `part` in context — a rule
  matching with nothing to apply the delta to is a caller bug, not a silently-ignored no-op. Write
  path: `entity.sexual.sensitivity[part].value += delta` — again, the object `.sensitivity[part]`
  hands back, not a private reach-around (see D-3's discussion of why this is the single generic
  rule design.md's D-3 for change 7 already named by ID).
- **`counter`** (`climax_today`): `then` carries `delta` only, applied as plain integer addition (no
  ordinal, no clamp). See D-5 for the write-path gap this field's read-only public property creates,
  and the proposed minimal resolution.
- **`flag_one_way`** (`virgin`): `then` carries only `{"set": false}` (transcribed from design doc
  §6.4's own worked example, which also carries a documentary `irreversible: true` key — kept in the
  YAML for fidelity to that example, but `_apply_then()` does not need to read it: irreversibility is
  already structurally enforced by `SexualState.virgin`'s own setter, per change 7's D-2. This
  table's job is only to decide *when* the event fires, never to re-implement the guard.
- **`append_only_set`** (`experience_types`): `then` carries `add` (a single Chinese type string).
  Write path: `entity.sexual.add_experience_type(add_value)` — change 7's documented sole mutator.

**Alternative considered**: one universal `{field, op, value}` triple for every kind. Rejected —
`sensitivity`'s dynamic part-key and `climax_phase`'s guard indirection are genuinely different
shapes, not a naming variance on one shape; forcing them into an identical grammar would either give
`sensitivity` and `climax_phase` rows a `part`/`guard` key that every other row's schema silently
ignores, or push kind-dispatch logic into `sexual.yaml` itself (which change 6's D-1 already
rejected doing to `then` in general). A `FIELD_KINDS` lookup table, read once at rule-table load
time by `_apply_then()`, keeps every row's YAML shape exactly as small as its own kind needs.

### D-2. `_parse_delta()`: fixed and random-range deltas, mirroring design doc §6.4's own
`"+1..+2"` example verbatim.

```python
def _parse_delta(spec: str) -> int | tuple[int, int]:
    """"+1" / "-1" -> int. "+1..+2" -> (1, 2), resolved via rng.randint() at apply time.
    Raises ValueError on any other shape -- a malformed delta string in sexual.yaml
    should fail at rule-table load time, not silently apply zero."""
```

`apply_event()` accepts an optional `rng` (defaulting to the `random` module), the same seam design
doc §10's "fixed seed, deterministic assertions" testing discipline for dice/combat already
establishes elsewhere in this project — every per-rule test exercising a range delta passes a
`random.Random(<fixed seed>)` or a stub exposing `.randint()`, never asserting against a live,
unseeded random draw.

### D-3. `_build_context()` and `apply_event()`'s fixed-point loop.

```python
def _build_context(entity, event: str | None, changed: dict, event_context: dict) -> dict:
    return {
        "event": event,                       # None on every pass after the first
        "arousal": entity.sexual.arousal,      # live OrderedLevelTrait -- gte/equals
        "wetness": entity.sexual.wetness,      # work for free per change 7's D-1
        "shame": entity.sexual.shame,
        "exposure": entity.sexual.exposure,
        "climax_phase": entity.sexual.climax_phase,
        "climax_today": entity.sexual.climax_today,
        "virgin": entity.sexual.virgin,
        "experience_types": entity.sexual.experience_types,
        "_changed": changed,                  # this pass's field_changed directions only
        **event_context,                      # e.g. part="乳房" for a sensitivity event
    }

def apply_event(entity, event: str, *, rng=None, max_passes: int = 50, **event_context) -> dict:
    """Runs sexual.yaml's rules to a fixed point. Pass 1 evaluates with the real
    event name; every later pass clears it to None so an event-conditioned rule
    fires exactly once per apply_event() call, never once per cascade pass."""
    rng = rng or random
    changed_this_pass: dict[str, str] = {}
    all_changes: dict[str, str] = {}
    current_event = event
    for _ in range(max_passes):
        context = _build_context(entity, current_event, changed_this_pass, event_context)
        changed_this_pass = {}
        for rule in _RULES:
            if evaluate_condition(rule.when, context):
                field, direction = _apply_then(entity, rule.then, context, rng)
                if field is not None:
                    changed_this_pass[field] = direction
                    all_changes[field] = direction
        if not changed_this_pass:
            break
        current_event = None   # only pass 1 sees the originating event
    return all_changes
```

**Why `_changed` holds only the immediately-preceding pass's deltas, not every change accumulated
across the whole call.** A field-changed-conditioned rule (`wetness_follows_arousal`) must fire
exactly once per underlying arousal rise, not once per remaining fixed-point pass while arousal sits
at its new level unchanged. Resetting `_changed` every pass to hold only that pass's own deltas gives
termination for free: once a pass produces zero changes, the loop stops; a rule keyed on a field that
stopped changing two passes ago no longer matches, because `_changed` no longer mentions it. Every
ordered-level field is bounded (`OrderedLevelTrait` clamps, per change 7's D-1), so even a cascade
that walks a field to its ceiling converges in at most `len(levels) - 1` passes for that field, well
under `max_passes`; `max_passes` is a defensive ceiling against a future rule author introducing a
genuine two-rule oscillation, not a value this table's current 24 rules are expected to approach.

**Why event-conditioned rules only fire on pass 1.** If `current_event` stayed set across every
pass, an event rule would refire on every subsequent pass for the remaining lifetime of the
cascade (there is nothing that "un-happens" an event), which is not what "首次...時" (upon first...)
or "...時提升" (rises upon...) mean in `variable_rule.md` — each describes a discrete occurrence, not
a persisting condition. Clearing the event after pass 1 is what makes an event rule fire exactly
once per `apply_event()` call, matching the source text's own one-shot phrasing.

**Alternative considered**: a single evaluation pass, with no cascade at all (every rule sees only
the state that existed when `apply_event()` was called). Rejected — this would make `climax_gate`
(reacts to `arousal` reaching `極限`) never fire on the same call that `arousal_up_on_stimulus` or
`arousal_extreme_stimulus_to_max` pushes `arousal` there, forcing every caller to invoke
`apply_event()` twice per meaningful action and to know, ahead of time, which rules chain into which
— exactly the coupling a declarative rule table exists to avoid.

### D-4. Rule catalog — 24 rules, organized by field, each mapped to its `variable_rule.md` source
line and, where relevant, its D-7 resolution.

| # | Rule ID | `when` | `then` | Source line |
|---|---|---|---|---|
| 1 | `arousal_up_on_stimulus` | `event: stimulus_applied` | `field: arousal, delta: "+1..+2"` | 「接受性刺激…時提升1-2級」— transcribed verbatim from design doc §6.4's own worked example |
| 2 | `arousal_up_on_sustained_stimulus` | `event: sustained_stimulus_applied` | `field: arousal, delta: "+1"` | 「持續刺激經過合理時長後再提升1級」— see D-6 for this rule's own ambiguity resolution |
| 3 | `arousal_extreme_stimulus_to_max` | `event: extreme_stimulus_applied` | `field: arousal, set: 極限` | 「極端刺激…可直接躍升至「極限」」 |
| 4 | `arousal_reset_after_climax` | `event: climax_ends` | `field: arousal, set: 微興奮` | 「高潮後短暫降至「微興奮」」(elf rapid-recovery clause excluded per D-7) |
| 5 | `wetness_follows_arousal` | `field_changed: arousal, direction: up` | `field: wetness, delta: "+1"` | 「性喚起每提升1級，濕潤程度至少提升1級」— D-7's two-rule split, half 1 |
| 6 | `wetness_up_on_direct_stimulus` | `event: direct_stimulus_applied` | `field: wetness, delta: "+1..+2"` | 「接受直接刺激時快速提升」— D-7's two-rule split, half 2 |
| 7 | `wetness_max_on_climax` | `event: climax_ends` | `field: wetness, set: 泛濫` | 「高潮時達到「泛濫」」 |
| 8 | `sensitivity_up_on_frequent_stimulation` | `event: frequent_stimulation` | `field: sensitivity, delta: "+1"` (part from event context) | 「頻繁刺激可逐步提升（長期變化）」(乳房.敏感度 and 私處.敏感度 identical wording — one generic, part-agnostic rule; named by this exact ID in change 7's own design.md D-3) |
| 9 | `climax_gate` | `field: arousal, equals: 極限` | `field: climax_phase, set: 接近` | 「性喚起達至「極限」時轉為「接近」」— transcribed verbatim from design doc §6.4's own worked example (identical `id`) |
| 10 | `climax_phase_critical_point_to_in_progress` | `field: climax_phase, equals: 接近, event: stimulus_applied` | `field: climax_phase, set: 進行中` | 「達臨界點時轉為「進行中」」— D-7's exact carried-forward resolution, transcribed as the literal `when` clause D-7 proposes |
| 11 | `climax_phase_ends_to_afterglow` | `event: climax_ends` | `field: climax_phase, set: 餘韻` | 「高潮結束後轉為「餘韻」」(afterglow's own later decay to 未達 is change 7's `decay_tick`, not a rule here) |
| 12 | `climax_today_increment_on_climax` | `event: climax_ends` | `field: climax_today, delta: "+1"` | 「每次達到高潮時+1」(elf multi-orgasm counting clause is not race-specific in its *counting* — every climax counts, always; only the *rate* of reaching another climax is race-specific and excluded per D-7) |
| 13 | `virginity_once` | `event: first_vaginal_penetration` | `field: virgin, set: false` | 「首次…陰道插入時變更為 false」— D-7's resolved, unqualified event |
| 14 | `experience_vaginal_added` | `event: first_vaginal_penetration` | `field: experience_types, add: 陰道性交` | 「陰道性交: 首次被插入後添加（同時處女變 false）」— D-7: shares `virginity_once`'s exact event |
| 15 | `experience_masturbation_added` | `event: masturbation_climax` | `field: experience_types, add: 自慰` | 「自慰: 首次成功自慰高潮後添加」 |
| 16 | `experience_lesbian_added` | `event: penetrative_sex_with_female` | `field: experience_types, add: 女女性愛` | 「女女性愛: 與其他女性進行插入性接觸後添加」 |
| 17 | `experience_titfuck_added` | `event: breast_sex_performed` | `field: experience_types, add: 乳交` | 「乳交: 使用乳房為他人服務後添加」 |
| 18 | `experience_watched_added` | `event: watched_during_activity` | `field: experience_types, add: 被觀看` | 「被觀看: 在他人注視下進行性活動後添加」— see D-6 for event-name unification with rule 23 |
| 19 | `experience_exposure_added` | `event: public_exposure` | `field: experience_types, add: 露出` | 「露出: 在公共場所故意暴露身體後添加」 |
| 20 | `experience_interspecies_added` | `event: sexual_activity_with_nonhuman` | `field: experience_types, add: 異種性愛` | 「異種性愛: 與非人類生物進行性活動後添加」 |
| 21 | `shame_up_on_exposure_increase` | `field_changed: exposure, direction: up` | `field: shame, delta: "+1"` | 「暴露增加…時提升」— half of an OR variable_rule.md states in one bullet; see D-6 |
| 22 | `shame_up_on_public_sexual_activity` | `event: public_sexual_activity` | `field: shame, delta: "+1"` | 「…公開場合性活動時提升」— other half of the same OR bullet |
| 23 | `shame_up_on_watched` | `event: watched_during_activity` | `field: shame, delta: "+1"` | 「被注視時提升」— see D-6 for event-name unification with rule 18 |
| 24 | `exposure_up_on_clothing_damaged` | `event: clothing_damaged_in_combat` | `field: exposure, delta: "+1"` | 「戰鬥中服裝破損可能增加暴露」— see D-6 for exposure's other two bullets, excluded |

Every rule's `event` name is a vocabulary this design defines but does not wire to any player command
— change 8 (`action-resolver`) decides which command or narrated action emits which event, per this
proposal's Impact section.

### D-5. `climax_today`'s write-path gap — flagged for change 7's owner, not worked around.

Change 7's documented `SexualState` public surface gives every ordered-level field
(`arousal`/`wetness`/`shame`/`exposure`/`climax_phase`) a property returning the *live trait object*,
so a rule can legally mutate it via the object's own `.value` (D-1). `climax_today`'s property,
per change 7's design.md D-2, returns a plain `int` by value:

```python
@property
def climax_today(self) -> int: return self._traits.climax_today.value
```

There is no live handle to mutate and no setter. `virgin` has `@virgin.setter`; `experience_types`
has `add_experience_type()` as its sole mutator; `climax_today` has neither. Rule 12
(`climax_today_increment_on_climax`, transcribing `variable_rule.md`'s plain, unconditional 「每次
達到高潮時+1」) therefore has no legal write path under change 7's documented contract as given, and
this design is explicitly instructed not to reach into `SexualState._traits` from outside the class,
and not to edit change 7's artifacts.

**This is a genuine boundary gap, not an ambiguity `variable_rule.md` itself creates** — the
behavior it describes is simple and unconditional; the gap is that change 7's property surface, as
documented, does not yet expose a way to satisfy it. **Resolution, flagged for coordination with
change 7's owner rather than worked around silently**: add one small, additive method,
`SexualState.record_climax()`, incrementing `climax_today` by exactly one — mirroring
`add_experience_type()`'s "sole mutator" shape (a single, narrowly-scoped method rather than a
general setter, keeping the same "one function owns this field's one legal mutation" discipline
change 7 already established for `virgin` and `experience_types`). `_apply_then()`'s `counter`
branch calls `entity.sexual.record_climax()`, never `entity.sexual._traits.climax_today.value += 1`.
This proposal does not implement or specify that method inside change 7's own files — tasks.md's
dependency-verification section flags it as a pre-implementation coordination point, the same
discipline change 7 itself used for its own Evennia-contrib API-signature verification tasks (design
doc D-1's "flagged for implementer verification").

**Alternative considered**: reach into `entity.sexual._traits.climax_today.value` directly from
`sexual_transitions.py`, the same way change 7's own `reset_daily_counters()` does internally.
Rejected — that function is defined *inside* `sexual_state.py`, the class's own module; replicating
the identical private-attribute access from a different module is precisely the bypass change 7's
D-2 warns a future consumer might attempt, and this task's own instructions name it explicitly:
"attach to it, never reach into the private `TraitHandler`." A one-line coordination flag is more
honest than a silent violation of a boundary this design was explicitly told to respect.

### D-6. Ambiguities this document resolves that D-7 did not already cover.

D-7 (change 7's design.md) analyzed `variable_rule.md` for its self-contradiction (virginity) and two
named ambiguities (`達臨界點`, wetness's `至少`). The following four points needed their own
resolution because they fall outside what D-7 was scoped to walk line-by-line:

1. **Arousal's own "1-2級" stimulus range and its "sustained stimulus" clause are two separate,
   unremarked triggers, not one.** `variable_rule.md` states 「接受性刺激…時提升1-2級」(discrete
   stimulus → +1-2) and, in the very next bullet, 「持續刺激經過合理時長後再提升1級」(continued
   stimulus after a "reasonable" duration → +1 more) with no numeric duration given, exactly the same
   shape of ambiguity D-7 already resolved for climax_phase's `達臨界點` ("interpret duration as a
   distinct event the caller decides when to fire, not a real-time measurement this table performs").
   Applying that identical resolution here: `arousal_up_on_sustained_stimulus` fires on a distinct
   `sustained_stimulus_applied` event, left for change 8's future author to decide when to emit
   (e.g. after N consecutive stimulus actions, or after a narrated time skip) — this table performs
   no duration arithmetic itself, mirroring D-7's own reasoning rather than inventing a new kind of
   ambiguity resolution.
2. **`watched_during_activity` is used as one event for two source bullets** — 性經驗類型's 「被觀看:
   在他人注視下進行性活動後添加」and 羞恥感's 「被注視時提升」. Both describe the same real-world
   moment (being watched while doing something sexual) from two different fields' point of view;
   `variable_rule.md` gives no indication that "being watched during sexual activity" and "being
   watched" (for shame's purposes) are meant to be different occurrences within a document whose
   entire scope is a sexual-state model. Using one event keeps the vocabulary minimal instead of
   inventing an unstated second event with no distinguishing description. If a future author finds a
   scenario where these should diverge (e.g. shame rising from being watched while merely exposed,
   with no sexual activity occurring), the correct fix is a new, distinctly-named event and a new
   rule for that specific case — not a retroactive split of this one.
3. **Exposure's `更換服裝時根據遮蓋程度調整` and `可故意調整服裝改變暴露程度` are equipment-system
   writes, not rows in this table.** Unlike this table's other 23 rules, these two bullets describe
   *the clothing/equipment system computing what `exposure` level a specific garment implies* — there
   is no fixed delta or fixed target level `sexual.yaml` could declare; the value depends on
   coverage data this table has no access to and change 5 (`skills-equipment`) owns. Only the one
   bullet expressible as a fixed, condition-triggered delta — 「戰鬥中服裝破損可能增加暴露」(combat
   clothing damage → `exposure +1`) — becomes rule 24. The other two bullets, and 「服裝決定基礎值」
   (clothing sets a *baseline*, not a *transition*), are left as an explicit integration point for
   whichever future change wires clothing items to `entity.sexual.exposure` directly (most plausibly
   change 5 or change 8), the same way change 7 itself left the buff-lever seam "documented, not
   filled" rather than guessing at a shape.
4. **羞恥感's 「習慣性降低: 長期重複相同行為後增加幅度降低」(habituation — repeated identical behavior
   reduces the increase magnitude of future shame rises) has no row in this table.** Implementing it
   would require a per-behavior repetition counter nowhere in design doc §6.4's field model and not a
   `SexualState` field this or change 7 owns — the condition grammar (`event`/`field`/`field_changed`/
   `buff_active`) has no way to ask "how many times has this specific behavior already happened,"
   and inventing such a counter is exactly the kind of new field-model surface change 7's scope, not
   this table's, would need to add first. Excluded for the same reason D-7 excludes race-specific
   asides: expressible only as a future mechanism (a per-behavior counter and a rate modifier reading
   it) that no named change in the roadmap currently owns, not silently dropped.

### D-7. Test discipline: the rule-ID-to-test correspondence and `FIELD_KINDS` coverage checks,
structurally enforced.

Mirroring change 6's own D-7 exactly (`test_every_rule_id_has_a_test()` walking
`combat_modifiers.yaml`'s rule IDs against `test_rule_<id>` functions via `inspect.getmembers`):

```python
def test_every_rule_id_has_a_test():
    """Walks sexual.yaml's loaded Rule.id values; asserts a test_rule_<id> function
    exists in this test module for every one, and that no test_rule_<id> function
    exists for an id sexual.yaml does not define (catches a stale test left behind
    after a rule is renamed or removed, not just a missing one)."""

def test_field_kinds_covers_every_targetable_field():
    """Asserts FIELD_KINDS' key set equals exactly the set of `then.field` values
    appearing anywhere in sexual.yaml -- no rule targets a field FIELD_KINDS does
    not recognize (which would silently no-op or raise deep inside _apply_then),
    and no FIELD_KINDS entry sits completely untargeted by any rule."""
```

Hard requirement 4 (one-way and append-only fields tested directly) gets two additional, targeted
tests beyond the one-per-rule-ID set: `test_virginity_once_is_irreversible()` fires
`first_vaginal_penetration` via `apply_event()` twice in sequence (and, separately, attempts a direct
`entity.sexual.virgin = True` afterward) and asserts `virgin` is `False` after both attempts, not just
after the first; `test_experience_types_only_grows()` fires two distinct experience-triggering events
and re-fires one of them, asserting the resulting set strictly grows across the sequence and never
loses or duplicates an entry. Both exercise the *rule* layer end-to-end (via `apply_event()`), not
only `SexualState`'s own isolated setter/mutator, which change 7's test suite already covers at the
handler level — hard requirement 4 asks for coverage of the *transition rules* specifically.

`test_climax_phase_rules_route_through_guard()` is a source-inspection test (mirroring change 7's own
task 8.2 discipline for its own module) asserting `sexual_transitions.py` contains no reference to
`.climax_phase.value =` or `._traits.climax_phase` outside the one call site inside `_apply_then()`'s
`ordered_level_cyclic` branch that invokes `_apply_climax_phase_set()`.

## Risks / Trade-offs

- **[Risk] `climax_today`'s write-path gap (D-5) means this proposal cannot fully implement rule 12
  without a coordinated, additive change to change 7's `sexual_state.py`.** → Documented explicitly
  rather than worked around; tasks.md's dependency-verification section flags the exact one-method
  addition needed (`record_climax()`) as a pre-implementation coordination point with change 7's
  owner, the same discipline change 7 itself used for unverified Evennia-contrib signatures.
- **[Risk] Unifying `watched_during_activity` across two source bullets (D-6.2) could under-model a
  future scenario where "watched, not sexual" and "watched, sexual" need different shame/experience
  consequences.** → Accepted for this table's current 24 rules; flagged explicitly as a resolution a
  future rule addition should split out with a new event name, not retroactively guessed at now.
- **[Risk] `max_passes=50` in `apply_event()`'s fixed-point loop is a defensive ceiling this table's
  current rules never approach (every ordered-level field converges in at most 4 passes by
  construction), so it is untested against a genuine oscillation.** → Accepted; a test constructs two
  synthetic, mutually-triggering rules against a throwaway rule list (not `sexual.yaml` itself) and
  asserts the loop terminates at `max_passes` rather than hanging, proving the ceiling fires without
  requiring `sexual.yaml` to contain a rule pair that oscillates.
- **[Risk] Exposure's clothing-driven bullets (D-6.3) are left as an unowned integration point** —
  no roadmap item currently claims "wire clothing items to `entity.sexual.exposure`." → Accepted and
  named explicitly, the same "documented, not silently dropped" treatment change 7's own Open
  Questions section gives its own unowned bestiary-override question.
- **[Risk] Habituation (D-6.4) has no row and no owner** — implementing it needs a field-model
  addition (a per-behavior repetition counter) neither change 7 nor this change is scoped to add. →
  Accepted and named explicitly for the same reason race-specific behaviors are (D-7): a future
  mechanism, not a silently dropped requirement.

## Migration Plan

Not applicable in the backward-compatibility sense — unreleased project, zero users,
`world/rules/rulebook/sexual.yaml` and `world/rules/sexual_transitions.py` do not exist yet. Sequencing
concerns only:

- Must land after change 7 (needs `SexualState`'s public surface and `_apply_climax_phase_set()`
  importable) and change 6 (needs `schema.py`'s `Rule`/`load_rules()`/`evaluate_condition()`
  importable).
- D-5's `record_climax()` coordination should ideally land as part of change 7 if change 7 has not
  yet been implemented when this change starts; if change 7 is already implemented without it, the
  minimal additive patch is this change's own first task, scoped to exactly one method, not a
  broader edit to change 7's file.
- Change 8 (`action-resolver`) is expected to call `apply_event()` from its effect-resolution step
  and to decide which command emits which event name; no such wiring exists yet.

## Open Questions

- **Should `masturbation_climax`, `penetrative_sex_with_female`, `breast_sex_performed`,
  `sexual_activity_with_nonhuman`, and `public_sexual_activity` be raised alongside a generic
  `climax_ends`/event for the same real-world moment, or should the resolver collapse them into one
  richer event payload (e.g. `climax_ends(cause="masturbation")`)?** Left to change 8's author —
  this table only defines the event *names* rules react to; it does not decide whether a single
  in-game action produces one `apply_event()` call or several. Both are expressible against this
  design without any change to `sexual.yaml`.
- **Exposure's clothing-driven baseline and mid-scene adjustment (D-6.3)** — left unowned, as stated,
  pending a future change (most plausibly change 5 or change 8) deciding how a worn item's coverage
  maps to an `exposure` level.
- **Habituation (D-6.4)** — left unowned pending a future field-model addition (a per-behavior
  repetition counter) that neither change 7 nor this change is scoped to add.
