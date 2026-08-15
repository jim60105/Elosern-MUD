## Context

A non-Monster NPC (no `threat_tier`) is delegated to `combat.default_attack_policy` by `monster_behaviour_policy` (`world/rules/monster_behaviour.py:300-301`). That policy's candidate scan (`world/rules/combat.py:503-519`) selects the first owned `ACTIVE` `damage:` skill that is affordable, with no spell-tier gate. `ActionResolver._step1_ownership` (`world/rules/action.py:229-240`) is the authoritative gate: it derives the spell's tier via `spell_tier_for` (`world/skills/cost_tiers.py:41-75`) and applies `can_cast_spell_tier` (`world/rules/progression.py:149-169`), rejecting an unmet gate with `UNKNOWN_SKILL`. `run_round` (`world/rules/combat.py:573-579`) keeps only successful results, so the rejected request vanishes and the companion repeats the same invalid pick every round.

The reachable payload is a valid import: `world/imports/validate.py:344-356` checks magic cap, affinity bounds, and registry-key existence only, never spell tier, and `world/imports/loader.py:59-84` persists literal `magic_level` and the authored `skills` order. `world/skills/handler.py:39-45` orders `owned_keys()` active-then-passive-then-innate (`"flee"`, `"basic_attack"`), so an imported spell always precedes `basic_attack`. A human NPC with `magic_level=15`, `affinity_elements=[]`, `mp>=30`, and `skills=["firestorm"]` legally passes import; `firestorm` is 術師-tier (30 MP, area band 26–34), `floor(15 × 1.0) = 15 < 16`, and the empty affinity matters (fire affinity would give `floor(15 × 1.1) = 16` and pass). The NPC joins via `party.join_party` (`world/rules/party.py:361-384`) and enters the allied roster via `combat_session.engage` (`world/rules/combat_session.py:563-606`).

The Monster path already applies the gate: `monster_behaviour._gate_allows` (`world/rules/monster_behaviour.py:155-169`) filters `_owned_damage_skills` (`:172-188`) and falls back to `basic_attack` — the design doc for the cast gate only hardened the Monster filter (`openspec/changes/archive/2026-08-13-element-mastery-cast-gate/design.md:47-50`), leaving the generic policy divergent.

## Goals / Non-Goals

**Goals:**
- One public, side-effect-free spell-tier eligibility predicate in the deterministic core, consumed by `ActionResolver`, the Monster policy, and the generic NPC policy.
- A non-Monster companion with an over-tier spell selects the next legal candidate (`basic_attack`) and acts every round; no policy output is rejected by the resolver's tier gate.
- Behavior-preserving for every currently-supported path: mastery override, affinity boundaries, and the Monster policy's existing fallbacks.

**Non-Goals:**
- Wiring the predicate into combat preview/submission revalidation (`world/rules/action_preview.py`) — owned by the parallel change `fix-combat-preview-tier-gate`, which depends on the predicate introduced here.
- Changing `run_round`'s handling of rejected or `None` policy results (after the fix, the supported policy paths cannot produce a tier-rejected request; a defensive rejection event is deliberately out of scope).
- Changing import validation to reject over-tier skills at load time (a supported character may legitimately own a spell it cannot yet cast — e.g. a mastery later unlocks it; the gate is a cast-time query by design).
- New `RejectReason` members or new command/schema surfaces.

## Decisions

**D1 — Promote the gate into a public predicate `can_cast_skill(entity, skill) -> bool` in `world/rules/progression.py`.** It composes the existing pure queries — `spell_tier_for(skill)` (`None` → `True`), then `can_cast_spell_tier(entity, skill.element.key, tier)` — and converts any `ValueError` (malformed MP cost, unknown element, unknown tier) to `False`, failing closed. This is exactly the semantics of `monster_behaviour._gate_allows` (with `skill.element.key` instead of a pre-validated element), moved beside its two building blocks so `world/skills/` stays a registry/read layer and `world/rules/` remains the deterministic core. *Alternative considered:* a duck-typed per-consumer copy — rejected, because that is the bug (three divergent duplicates already exist: resolver inline block, `_gate_allows`, and the missing generic-policy check).

**D2 — `ActionResolver._step1_ownership` consumes the predicate.** The inline `try/except` block (`world/rules/action.py:229-240`) becomes `if not can_cast_skill(request.actor, skill): raise RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)`. Deliberate detail change: a malformed-spell rejection's payload becomes the skill key rather than the `ValueError` message — consistent with the ownership-style rejection the design doc already mandates ("rejects like an unowned-skill cast", no new `RejectReason`), and consistent with the existing preview's shape (`action_preview.py:87` already emits `(UNKNOWN_SKILL, skill_key)`). `player_messages.rejection_message` never interpolates the detail (`player_messages.py:67-74`), so no player-facing message changes. Existing tests assert only `reason is RejectReason.UNKNOWN_SKILL`, so the contract is preserved; the resolver keeps its fail-closed property by construction of D1.

**D3 — The Monster policy delegates to the predicate.** `_gate_allows` is deleted; `_owned_damage_skills` calls `progression.can_cast_skill`. Behavior is unchanged for monsters (the same gate, same fail-closed path), so `test_elemental_spell_above_the_magic_tier_is_never_chosen` and `test_direct_mastery_unlocks_an_elemental_spell_for_the_policy` stay green. The existing malformed-spell test patches `world.rules.monster_behaviour.can_cast_spell_tier`; since the policy no longer imports that name, the test's patch target must move to the shared predicate (or to `world.rules.progression.can_cast_skill`).

**D4 — `default_attack_policy` gates its candidate scan (the fix).** The scan adds the predicate to the existing affordability/filter chain (`world/rules/combat.py:503-519`). Because `owned_keys()` orders imported actives before innates and `basic_attack` is a zero-cost, gate-free ACTIVE `damage:` skill (no MP cost → `spell_tier_for` returns `None`), the over-tier spell is skipped and the first legal candidate is `basic_attack` — the fallback the finding demands, with no retry loop and no new scan logic. Combat sessions reach this path exactly the way the finding describes: every companion turn goes through `monster_behaviour_policy` (`world/rules/combat_session.py:485-491`), which delegates non-Monster entities to `default_attack_policy`. The Monster delegation requirement (`monster-action-policy` spec) remains satisfied: delegation is still exact and unmodified; only the delegated policy's eligibility rule changed. `combat.py` gains `from world.rules.progression import can_cast_skill` (module has no existing progression import, so no cycle: `progression.py` imports only registry/lore/`skills` layers).

**D5 — Tests are behavior-level and deterministic.** Pure `unittest.TestCase` for the predicate and the policy (existing `FakeEntity`/`combat_fixtures` support `magic_level`, `mp`, `owned`, and affinity via plain attribute, which `progression._affinity_elements` reads), plus an `EvenniaTest`-style `run_round` integration proving the companion emits an event every round. New tests carry behavior only; `covers_requirement` annotations are added when the delta requirements are synced into `openspec/specs/` during the archive step (the identifiers do not exist in the main index yet).

## Risks / Trade-offs

- [Risk] Changing the resolver's gate code touches a well-tested pipeline step (`action-resolution-pipeline`, `element-mastery`); a regression would change rejection outcomes. → Mitigation: the predicate preserves exact semantics (verified against `ElementTierCastGateTests` in `test_action_pipeline_rejections.py:141-230`, which must stay green unchanged); tasks run that file plus the monster-policy and progression suites.
- [Risk] The malformed-spell test patch target changes with D3; if the patch is left stale it would silently no-op (test still passes for the wrong reason). → Mitigation: task 3.2 explicitly re-points the patch at the shared predicate and the task's acceptance includes re-running the test with the failure mode re-proven (patched predicate raising must still yield `basic_attack`).
- [Risk] A future consumer could bypass the predicate and re-embed the gate, reintroducing drift. → Mitigation: the `element-mastery` delta requires all AI policies and the resolver to consume the single predicate; the parallel `fix-combat-preview-tier-gate` change closes the remaining preview surface on the same helper.
- [Trade-off] A companion whose only damage skill is over-tier now falls back to `basic_attack` instead of being a silent no-op; its per-round power is lower than an author may have intended, but it is always legal, always acts, and never wastes MP.

## Migration Plan

No data migration: the gate is a pure cast-time query, never a stored fact. No schema change, no command-surface change, and no player-facing documentation change. The change lands independently of `fix-combat-preview-tier-gate`, which depends on the predicate introduced here.

## Open Questions

None.
