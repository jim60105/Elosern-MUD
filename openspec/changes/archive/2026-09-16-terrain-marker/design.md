## Context

Delivers the generic **ground-hazard marker** primitive the earth wave's terrain line needs — 地裂術's 「地面裂開成縫，留在裂縫上的目標承受…DoT」、地震術's 「附加裂縫地形標記」、大地神格's 「覆蓋全場的裂縫地形（留在其上者吃…頂規 DoT）」、and 大地審判's 「對站在裂縫標記上的目標額外 +0.6」 (`docs/lore/skill-trees/earth.md`; constitution §4.2 earth row: 困難地形標記的召出者). Per the user-ratified naming requirement the primitive is element-agnostic mechanic vocabulary; the earth rows (keys, durations 60/40/90 s, DoT rungs −12/−40 per 10 s, the +0.6 synergy data) belong to `earth-spell-catalog`. Pre-audited engine facts (verified at e7234ad):

- **No terrain/position primitive exists.** In-combat position is binary — the battlefield roster tracks `fled`/`knocked_out` sets only (`world/rules/combat_session.py`); there is no tile, zone, or ground state anywhere in `world/rules`. Room-level `TerrainRoom`/wilderness terrain is out-of-character exploration flavor, not a per-combatant condition, and is not extended here.
- **The buff layer already models exactly this shape**: `paralysis`, `fear`, `water_bind` are marker-only rows whose whole meaning is「holding the key」(the shipped definition requirement even names them marker buffs), detection rides `entity_active_buffs`, duration/refresh/expiry ride world seconds, and damaging rate rows tick through `_apply_rate_modifier` with the shipped attribution. Recommended modeling (adopted, D1): the marker is a buff mounted on the individual; 「站在裂縫上」 == 持有該 marker 實例.
- **`DamagePolicy.predicate` is static-only today**: `matches_target_predicate` (`world/rules/target_facts.py`) unions `get_affinity_elements` ∪ `get_combat_traits` only, and `DamagePolicy.__post_init__` rejects ANY namespaced entry (`test_namespaced_predicate_entries_raise` pins it). 大地審判's synergy needs a dynamic「target holds buff X」fact — this is a strict-superset MODIFIED delta on `skill-effect-model::conditional-damage-policies-compose-without-double-matching` (D3).
- **`modifiers` keys are a closed exhaustive set** (`rate`/`bounds`/`divert`/`decay`, fail-closed load). The marker clause therefore rides as a **top-level definition field** beside `duration`/`stacking`/`polarity` (D1), not a `modifiers` key — the modifier table stays what its requirement says it is.
- **Buff lifecycle is already the shipped shape** — duration expiry, `refresh` stacking, dispel/cleanse via `remove_by_selector`, grant-time source attribution. The only lifecycle gap a ground hazard needs is battlefield-exit extinguishment (D2): today buffs persist across combat sessions by design (equipment/aftermath markers rely on it), which is right for a carried status and wrong for cracked ground.

User-ratified givens: **no second rules engine, no element-key branches in generic code** — every addition is declarative vocabulary on existing surfaces. **NON-GOAL: 遊戲資料契約** — verification is behavior contracts on synthetic buffs/skills/state transitions only; this change ships zero live marker rows (inert-but-valid vocabulary, the `caster_share` precedent). **Clean cut, zero users**: no migrations, no aliases.

## Goals / Non-Goals

**Goals:** One declarative marker clause on the buff-definition grammar; holding-the-marker == standing-on-it as the canonical fact; world-second duration/refresh semantics inherited unchanged; flee/knockout/session-end extinguishment scoped to marker rows; a `buff:<key>` dynamic-fact entry in the DamagePolicy predicate vocabulary; behavior-test-only proof; every piece generic — fire's future on-ground hazards and any later element ride the same fact.

**Non-Goals:** No earth registry rows or marker buff rows (`earth-spell-catalog` authors all data); no room/tile/zone state, no world-clock terrain system, no wilderness-terrain coupling; no action-lock or 束縛 semantics (the lore explicitly routes 鎖動作 to ice's verbs); no `combat_modifiers.yaml` rows (the marker's consequences are either its own rate/bounds rows — catalog data — or the +0.6 synergy policy — D3); no `state_reactions.yaml` change (owned by the sibling `on-hit-counter-damage` change); no data-contract tests.

## Decisions

### D1 — Carrier: a top-level `marker: ground` clause on the buff definition, not room state, not a modifiers key

| Axis | buff-definition marker clause (chosen) | room/ground state (rejected) | `modifiers` key (rejected) |
|---|---|---|---|
| Position model | none needed — 「留在裂縫上」 has no movement verb in this engine; the lore's own semantics are「留在/站在」 = the target the hazard was applied to keeps suffering it until it leaves the fight | requires a per-combatant position axis that does not exist; inventing one collides with flee-only binary position and buys nothing no-buff solution can express | — |
| Lifecycle | expiry/refresh/dispel/cleanse already shipped and battle-tested | new scheduler/state = second rules engine, constitution-forbidden | — |
| Grammar integrity | top-level field beside `duration`/`polarity`; `modifiers` stays the closed {rate,bounds,divert,decay} table its requirement pins | — | adding a 5th `modifiers` key rewrites the exhaustive-list sentence and mixes identity (what the row IS) with effect (what it DOes) |
| Fact read | `entity_active_buffs` already answers 「holds the key」 for `combat_modifiers`, `spell_conditions` and (via D3) DamagePolicy | new query surface | — |

Clause shape: `marker: ground` (a top-level string field; closed vocabulary `{"ground"}` at `load_buff_definitions`; malformed value names the offending key and fails the load). The hazard's damage and 敏捷 −3 ride the SHIPPED `rate` + the shipped `ice_slow` reuse as pure data later — the clause adds zero effect behavior by itself; it marks the row as ground-hazard vocabulary and arms the D2 exit sweep. The standing-on-it fact is「the entity has a live instance of a definition carrying the clause (or, for a predicate query, of the named key)」 — no element key is read anywhere.

### D2 — Battlefield-exit extinguishment: a scoped sweep at the existing session-settlement writes

Markers must not follow an entity out of the battlefield. The removal rides the existing `remove_by_selector`/instance-removal path (zero new removal machinery, no damage/revive side effects) and fires at exactly three already-persisted transitions in `world/rules/combat_session.py`: (a) when a round's settlement persists a newly `fled` participant, (b) when it persists a newly `knocked_out` participant, (c) at session end (win/loss/withdraw — the existing teardown). The sweep consults only definitions declaring `marker: ground` — non-marker rows are never touched, so equipment-granted, aftermath and carried-status persistence is byte-identical. A marker on a still-active combatant survives rounds untouched until its own duration elapses (the existing per-round upkeep ticks it). Each sweep removal is a persistent transition, so it logs one observability boundary line (facade `log_info`, the shipped convention) — no new event vocabulary. Knockout-vs-defeat: knockout already floors HP at 1 and marks the battlefield; defeat settlement already ends the victim's ticks — the sweep makes the marker's own exit fact explicit for knockouts and flee, where the instance would otherwise linger past the fight.

Rejected: per-round expiry-only semantics (a fled monster would keep burning its own ground for up to 90 s of world time and re-enter fights still「standing on fissures」 — observable bug), and tying removal to `BLOCKING_BUFF_KEYS`-style hard-coded key sets (a key branch, forbidden).

### D3 — The predicate seam: `buff:<definition-key>` as the one admitted namespaced fact family

大地審判's 「對站在裂縫標記上的目標額外 +0.6」 is authored as `DamagePolicy(predicate=("buff:<fissure-key>",), attack_multiplier=…)` data in the catalog; this change opens the seam:

1. **Validation** (`DamagePolicy.__post_init__`): an entry with `":"` is accepted ONLY when its namespace is exactly `buff` and its key is in `BUFF_DEFINITIONS`; every other namespaced form keeps failing with the existing message shape, and bare entries keep the ELEMENT_REGISTRY ∪ COMBAT_TRAITS_VOCABULARY check unchanged. Duplicates still rejected (namespaced entries dedupe on their full text).
2. **Matching** (`matches_target_predicate`): entries starting `buff:` are consulted against the target's live buff keys through the shipped no-create `entity_active_buffs` reader — a live, unexpired, non-paused instance matches; anything else does not. Static facts never satisfy a `buff:` entry and vice versa. The existing ANY-semantics and once-per-strike multiplier application are untouched: the extension adds entries to the same loop.
3. **Purity note**: `target_facts.py`'s docstring pins「read strictly from persistent deterministic data」 — a live buff instance IS persistent deterministic data (Evennia attribute-backed); the module stays read-only and never mutates. The docstring's fact-source list widens with the requirement text.
4. **Timing**: the fact is read at strike settlement inside `_handle_damage` (where `matches_target_predicate` is already called), so application/expiry/removal between cast authoring and settlement settles with the instance — the terrain-marker lifecycle (D1/D2) therefore feeds the synergy with zero extra machinery.

5. **Unconditional bypass composes with the dynamic fact (the earths_judgment fit check).** The shipped semantics make `bypass_defense` *conditional* when a predicate is configured (only matching targets bypass; unconditional execution authors today with an empty predicate). `earths_judgment` is 處決級 **unconditionally** and additionally priced on the marker fact — a single component must carry both. Seam decision: an independent `unconditional_defense_bypass: bool` field (default False; the shipped conditional `bypass_defense` semantics unchanged for every existing policy), accepted with an empty predicate (reduces to the shipped unconditional-execution behavior) or any predicate set, REJECTED only co-declared with `bypass_defense=True` (one meaning, one field). The catalog authors 大地審判 as `coefficient=4.0` + `DamagePolicy(predicate=("buff:<fissure-key>",), attack_multiplier=<synergy rung>, unconditional_defense_bypass=True)` and the unconditional bypass never depends on a marker match. Empty-predicate policies keep rejecting a non-1.0 multiplier exactly as today. Consuming the field is a hunk inside `_handle_damage`'s policy-decision block in `world/rules/combat.py` — see the shared-file schedule in D4.

The existing `test_namespaced_predicate_entries_raise` test is updated in-place, not deleted wholesale: its non-`buff:` namespace rejections stay verbatim; the blanket「any colon raises」 pin retires because the requirement changed (behavior-first convention). `test_conditional_damage.py` gains the new dynamic-fact behaviors.

### D4 — Wave interface-ownership matrix (integration contract for all earth changes)

| Interface | First owner | Consumers |
|---|---|---|
| `marker: ground` definition clause + standing-on-it fact + battlefield-exit extinguishment + `buff:<key>` predicate entry | this change (`terrain-marker`) | `earth-spell-catalog` (the 裂縫 rows + `earths_judgment` policy data); any future element's ground hazard (fire's scorching ground is lore-adjacent vocabulary, not this wave) |
| on-hit reaction event carrying the attack source + source-targeted counter action (shape fixed in `on-hit-counter-damage` design.md) | `on-hit-counter-damage` | `earth-spell-catalog` (`thorned_carapace` row); later fire `scorching_armor` on-hit ignite authors as **data** — apply-buff-to-source reuses the same event, the then-vocabulary must admit `apply_buff_to_source`-shaped actions so no new trigger event is needed |
| 14-node registry block + earth buff/modifier rows + status-display census sync + echo-test retirement + shard manifest final state | `earth-spell-catalog` | — |
| (inherited, unchanged) damaging rate rows + `caster_share`, execution bypass, devastation rider, reverse-edge caps, grant-time source attribution, `ice_slow` reuse | archived light/water/dark waves | this wave's data only |

File ownership is disjoint between the two behavior changes EXCEPT one shared file: `world/rules/combat.py` — this change edits `_handle_damage`'s policy-decision hunk (unconditional-bypass consumption) and `on-hit-counter-damage` edits the same function's staged `apply()` dispatch leg (~85 lines apart, textually disjoint hunks, same function). The supervisor therefore SEQUENCES the two merges (this change first; the catalog needs both regardless so the queue order is unaffected). Everything else is disjoint: this change owns `world/rules/buffs.py`, `world/rules/target_facts.py`, `world/skills/effects.py` (DamagePolicy validation), `world/rules/combat_session.py` (exit sweep) + their test modules; `on-hit-counter-damage` owns `world/rules/state_reactions.py`/`.yaml` + its test module. `earth-spell-catalog` edits only `registry.py` earth block, `buffs.yaml`, `state_reactions.yaml`, `status_display.yaml`, echo-test files, shard manifest — strictly after both merge.

### D5 — Batch order

1. `terrain-marker` → `on-hit-counter-damage` — file-disjoint except the shared `world/rules/combat.py` `_handle_damage` (disjoint hunks, same function): the supervisor sequences the two merges, terrain-marker first (declared in both proposals' `## Batch`). Concurrent execution is NOT safe on that one file.
2. `earth-spell-catalog` — after BOTH merge (authors data over their shipped vocabulary).

### D6 — Verification contract, shared by the whole wave

1. **Every test is behavior on synthetic state** — synthetic buffs/skills/entities, real settlement through the action/buff/clock/combat/session stages; tests MUST fail on plausible bugs (marker following a fled holder, sweep touching a non-marker buff, `buff:` entry matching a static fact or an expired instance, multiplier applied per matching entry, a marker clause loading with a junk value, a policy accepting `buff:<unknown>` or a foreign namespace). Source-text, data-echo and row-mirror assertions are prohibited, including in the catalog change.
2. **This change's own proof**: synthetic marker hazard ticking through `tick_buffs`/upkeep; flee/knockout/session-end sweeps observed through real `combat_session` settlement with a non-marker control buff; the predicate entry through `_handle_damage` strikes with live/expired/absent instance states; `load_buff_definitions` fail-closed matrices; policy-construction rejection matrices. New synthetic modules registered in exactly one shard each.
3. **Focused invocation** (each change's tasks.md): `uv run --locked evennia test --settings test_settings.py --keepdb <modules>` with `MUD_TEST_SETTINGS=1` via the tool env, NEVER a shell prefix; plus `tools.observability_lint check`, `tools.test_data_lint check`, `tools.spec_traceability check`, `openspec validate <change> --strict`. No full local suite / browser / aggregate-coverage run; no command above ten minutes.
4. **Traceability**: canonical IDs via `uv run --locked python -m tools.spec_traceability list`; `@covers_requirement` literal IDs only; ledger hygiene at the separately authorized main-sync.
5. **Shards**: new non-browser test modules join exactly one shard in `.github/evennia-shards.json`; the ownership-contract test verifies.

## Risks / Trade-offs

- **Refresh redirects the hazard's origin.** A second caster re-applying the same fissure key refreshes the single instance (shipped stacking). Area re-casts from different casters redirect nothing observable today (markers price no leech); if a future element wants per-caster ground stacks it needs `unique_per_source` keys — vocabulary already exists, no change needed here.
- **Knockout sweep vs nonlethal floors.** Knockout floors HP at 1 and keeps the instance-owner alive; sweeping the marker there means a knocked-out fighter standing on cracked ground stops burning — intended (unconscious bodies don't stand), and the sweep runs inside the same settlement transaction so rollback restores the instance.
- **Session-end sweep is a behavior change scoped to marker rows only** — today no shipped row declares the clause, so nothing live changes until the catalog authors rows; the sweep's control-buff test pins non-marker persistence.
- **`buff:` predicate reads live state at strike time** — a dispel mid-round flips the fact. That is the lore's semantics (you get judged harder only while standing in the fissure); the once-per-strike rule keeps the multiplier un-doubled regardless.
- **Two `buff:` entries for different keys are independent ANY facts** — a spell can declare fissure-or-ash predicates; once-per-strike semantics make OR-with-one-multiplier the only pricing, which is what both planned consumers need.

## Migration Plan

Nothing migrates. Definition-clause validation → exit sweep at the three session transitions → predicate validation/matching extension → synthetic behavior suites → shard registration, in one reviewable slice. Zero live marker rows ship from this change; `earth-spell-catalog` authors every row. Main-spec sync, ledger and freeze-list edits stay in the separately authorized workflow.

## Open Questions

None blocking. One vocabulary tension recorded and resolved at authoring: `earths_judgment`'s 「額外 +0.6」 is phrased as a flat addition while the shipped conditional seam prices multipliers. The node table's 威力係數 column is multiplicative (4.0) and the DamagePolicy seam exposes `attack_multiplier`; authoring the synergy as `attack_multiplier` on the predicate hit lets the catalog pick the multiplier whose product matches lore intent at data time (the catalog change owns the numeric decision; this change guarantees BOTH shapes ride the same entry — a future flat-addend clause, if ever wanted, is a separate grammar addition, not a blocker here).
