# Sexual Act System — Overview & Implementation Map

**Date:** 2026-08-15
**Status:** Approved (pending final user review of this document set)
**Scope:** `world/lore/sexual_vocab.py`, `world/rules/sexual_state.py`, `world/rules/sexual_transitions.py`,
`world/rules/rulebook/sexual.yaml`, `world/skills/` (registry, effects, new act catalog package),
`world/rules/action.py` effect handlers, `world/rules/combat.py`, `world/rules/clock.py`,
`world/rules/combat_session.py`, `world/rules/combat_view.py`, `world/rules/status_query.py`.

This is the hub document for a six-document set. It states the problem, the cross-cutting
architectural decisions, and the implementation sequence. The detailed designs live in:

| Document | Covers |
|---|---|
| [Skill Category System](2026-08-15-skill-category-system-design.md) | Presentation taxonomy for all 117 registry skills; prerequisite for everything else |
| [Sexual Pleasure Model](2026-08-15-sexual-pleasure-model-design.md) | The `pleasure` gauge, the eleven counters, climax settlement and extension |
| [Act Resolution](2026-08-15-sexual-act-resolution-design.md) | Act registry, unlock query, effect handlers, part resolution, the resist contest |
| [Act Catalog](2026-08-15-sexual-act-catalog-design.md) | The 62 counter-gated acts across five lines and their unlock ladder |
| [Divine Sexual Arts](2026-08-15-divine-sexual-arts-design.md) | The seven 神之秘法 acts that deliberately break the balance the other five lines rely on |

This document set is subordinate to `2026-07-29-ai-mud-engine-design.md`, the architectural source
of truth. Where it amends that document, the amendment is stated explicitly (see D-10).

---

## 1. Problem Statement

The engine already contains a substantially complete sexual state machine that **nothing drives**.

`world/rules/sexual_state.py` mounts `SexualState` on every `LivingEntity` as `entity.sexual`, with
five `OrderedLevelTrait` fields (`arousal`, `wetness`, `shame`, `exposure`, `climax_phase`), a
lazily-populated per-body-part `sensitivity` mapping, a daily `climax_today` counter, a one-way
`virgin` flag, and an append-only `experience_types` set. `world/rules/rulebook/sexual.yaml` declares
25 transition rules over that state, driven by `apply_event()` in `sexual_transitions.py`, including
the stamina cost of climax (`sp_cost_on_climax`, `-30..-20`). `world/rules/rulebook/combat_modifiers.yaml`
already couples that state to combat: `high_arousal_agility_accuracy_penalty` (`agility: -20%`,
`accuracy: -15`) and `climax_in_progress_locks_actions` (`actions_per_turn: 0`).
`world/rules/action.py` registers a `sexual_event:` effect prefix that routes a cast straight into
`apply_event()` through the ordinary `ActionResolver` pipeline.

Every piece of that works. What is missing is the actor-facing surface:

1. **Exactly one skill emits a sexual event.** `divine_sexual_arts` (神之秘法：性愛系統) carries
   `sexual_event:stimulus_applied` and is gated behind `requires_divine_arts`. Roughly twenty of the
   25 rules in `sexual.yaml` are conditioned on events that **no production code path ever emits** —
   `masturbation_climax`, `public_exposure`, `watched_during_activity`, `breast_sex_performed`,
   `sexual_activity_with_nonhuman`, `first_vaginal_penetration`, `climax_ends`, and others.
2. **There are no cumulative counters.** `climax_today` resets daily and is the only tally that
   exists. Nothing records lifetime behaviour, so nothing can gate on it.
3. **There is no unlock concept.** `SkillDef` has no notion of a requirement that is met by play.
4. **There is no multi-participant model.** `TargetSpec` is `NONE`/`SELF`/`SINGLE`/`AREA`, and every
   effect handler applies its effect to the resolved targets only — never to the actor as a
   co-participant.
5. **`climax_phase` `進行中` is a dead end, and it is a latent action-lock bug.** The only rule that
   leaves `進行中` is `climax_phase_ends_to_afterglow`, conditioned on the `climax_ends` event, which
   nothing emits. `DECAY_CONFIG["climax_phase"]` declares `only_from: 餘韻`, so decay cannot rescue
   it either, and `_VALID_CLIMAX_TRANSITIONS` permits only `進行中 → 餘韻`. Combined with
   `climax_in_progress_locks_actions`, **any entity that reaches `進行中` loses its actions
   permanently.** The bug is currently unreachable because nothing raises `arousal` to `極限`;
   introducing acts makes it immediately reachable, so climax settlement is not optional scope.
6. **`SexualMasteryEffect` has no consumer.** The typed effect exists in `world/skills/effects.py`,
   its docstring states it should "unlock casting of the sex-magic skill family", and the
   skill-system redesign design doc lists it as the non-elemental sibling of `ElementMasteryEffect`'s
   cast-gate override — but no code reads it.

Separately, and independently of the above, `SKILL_REGISTRY` holds **117 skills** in one flat list
(80 elemental spells, 8 element masteries, and 29 others). The combat panel renders owned skills as
one unsorted array. This is already marginal; adding 69 acts makes it unusable.

---

## 2. Cross-cutting Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| D-1 | **Sex acts are ordinary `SkillDef` entries in `SKILL_REGISTRY`, not a parallel action subsystem.** Act-specific metadata (unlock requirements, participant roles, body parts, base pleasure) lives in a parallel frozen `SEXUAL_ACT_REGISTRY` keyed by the same key. | Reuses `ActionResolver` wholesale: targeting validation, the atomic all-or-nothing commit, rollback surfaces, EventLog, and practice-XP grants. This project's specs repeatedly forbid a second parser or a second resolution pipeline (`sexual-transition-rulebook`: "no rule-loading or condition-matching logic duplicated"), and a bespoke act resolver would be exactly that. Keeping the extra metadata in a side registry avoids bloating `SkillDef` with fields that 117 existing skills will never set. |
| D-2 | **Unlocked acts enter `SkillHandler.owned_keys()`; locked acts are absent from it.** | Makes "hide, do not disable" free. `owned_keys()` already feeds both `_step1_ownership` in `action.py` and the combat panel in `combat_view.py`, so a locked act is simultaneously un-castable and unrenderable, with no presenter changes and no possibility of the two disagreeing. Mirrors the existing `INNATE_SKILL_KEYS` precedent, which grants `flee`/`basic_attack` through the same list. |
| D-3 | **`pleasure` (0–100 integer) becomes the authoritative arousal quantity; `arousal` becomes a derived, still-comparable ordered-level view over it.** | Five discrete levels with `+1..+2` deltas means three actions reach `極限`, which cannot express 69 acts of differing magnitude, nor sensitivity/shame multipliers. Keeping `arousal` readable and comparable against its vocabulary means `combat_modifiers.yaml`, `overwhelm.py`, and `status_display.yaml` need no changes at all, which removes three files from the dependency chain (see §4). |
| D-4 | **Every act applies pleasure to the actor as well as to its targets.** Enforced as a structural, registry-load-time invariant, not a convention. | This is the system's only self-limiting mechanism. Because the actor's own gauge rises, sustained offensive use degrades the actor through the *already existing* `high_arousal_agility_accuracy_penalty` and eventually locks their own actions via `climax_in_progress_locks_actions`. Without it, sex acts are a free action-denial engine. Divine arts are the declared exception (D-9). |
| D-5 | **A target may resist, resolved by one d100 contest in the shape `disengage.py` already uses.** Success wastes the actor's turn and the target proceeds normally; failure executes the act and consumes both parties' turns. | Reuses `_attempt_flee`'s exact formula shape (`roll_d100() + actor_value >= defender_constant + defender_value`, `defender_constant: 51`) rather than inventing a second contest idiom. Because the resist value is read through `evaluate_combat_modifiers()`, a target at maximum pleasure automatically resists worse via the existing `-20%` agility row — "someone mid-climax struggles to break free" needs no new rule. |
| D-6 | **Affinity modifies the resist contest, and the two stages above the natural cap short-circuit it entirely.** `至愛` (floor 90) and `絕對羈絆` (floor 100) carry an `auto_comply` flag rather than a numeric bonus. | The user's requirement is a fixed bonus reaching guaranteed compliance. A numeric bonus cannot guarantee anything in this engine: `body_enhancement_extreme` multiplies stats by 1000, so any fixed constant is defeatable. An explicit flag delivers the intended behaviour and cannot be out-scaled. `至愛` is the highest stage reachable without a `cap_breaks` milestone (natural cap is 99, `絕對羈絆`'s floor is 100). |
| D-7 | **Only a failed resist (a forced act) costs affinity. An attempt that is successfully refused costs nothing beyond the wasted turn.** | Forcing a companion should be able to drive affinity below `invite_threshold` (70) and trigger the existing party auto-leave, which gives the mechanic real weight. Charging for the attempt would make the low-affinity path so punitive that no player would explore it, killing the content. Because `至愛`+ short-circuits to compliance, a well-loved companion can never take this penalty. |
| D-8 | **Monsters have no body parts.** `resolve_part(entity, declared)` returns the single constant `GENERIC_BODY_PART` (`軀體`) for any `Monster` and the declared part otherwise. | Monsters are arbitrarily shaped; a per-archetype part table is exactly the maintenance burden the `sexual-state-handler` spec's 2026-08-09 amendment already refused for monster baselines. The predicate is `isinstance(entity, Monster)` — the same one `SexualState.__init__` uses to clamp monster `shame` — so no new taxonomy is introduced. Sensitivity training still works on monsters; they simply have one channel where a humanoid has ten. |
| D-9 | **神之秘法 acts are exempt from D-4 and from every counter gate.** The exemption is keyed on the existing data field `requires_divine_arts`, never on a hardcoded key list. | 神之秘法 is defined in world lore as the highest technique for altering the world through divinity, and is deliberately positioned to break game balance. The exemption from self-inflicted pleasure is precisely what makes it break: every other act punishes overuse, these do not. Containment is the pre-existing, very narrow `RaceProfile.can_use_divine_arts` gate enforced by `_step1_divine_arts_gate`, not a resource cost — consistent with the skill-system redesign's D7, which shipped divine mysteries as free-cost and race-gated. |
| D-10 | **`無垢回歸` restores `virgin` through a separately named mutator, `SexualState.restore_purity()`; `experience_types` is never cleared.** This is an explicit amendment to `2026-07-29-ai-mud-engine-design.md` §6.4's "one-way, irreversible" description. | The shipped `sexual-state-handler` requirement constrains *the public setter* ("no later mutation **through that public setter**"), so a separately named mutator does not weaken it — every ordinary rule path stays one-way. The same requirement's `experience_types` clause is absolute ("SHALL expose no replacement or removal method"), so clearing it would require rewriting a live requirement; leaving experience intact avoids that and reads better besides (the body is restored, the memory is not). |
| D-11 | **The act catalog is a package with one module per line, and the empty line modules plus their `__init__.py` imports ship in the registry proposal before any catalog content.** | Six catalog proposals can then be implemented fully in parallel, each owning exactly one file. If the catalog were one module, or if `__init__.py` grew an import per line, every catalog proposal would conflict with every other. See §4. |
| D-12 | **`virgin` breaks only on vaginal intercourse with an opposite-sex partner.** A same-sex act, an anal act, and any act against a `Monster` never break it. This requires a new `sex` field on entities, which does not exist anywhere in the codebase today. | The rulebook already draws this distinction and has since it shipped: `virginity_once` is conditioned on `first_vaginal_penetration`, while the same-sex path `penetrative_sex_with_female` adds the `女女性愛` experience type and deliberately never touches `virgin`. The branch therefore belongs in the act catalog, not in the rules — but nothing can currently *evaluate* it, because `CHARACTER_SCHEMA_V1` declares `age`, `apparent_age`, `race`, and `subrace` and no notion of sex. An entity whose sex is unknown or `other` never breaks virginity, which makes the monster case fall out for free instead of needing a special case. **The branch itself ships in the follow-up `sexual-intercourse-acts` (§4.2), which supplies the sex-conditional event mechanism C4 could not build.** |

---

## 3. System Shape

```
world/lore/sexual_vocab.py          AROUSAL_LEVELS … SENSITIVITY_LEVELS   (existing)
                                    BODY_PARTS, GENERIC_BODY_PART         (new)
                                    ↓
world/rules/sexual_state.py         SexualState                           (extended)
                                      pleasure  0–100  authoritative      (new)
                                      arousal   derived ordered view      (changed)
                                      11 counters + sole mutators         (new)
                                    ↓
world/rules/rulebook/sexual.yaml    transition rules                      (extended)
world/rules/sexual_transitions.py   apply_event()                         (unchanged engine)
                                    ↓
world/skills/sexual_acts/           SEXUAL_ACT_REGISTRY + SkillDef rows    (new package)
  solo · shame · partner · combat · interspecies · divine
                                    ↓
world/rules/sexual_unlock.py        unlocked_act_keys()                   (new)
world/skills/handler.py             owned_keys() includes unlocked acts   (extended)
                                    ↓
world/rules/action.py               pleasure: / sexual_counter: handlers  (new prefixes)
world/rules/sexual_resist.py        resist contest                        (new)
                                    ↓
world/rules/combat.py · clock.py    climax settlement + extension         (extended)
world/rules/combat_view.py          grouped skill panel                   (extended)
```

Nothing in this diagram introduces a new resolution path. Every arrow crossing into game state
passes through `ActionResolver` or through `apply_event()`, both of which already exist and are
already atomic.

---

## 4. Implementation Sequence

Twenty-two proposals, plus five follow-ups — `sexual-resist-out-of-combat` (discovered and deferred
during `B6b`'s own design), `sexual-resist-cast-wiring` (discovered post-implementation, when `B5`'s
own row's stated obligation below turned out not to have been fulfilled — see the note under §4.2's
table), and the three post-implementation review proposals `sexual-intercourse-acts`,
`sexual-public-act-events`, and `combat-panel-skill-capacity` (discovered when the shipped system was
reviewed for wiring gaps — see the second note under §4.2's table) — each sized for one working day.
The organising principle is **disjoint file
ownership**: no two proposals in the same batch touch the same file. That is the only real lever on
rebase cost.

### 4.1 Dependency graph

```
S1 ──────────────────────────────────────────────────────── C4
C1 ─────────────────────────────┐
A1 ──┬── A2                     │
     ├── A3                     │
     └───────────┐              │
B1 ──┬── B2 ──┬──┴── B4 ──┬── B5 ┴── B8 ── C2/C3/C4/C5/C6/C7a
     │        └── B3 ─────┘     │
     │                          └── B6a ── B6b
B7 ──┘ (independent)                                 C7b ── (last)
```

### 4.2 Proposals

| # | Key | Content | Depends on | Files owned exclusively |
|---|---|---|---|---|
| S1 | `entity-sex-field` | `sex` (`female` / `male` / `other`) on the character schema and on `LivingEntity`; import validation; example record update. Required for characters, defaulting to `other` for entities with no record. **Prerequisite for D-12; no such field exists today.** | — | `world/imports/schema.py`, `world/imports/examples/`, `typeclasses/` |
| C1 | `sexual-body-parts` | `BODY_PARTS` (10) and `GENERIC_BODY_PART` as pure vocabulary constants. `resolve_part()` itself lives in `B5`, because this module's spec forbids it from containing behaviour. | — | `world/lore/sexual_vocab.py` |
| A1 | `skill-category-registry` | `SkillCategory`, `category`/`group` fields, all 117 assignments, structural tests | — | `world/skills/registry.py` |
| B1 | `pleasure-gauge` | `pleasure` authoritative, `arousal` derived, band table, rewrite the four arousal-writing rules | — | `sexual_state.py`, `sexual.yaml`, `sexual_transitions.py` |
| B7 | `exposure-combat-modifier` | New `combat_modifiers.yaml` rows keyed on `exposure` | — | `combat_modifiers.yaml` |
| A2 | `skill-category-combat-panel` | `context_actions` v2→v3 grouped payload, telnet parity, Node/browser tests, spec delta | A1 | `combat_view.py`, `web/` |
| A3 | `skill-category-status-listing` | Out-of-combat listing reads `owned_keys()` and groups; fixes innate skills being invisible | A1 | `status_query.py` |
| B2 | `sexual-counters` | Eleven counter traits plus one sole mutator each | B1 | `sexual_state.py` |
| B3 | `climax-settlement` | Emit `climax_ends` from both existing decay call sites, `climax_extended`, extension threshold, the `penetrative_sex_with_male` rule row (D-12 symmetry), **fixes the `進行中` dead end** | B1, B2 | `sexual_state.py`, `sexual.yaml`, `combat.py`, `clock.py` |
| B4 | `sexual-act-registry` | `SexualActDef`, `_act_family()`, `unlocked_act_keys()` incl. mastery blanket unlock, `owned_keys()` integration, **six empty line-module stubs** | A1, B2 | `world/skills/sexual_acts/`, `handler.py` |
| B5 | `sexual-act-effects` | `pleasure:` / `sexual_counter:` prefixes and handlers, bidirectional participant application, part resolution; **emits the `EventEntry(kind="sexual_resist", ...)` contract `B6b`'s scan consumes, per source design §3.4 — fixed in the shared source design so this obligation applies regardless of `B5`/`B6b` batch order** | C1, B1, B4 | `effects.py`, `action.py`, `world/rules/sexual_acts.py` |
| B6a | `sexual-resist-contest` | Contest as a pure function, affinity modifier table, `auto_comply`, the first-five-climax-turns short circuit | B3, B4 | `world/rules/sexual_resist.py`, `sexual_resist.yaml` |
| B6b | `sexual-resist-turn-cost` | The in-combat affinity consequence of a resisted or forced act: a new `AffinitySource`, a `_scan_sexual_coercion` post-round scan mirroring `_scan_friendly_fire`, and the documented `EventEntry` contract `sexual-act-effects` must emit for it to react to. **File ownership widened during `B6b`'s own design** (see that proposal's design.md Decision 4) to include the penalty's rulebook field | B5, B6a | `combat_session.py`, `affinity.py`, `affinity_config.py`, `rulebook/affinity.yaml` |
| — | `sexual-resist-out-of-combat` | The symmetric affinity consequence at the out-of-combat cast path, deferred out of `B6b`'s scope (see that proposal's design.md Decision 5) because neither `cast_settlement.py` nor `commands/action.py` was in any proposal's ownership and auditing them was not achievable within `B6b`'s one-day sizing | B6b | `cast_settlement.py` or `commands/action.py` (exact call site TBD by that proposal) |
| — | `sexual-resist-cast-wiring` | **`B5`'s row above states it emits the `sexual_resist` `EventEntry` contract; it did not (see the note below the table).** This follow-up actually wires `resist_verdict()` into `ActionResolver.resolve()`: one new pre-effect-resolution step excludes a successfully-resisting target from a `resistible=True` act's pleasure/counter/event effects and emits the `EventEntry(kind="sexual_resist", ...)` `B6b`'s `_scan_sexual_coercion` already consumes. Actor-side effects, resource cost, time cost, and practice XP stay unconditional on resist outcome. | B5, B6a, B6b | `world/rules/action.py` |
| B8 | `sexual-act-seeds` | Seven seeds plus one representative upper-tier act per line (~14) | B5, B6b | the six line modules |
| C2 | `sexual-catalog-solo` | 獨處線, 17 acts | B8 | `sexual_acts/solo.py` |
| C3 | `sexual-catalog-shame` | 羞恥線, 10 acts | B8 | `sexual_acts/shame.py` |
| C4 | `sexual-catalog-partner` | 關係線, 18 acts; the D-12 opposite-sex branch on 交合 / 深度交合. **交合 / 深度交合 were deferred out of C4 (its design D-2) and ship in the follow-up `sexual-intercourse-acts` below.** | B8, **S1** | `sexual_acts/partner.py` |
| C5 | `sexual-catalog-combat` | 戰鬥線, 10 acts | B8 | `sexual_acts/combat.py` |
| C6 | `sexual-catalog-interspecies` | 異種線, 7 acts, `異種次數` wiring | B8 | `sexual_acts/interspecies.py` |
| C7a | `divine-sexual-arts-reuse` | 絕頂律令 / 時姦 / 神域搾取 — the three 神之秘法 needing no new `SexualState` surface | B8 | `sexual_acts/divine.py` |
| C7b | `divine-sexual-arts-mutators` | 感度創世 / 恥辱剝奪 / 絕對從屬 / 無垢回歸 — needs `saturate_sensitivity()`, `clamp_shame_to()`, `mark_submission()`, `restore_purity()` | C7a | `sexual_state.py`, `sexual.yaml` |
| — | `sexual-act-docs` | `docs/game/commands.md`, `docs/game/command-reference.md` | B8 | `docs/game/` |
| — | `sexual-intercourse-acts` | 交合 / 深度交合 — the D-12 branch C4 deferred. Adds `SexualActDef.pair_events` (sorted two-sex pairs → event, validated in `_act_family()`), the `act_pair_event:<key>` effect prefix, and makes acts' `sexual_event:` entries fire on **every participant** — with a dedicated `_LEGACY_TARGET_SCOPED_EVENTS` keeping `divine_sexual_arts`'s `stimulus_applied` target-scoped (D-9). Opposite-sex casts emit `first_vaginal_penetration` and break `virgin` on both parties; both-female/both-male emit the matching experience event without breaking it; either party `other`/unknown (incl. every `Monster`) emits nothing. S1's `sex` field gets its first consumer; the participant-scoped semantics also closes C4's design D-3 recipient asymmetry for 乳交 / 異種交合. | B5, B8, **S1** | `_builder.py`, `sexual_act_effects.py`, `action.py`, `effects.py`, `partner.py` |
| — | `sexual-public-act-events` | `watched_during_activity`, `public_exposure`, and `public_sexual_activity` still had no production emitter. Adds the actor-scoped `sexual_event_actor:` channel, the deterministic `observers_present()` presence read (`RoomActionContext` now injects `event_context["room"]`), observer-gating for `watched_during_activity`/`watched_count`, and the shame catalog's public-event declarations — completing the room-occupancy read C3's design D-4 deferred and the actor-side event channel C3's design D-6 deferred. | `sexual-intercourse-acts` | `targeting.py`, `_builder.py`, `shame.py`, `sexual_act_effects.py`, `action.py`, `effects.py` |
| — | `combat-panel-skill-capacity` | The combat panel's `MAX_SKILLS = 32` presentation bound vs. the catalog's 63 new active skills (154 obtainable active skills total, against 32): raise the bound to 192 across the four mirrors (`combat_view.py`, `combat_panel.py`, `protocol.js`, and the boundary tests), keep the flattened-total semantics, and gate the raise on a measured byte-fit test against the OOB envelope (`MAX_CANONICAL_JSON_BYTES` / `MAX_LIST_ITEMS`). | A2 | `combat_view.py`, `combat_panel.py`, `protocol.js`, panel/protocol tests |

**The three post-implementation review proposals.** A code review of the shipped system found three
wiring gaps the original sequence left open. (1) C4's own deferral of 交合/深度交合 (design D-2) meant
`first_vaginal_penetration`, `penetrative_sex_with_male`, and `penetrative_sex_with_female` still had
no production emitter: `virginity_once` could never fire, `virgin` could never break through play,
and S1's `sex` field had zero consumers — `sexual-intercourse-acts` closes that loop, and its
participant-scoped event semantics also fixes the recipient asymmetry C4's design D-3 documented for
乳交 and 異種交合. (2) `watched_during_activity`, `public_exposure`, and `public_sexual_activity`
still had no emitter, and C3's own D-4/D-6 notes explicitly deferred the room-occupancy read and the
actor-side event channel — `sexual-public-act-events` is that follow-up, and it closes the "被觀看/露出
experience types can never be granted" gap in the same move. (3) the catalog's 63
active skills push realistic characters past the combat panel's `MAX_SKILLS = 32` presentation bound,
taking the whole combat action panel down with a `CombatViewError` — `combat-panel-skill-capacity`
reconciles the bound with the enlarged skill universe. The first two re-enter `action.py`'s event
handling and the `_act_family()` effects shape; they SHALL be implemented and archived in that order
(see §4.4).

**`B5`'s stated emission obligation was not fulfilled.** `B5`'s row above quotes this document's own
original instruction: `B5` was to emit the `EventEntry(kind="sexual_resist", ...)` contract `B6b`'s scan
consumes, "regardless of `B5`/`B6b` batch order." `B5`'s actual archived proposal
(`openspec/changes/archive/2026-08-16-sexual-act-effects/design.md`, Non-Goals) declined it instead: "No
resist contest — this proposal's handlers assume the act's cast already succeeded; whether it should have
been resistible is `sexual-resist-contest`'s and `sexual-resist-turn-cost`'s territory." `B6b`, in turn,
shipped only the consequence side and documented as a known risk that it has "no production caller until
`sexual-act-effects` lands and actually emits `sexual_resist`-kind entries" — relying on this document's
`B5` assignment as the reason it did not need to build the emission itself. Neither proposal closed the
loop, so `resist_verdict()` (`B6a`) had no caller and every `resistible=True` act executed unconditionally
until `sexual-resist-cast-wiring` (above) was proposed to pick up the obligation `B5`'s row describes but
did not deliver.

### 4.3 Parallel batches

| Batch | Parallel tracks | Notes |
|---|---|---|
| 1 | `S1` ∥ `C1` ∥ `A1` ∥ `B1` ∥ `B7` | Five independent tracks. `B7` can run alongside `B1` **only because** D-3 keeps `arousal` comparable, so `combat_modifiers.yaml` needs no edit from `B1`. `S1` owns `world/imports/` and `typeclasses/`, which nothing else in the set touches. |
| 2 | `A2` ∥ `A3` ∥ `B2` | `A2` is the tightest single day in the plan: each combat browser test boots its own Evennia server (~35–70 s each). Do not pair a second track with it for the same implementer. |
| 3 | `B3` ∥ `B4` | `B3` owns `combat.py`/`clock.py`; `B4` owns `world/skills/`. |
| 4 | `B5` ∥ `B6a` | `B6a` is deliberately specified as a pure function so it can run beside `B5`. |
| 5 | `B6b` ∥ `B8` | |
| 6 | `C2` ∥ `C3` ∥ `C4` ∥ `C5` ∥ `C6` ∥ `C7a` ∥ `docs` | Seven fully parallel tracks, zero conflict — pure data rows in disjoint modules. |
| 7 | `C7b` | Runs alone; it re-enters `sexual_state.py`. |
| 8 (unscheduled) | `sexual-resist-out-of-combat` | Not part of the original sequence; ready to schedule once `B6b` lands and its `_scan_sexual_coercion` pattern exists to mirror at the out-of-combat cast path. |
| 9 (unscheduled) | `sexual-resist-cast-wiring` | Not part of the original sequence; picks up the emission obligation `B5`'s row assigned but did not fulfil (see the note under §4.2's table). Ready to schedule once `B5`, `B6a`, and `B6b` have all landed — all three already have. |
| 10 (unscheduled) | `sexual-intercourse-acts` | Post-implementation review proposal; owns the D-12 branch and the participant-scoped event semantics (see the second note under §4.2's table). |
| 11 (unscheduled) | `sexual-public-act-events` | Must follow batch 10: both re-enter `action.py`'s event handlers and the `_act_family()` effects shape, and its delta specs are written against the post-10 main specs (see §4.4). |
| 12 (unscheduled) | `combat-panel-skill-capacity` | Independent of batches 10–11; touches only the combat panel/protocol files and their tests. |

Seven batches for the original twenty-two proposals. With the parallel tracks actually staffed, the
critical path is **seven working days**; implemented serially it is twenty-one. The deferred
follow-ups (batches 8–12) each add at most one more day once scheduled; batches 10 and 11 are
strictly ordered (§4.4).

### 4.4 Serialization constraints

Three things cannot be parallelised and must be scheduled explicitly.

- **Delta-spec sync at archive time.** Each proposal's `openspec/changes/<name>/` directory is
  conflict-free by construction, but archiving syncs deltas into the shared `openspec/specs/` tree.
  **Two proposals in the same batch must not be archived concurrently**; queue them.
- **The `sexual_state.py` spine.** `B1 → B2 → B3 → C7b` all edit the same module and cannot be
  reordered or merged into one day. They already fall in batches 1, 2, 3, and 7 respectively, so the
  spine is naturally staggered — but this is the constraint that fixes the overall batch count at
  seven, and any re-planning must preserve it.
- **The `action.py` event-handler seam (`sexual-intercourse-acts` → `sexual-public-act-events`).**
  Both follow-ups edit the `sexual_event:` recipient semantics and the `_act_family()` effects shape
  (plus their shared `sexual-act-registry` / `sexual-act-effects` delta requirement blocks). They
  cannot be parallelised: `sexual-public-act-events` SHALL be implemented and archived after
  `sexual-intercourse-acts`, and its delta requirement blocks are written against the
  post-`sexual-intercourse-acts` main specs.

### 4.5 Why `B4` ships empty stubs

`B4` creates `world/skills/sexual_acts/` with `solo.py`, `shame.py`, `partner.py`, `combat.py`,
`interspecies.py`, and `divine.py` **already present and already imported by `__init__.py`**, each
exporting an empty tuple. Batch 6's seven tracks then each fill exactly one module and touch nothing
else. Without the pre-declared stubs, `__init__.py` becomes a seven-way conflict point. Explicit
stubs are preferred over package auto-discovery to match this codebase's stated preference for
deterministic, inspectable registries over import-time magic.

---

## 5. Testing Strategy (cross-cutting)

Per-area strategies live in the individual documents. Three obligations apply across the whole set.

1. **Every main-spec requirement gets a substantively matching test**, annotated with
   `covers_requirement` using IDs obtained from `tools.spec_traceability list`. There is no waiver
   for an uncovered requirement.
2. **Structural tests, not conventions.** Following `sexual.yaml`'s existing
   `test_every_rule_id_has_a_test()` and `test_field_kinds_covers_every_targetable_field()`
   precedent, this set adds registry-load-time or test-time structural checks for: every skill
   declaring a category (A1); every act applying non-zero actor pleasure unless
   `requires_divine_arts` (D-4/D-9); no act declaring `GENERIC_BODY_PART`; no 異種 act declaring a
   target part; every counter named by an act existing in `SexualState`.
3. **Determinism.** Every contest and every random delta takes an injectable RNG, matching
   `sexual_transitions.py`'s existing `rng=` seam and `disengage.py`'s testable contest.

---

## 6. Explicitly Out of Scope

- **A `精神力` resource for divine arts.** Deferred for the same reason the skill-system redesign
  deferred it (D7): nothing consumes it, and divine arts are contained by the race gate instead.
- **Monster policy selecting sex acts.** `monster_behaviour_policy()` is untouched by this set;
  monsters remain targets, not initiators. Unlimited suppression by a monster is therefore not
  reachable in this set even though the extension mechanic permits it in principle. Making monsters
  initiate is a separate proposal that must revisit the soft-lock analysis in
  [Sexual Pleasure Model](2026-08-15-sexual-pleasure-model-design.md) §5.
- **Toy/consumable items as real inventory objects.** The `玩具` acts in the catalog gate on the
  `玩具使用次數` counter, not on possessing an item. Integration with `world/skills/equipment.py` is
  noted as a future seam in the catalog document.
- **Per-archetype monster sexual baselines.** Unchanged from the `sexual-state-handler` spec's
  2026-08-09 amendment: one uniform generic baseline.
- **LLM narration of acts.** `world/ai/` is untouched. Acts emit EventLog entries exactly as every
  other action does; the Narrator consumes them through the existing path with no new seam.
