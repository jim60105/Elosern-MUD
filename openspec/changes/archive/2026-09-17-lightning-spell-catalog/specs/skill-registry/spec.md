## REMOVED Requirements

### Requirement: SKILL_REGISTRY contains the full 雷-element spell set
**Reason**: The old requirement mandates a duplicated dev-era ten-row data contract (the 2026-08-12 set — no prerequisites, no coefficients, an inert `bounds`-illusion mount pair, no extra-action/order/multi-strike behavior). The ratified wave NON-GOAL rules out lightning catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the skill-tree table.
**Migration**: Delete the lightning catalog echo table and its three echo methods in `world/skills/tests/test_spell_catalogs.py` (the builder-shape MECHANIC test stays — the builder survives as tested grammar with this block as its last caller; `ClosedVocabularyParseTests` untouched), the lightning tier-label echo in `world/skills/tests/test_cost_tiers.py`, the dev-era mount numeric pins in `world/rules/tests/test_buffs.py` re-homed to load/apply/presence per the ratified M4 discipline, and the obsolete traceability/freeze entries during the separately authorized main-sync. Replace this requirement with the behavioral 回合 progression requirement below, backed by synthetic behavior modules and the shipped-primitive contracts only.

## ADDED Requirements

### Requirement: Lightning spell progression composes executable turn-order behavior
The lightning spell family SHALL provide the documented 回合 progression as executable skill behavior using the common effect, audience, policy, buff, modifier, reaction and lineage mechanisms: an extra-action grant mounted as a detectable self-only buff and settled through the turn loop's action-count consumption at the authored duration; in-round order rewriting as declarative position markers only — a self advance mounted by its authoring node and tail retreats reaching the melee attackers of the two detection mounts through the shared outcome-reaction vocabulary and the struck victims of the 神格 canopy through the enemy-audience effect leg, each settled through the round loop's declarative fold at authored keys with already-acted combatants untouchable; the 麻痺 ladder locking every action through the shipped rule-table path at the authored 20/30-second rungs on family-owned keys with the shipped marker-path inventory untouched; a declared-chance micro-rung whose one recorded per-round roll decides the skip; a 多段 rung resolving three independent strikes under the widened cap with the shipped once-paid and single-terminal-emission discipline; a 處決級 execution rung that ignores defense; 毀滅級 devastation rungs; and a two-root branching lineage whose two 主宰 routes converge only at the two-parent 神格 canopy. All numeric values are authored data pinned at load/apply/presence, never re-derived by generic code.

#### Scenario: The extra-action grant provisions its second slot while live and one after lapse
- **WHEN** a synthetic self-only grant composition mounts the authored extra-action row and the round loop next provisions that combatant while the mount is live, and separately the mount is allowed to lapse before the next provisioning
- **THEN** the live-mount combatant receives exactly two action slots at its sequence position within the one round settlement, the lapsed combatant receives exactly one, and no other combatant's slot count changes at either provisioning

#### Scenario: The ward micro-rung marks melee attackers and the declared chance decides
- **WHEN** a synthetic ward carrier is struck by a landed physical attack from a living attacker, then by a magic attack, a missed swing and a sourceless write, and separately the marked attacker is gated by the authored declared-chance lock under fixed losing and winning dice
- **THEN** only the qualifying physical attacker carries the live retreat-marker instance attributed to the ward holder refreshed per qualifying strike, the magic/miss/sourceless paths apply nothing, the losing dice produce the skip event recording the authored chance and the consumed roll while the winning dice let the marked attacker act, and the marker itself mutates no initiative sequence

#### Scenario: The self advance and the canopy tail-push relocate only the still-to-act
- **WHEN** a synthetic self-advance composition mounts its authored advance row on a caster whose round slot has not arrived, and a synthetic canopy area composition strikes victims some of whom have already acted this round
- **THEN** the caster acts ahead of every combatant still to act that round, each struck not-yet-acted victim moves behind them, already-acted victims keep their completed turns, every other relative order is unchanged, and the following round re-rolls clean

#### Scenario: The paralysis ladder locks at the authored rungs on family keys
- **WHEN** a synthetic single-target composition applies the authored base 麻痺 row and another applies the authored enhanced rung, and the clock advances to each authored expiry
- **THEN** each holder's every action attempt resolves zero actions through the rule-table path for exactly its authored duration, the shipped marker-path inventory is unchanged throughout, and expiry restores action resolution

#### Scenario: The three-strike 多段 rung lands three judgments in one paid cast
- **WHEN** a synthetic 多段 composition with the authored count of two extra strikes and coefficient strikes one target under fixed rolls covering an all-hit sweep and a miss-interrupted sweep
- **THEN** exactly three independent rolls are recorded in order with the same authored coefficient per landing strike, resources and practice move once, and at most one terminal defeat or knockout emits regardless of which strikes cross a threshold

#### Scenario: The execution and devastation rungs price their clauses
- **WHEN** a synthetic 處決級 composition strikes a high-defense target, and a synthetic 毀滅級 area composition strikes a mixed battlefield
- **THEN** the execution strike skips defense subtraction entirely and each devastation victim takes the authored coefficient plus its authored maximum-HP share with allies untouched

#### Scenario: Branching and the two-parent capstone gate through the lineage engine
- **WHEN** a synthetic family replicates the documented two-root chains, the authored branch points and the two-parent canopy prerequisite shape
- **THEN** use rejects until every authored threshold is met, the canopy unlocks only when BOTH authored parents reach their authored thresholds, each route progresses independently, and prerequisite caps stay derived from the shared reverse-edge map with leaves at the shared tip cap

#### Scenario: Retired dev-era clauses resolve as ordinary rejections
- **WHEN** a caller casts a never-existing lightning key through the ordinary cast surface after replacement, or references the retired bounds-illusion payloads as effect bindings
- **THEN** each rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on
