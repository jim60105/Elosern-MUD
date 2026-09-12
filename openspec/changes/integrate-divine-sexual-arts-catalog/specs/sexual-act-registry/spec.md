## RENAMED Requirements

- FROM: `### Requirement: SEXUAL_ACT_REGISTRY's keys and SKILL_REGISTRY's SEXUAL_ACT-categorised keys agree exactly, modulo the three named mastery/mystery exclusions`
- TO: `### Requirement: SEXUAL_ACT_REGISTRY's keys and SKILL_REGISTRY's SEXUAL_ACT-categorised keys agree exactly, modulo the two named mastery exclusions`

## MODIFIED Requirements

### Requirement: SEXUAL_ACT_REGISTRY's keys and SKILL_REGISTRY's SEXUAL_ACT-categorised keys agree exactly, modulo the two named mastery exclusions
A structural test SHALL assert that `set(SEXUAL_ACT_REGISTRY)` equals the set of `SKILL_REGISTRY`
keys whose `category` is `SkillCategory.SEXUAL_ACT`, with `{"divine_sexual_mastery",
"reincarnation_boon_yuna"}` excluded from that comparison on both sides. `divine_sexual_arts` SHALL
NOT be a member of the exclusion set: it is registered as a catalogue row (see the added
requirement) and participates in the agreement comparison on both sides. The shipped structural
constant `_STRUCTURAL_EXCLUSIONS` is therefore exactly that two-key set once the integration lands.

#### Scenario: The two registries agree after the catalogue lands
- **WHEN** the structural test runs against the assembled registries after every catalog proposal and
  the `divine_sexual_arts` integration have landed
- **THEN** it passes, because every `SEXUAL_ACT`-categorised `SKILL_REGISTRY` key except the two
  remaining named exclusions has a paired `SEXUAL_ACT_REGISTRY` row, `divine_sexual_arts` included

#### Scenario: A SkillDef categorised SEXUAL_ACT with no paired SexualActDef fails the structural test
- **WHEN** a hypothetical skill is added to `SKILL_REGISTRY` directly (not through the catalogue)
  with `category=SkillCategory.SEXUAL_ACT` and a key not in `SEXUAL_ACT_REGISTRY` and not one of the
  named exclusions
- **THEN** the structural test fails, naming the unmatched key

#### Scenario: divine_sexual_arts no longer needs an exclusion
- **WHEN** a hypothetical half-migrated registry omits `divine_sexual_arts` from
  `SEXUAL_ACT_REGISTRY` while `SKILL_REGISTRY` still categorises it `SEXUAL_ACT`
- **THEN** the comparison fails naming `divine_sexual_arts`, proving the exclusion set no longer
  hides it

### Requirement: SexualActDef carries exactly the metadata a sex act needs beyond SkillDef
`world/skills/sexual_acts/_builder.py` SHALL define `SexualActDef` as a frozen dataclass with exactly
these fields: `key`, `unlock` (a mapping of `SexualState` counter attribute names to integer
thresholds, all of which SHALL be met for the act to unlock), `base_pleasure` (a positive integer),
`actor_part` and `target_part` (each `None` or a member of `world.lore.sexual_vocab.BODY_PARTS`),
`actor_pleasure_ratio` (a float), `actor_counters` and `participant_counters` (each a tuple of
`SexualState` counter attribute names), `sexual_events` (a tuple of event-name strings in emission
order), `resistible` (a bool), `pair_events` (a tuple of `(sex_pair, event_name)` entries, empty for
acts without a sex-conditional event; see the pair-events requirement), and `ownership_gated` (a
bool, default `False`) — when `True` the row is never unlocked through the counter-derivation branch
of `unlocked_act_keys_for` regardless of its `unlock` mapping, and is usable only by entities that
actually own the paired `SkillDef` key; the derivation-side exclusion itself is pinned by the
`sexual-state-handler` capability. `SexualActDef` SHALL declare no `line` field; an act's line is
read from the paired `SkillDef.group`. `_act_family()` SHALL NOT expose an `ownership_gated` row
knob (catalogue rows are never ownership-gated; only hand-built rows may set it).

#### Scenario: A seed act declares an empty unlock mapping
- **WHEN** a `SexualActDef` is constructed with `unlock={}` and the default `ownership_gated=False`
- **THEN** construction succeeds and the act is always available regardless of any counter's value

#### Scenario: An ownership-gated row is constructible and registers like any other
- **WHEN** a `SexualActDef` is constructed with `unlock={}` and `ownership_gated=True`
- **THEN** construction succeeds and the field reads back `True`

#### Scenario: SexualActDef declares no line field
- **WHEN** `SexualActDef`'s field set is inspected
- **THEN** it contains no field named `line`, and an act's line is obtained by reading
  `SKILL_REGISTRY[act.key].group` instead

#### Scenario: An act without a sex-conditional event declares an empty pair_events tuple
- **WHEN** a `SexualActDef` is constructed for an ordinary act that does not name `pair_events`
- **THEN** the constructed value's `pair_events` equals `()`

#### Scenario: An act's unlock mapping is exposed as a read-only proxy
- **WHEN** a `SexualActDef` is constructed with a mutable `dict` as its `unlock` mapping
- **THEN** `act.unlock` is a read-only `MappingProxyType` view, `dict(act.unlock) == unlock` still
  holds, and mutating the caller's original dict after construction does not change `act.unlock`

## ADDED Requirements

### Requirement: divine_sexual_arts is the eighth hand-built 神之秘法 row
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL contain a hand-built
`(SkillDef, SexualActDef)` pair with key `divine_sexual_arts` declaring `requires_divine_arts=True`,
`unlock={}`, `ownership_gated=True`, `target_part=None`, `resistible=True`, `actor_counters=()`,
`participant_counters=()`, and `effects=["sexual_event_target:stimulus_applied"]`; it SHALL NOT be
constructed via `_act_family()`, and `world/skills/registry.py` SHALL NOT define this key inline.
Because it is a catalogue row with `resistible=True`, the shipped `_step4b_sexual_resist_gate`
applies to it exactly as it applies to the seven existing divine acts.

#### Scenario: The divine line carries the eighth pair
- **WHEN** `world.skills.sexual_acts.divine.DIVINE_ACTS` is inspected after this change
- **THEN** a pair with key `divine_sexual_arts` is present in the tuple with the fields above, and
  `SKILL_REGISTRY["divine_sexual_arts"]` is the same `SkillDef` object surfaced by the catalogue
  import rather than a main-registry definition

#### Scenario: The shipped row's parsed effect is the target-scoped event effect
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"].parsed_effects` is inspected
- **THEN** it equals one `TargetSexualEventEffect(event_name="stimulus_applied")` — the prefix's
  parse contract is owned by the `sexual-act-effects` capability's parser requirement, not this one

#### Scenario: The eighth act is subject to the resist gate
- **WHEN** `divine_sexual_arts` is cast by its sole owner at a target whose resist contest resolves
  `resisted=True`
- **THEN** the cast succeeds with the resist verdict logged, the resisted target receives no
  `stimulus_applied` event, and no `RejectedAction` is raised

#### Scenario: The mastery blanket still does not reach the eighth act
- **WHEN** an entity directly owns a skill carrying `SexualMasteryEffect` but has no divine-capable
  race and does not own `divine_sexual_arts`
- **THEN** `owned_keys()` includes the full counter-gated catalogue but not `divine_sexual_arts`,
  because the mastery branch excludes `requires_divine_arts=True` acts and the counter branch
  excludes `ownership_gated` rows

### Requirement: Only actual ownership grants divine_sexual_arts to a divine-capable entity
A structural-plus-behavior pair SHALL pin that an entity whose `base_owned_keys()` excludes
`divine_sexual_arts` — a fresh non-Yuna elf included — neither derives the key through
`unlocked_act_keys()`/`owned_keys()` nor casts it (the `_step1_ownership` step rejects), while the
`yuna_darknight` preset's actual ownership grants the cast. The seven shipped divine acts'
counter-derivation behavior SHALL NOT change: only `ownership_gated=True` rows are excluded from the
counter branch. The confer/grant surface (`conferred_grants()`) SHALL NOT become an acquisition path
for this row: `SkillHandler.owned_keys()` is base keys plus derived act keys and `_step1_ownership`
consults it alone — the shipped ownership-only contract, restated here because the row's entire
exclusivity rests on it.

#### Scenario: A fresh elf does not derive or cast the signature act
- **WHEN** `owned_keys()` is read for a fresh elf entity that owns no skill kits beyond innates, and
  that entity then casts `divine_sexual_arts`
- **THEN** the key is absent from `owned_keys()` and the cast is rejected at `_step1_ownership`

#### Scenario: Yuna's kit grants the cast
- **WHEN** an entity built from the `yuna_darknight` preset casts `divine_sexual_arts`
- **THEN** ownership and the divine-arts race gate both pass, and the cast resolves against the
  target

#### Scenario: A conferred grant alone does not reach the act
- **WHEN** a divine-capable entity carries `divine_sexual_arts` only in `conferred_grants()` and not
  in its base keys
- **THEN** the key is absent from `owned_keys()` and a cast is rejected at `_step1_ownership` —
  conferral is not an ownership path for any skill, ownership-gated or not

#### Scenario: The seven shipped divine acts keep deriving through counters
- **WHEN** `unlocked_act_keys()` is read on a fresh entity of any race
- **THEN** all seven `divine.py` acts are present, unchanged from the shipped empty-unlock semantics

### Requirement: The only claim of divine_sexual_arts in shipped data is Yuna's preset
A structural test SHALL flatten the `active_skills` plus `passive_skills` lists of every
`PLAYER_PRESET_REGISTRY` entry — the sole shipped **authored** skill-kit surface today, since shipped
NPC companions are built from preset cards (the claim covers authored content, not arbitrary
runtime `db.skills` writes, for which no shipped catalog scan exists) — and assert that exactly one
claimant, the `yuna_darknight` preset, declares the key `divine_sexual_arts`. The scan SHALL read
the live registry
rather than a hardcoded preset list, so any new preset is covered automatically.

#### Scenario: Yuna is the sole claimant
- **WHEN** the structural test flattens every shipped claiming surface
- **THEN** `divine_sexual_arts` appears in exactly one claimant's skill lists, keyed `yuna_darknight`

#### Scenario: A second hypothetical claimant fails the structural test
- **WHEN** a hypothetical preset (injected into the live `PLAYER_PRESET_REGISTRY` inside the test)
  also declares `divine_sexual_arts`
- **THEN** the uniqueness assertion fails, naming both claimants

#### Scenario: The scan covers every preset's complete kit
- **WHEN** the structural test flattens the scan input
- **THEN** every `PLAYER_PRESET_REGISTRY` key contributes both its `active_skills` and its
  `passive_skills` (count-checked against the live registry), so no kit escapes the uniqueness
  assertion

