# Proposal: Sexual Intercourse Acts (交合 / 深度交合) with the D-12 Conditional Branch

## Why

`sexual-catalog-partner` deferred 交合 and 深度交合 (partner design.md D-2) because
`SexualActDef.sexual_events` is a fixed tuple with no mechanism to select an event from runtime
participant state. That deferral left the system's flagship D-12 mechanic unwired: the three
penetration events (`first_vaginal_penetration`, `penetrative_sex_with_female`,
`penetrative_sex_with_male`) have **no production emitter**, so `virginity_once` can never fire,
`virgin` can never break through play, and the `sex` field shipped by S1 has zero consumers. The
same review found that acts' events fire on targets only — never on the acting participant — so a
two-party act's experience credits (乳交, 異種交合) land on the partner alone (partner design.md
D-3's documented asymmetry). This change closes both loops.

## What Changes

- **BREAKING (engine semantics)**: an act's `sexual_event:<name>` entries now fire on **every
  participant** (actor plus targets), mirroring the pleasure and counter handlers. Events in a new,
  dedicated `_LEGACY_TARGET_SCOPED_EVENTS` set — the legacy `divine_sexual_arts` skill's
  `stimulus_applied` — stay target-scoped so the divine-arts exemption from self-pleasure (D-9) is
  preserved.
- **New conditional-event mechanism**: `SexualActDef.pair_events` — a validated tuple of
  `((sex, sex), event_name)` entries selected at cast time from the participants' `sex` fields
  (opposite → `first_vaginal_penetration`, both female → `penetrative_sex_with_female`, both male →
  `penetrative_sex_with_male`, either `other`/unknown → no event). Acts declaring `pair_events`
  SHALL be `TargetSpec.SINGLE`, enforced structurally.
- **New effect prefix** `act_pair_event:<act_key>` with a dedicated handler in
  `world/rules/action.py` that resolves the selected event and applies it to every participant —
  the D-12 table says an opposite-sex 交合 breaks `virgin` for **both parties at once**.
- **Catalog**: two Tier-3 關係線 acts — 交合 (`partner_vaginal_sex`) and 深度交合
  (`partner_deep_vaginal_sex`), both `{duo_act_count: 30, climax_count: 10}`, part 私處,
  `resistible=True`, crediting `duo_act_count` on both participants. The `sex` field finally gets
  its first consumer.
- No `sexual.yaml` rule changes: `virginity_once`, `experience_vaginal_added`,
  `experience_lesbian_added`, `experience_gay_added` and the `penetrative_sex_with_male` row (B3)
  all already exist and simply gain their first real emitters.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `sexual-act-registry`: `SexualActDef` gains the `pair_events` metadata field with load-time
  validation; `_act_family()` gains the `act_pair_event:<key>` effect entry for acts declaring it.
- `sexual-act-effects`: the `sexual_event:<name>` handler applies to every participant (with the
  forbidden-event legacy exception); a new `act_pair_event:<key>` handler resolves the
  sex-conditional event through a pure selector.
- `sexual-catalog-partner`: the partner catalog grows from fourteen to sixteen acts; 交合/深度交合
  implement the D-12 branch (sex-dependent event, symmetric `virgin` break, `other`/unknown and
  monster targets never break `virgin`).
- `sexual-catalog-shame`: the AREA-act `self_exposure` recipient scenario is amended to the
  participant-scoped semantics — the performing actor of a public act is publicly exposed too.

## Impact

- `world/skills/sexual_acts/_builder.py` — `SexualActDef.pair_events`, validation, effect emission.
- `world/skills/sexual_acts/partner.py` — two new act rows.
- `world/skills/effects.py` — `act_pair_event` typed effect parse.
- `world/rules/sexual_act_effects.py` — pure pair-event selector reading `SEX_VALUES`.
- `world/rules/action.py` — `_handle_sexual_event` participant semantics; new
  `_handle_act_pair_event` handler + registration.
- Tests: registry structural checks, effects unit tests, catalog tests, and a full D-12 branch
  acceptance test (opposite/same-sex/other pairings).
- Spec deltas: `sexual-act-registry`, `sexual-act-effects`, `sexual-catalog-partner`,
  `sexual-catalog-shame` (the AREA-act recipient amendment).
