## Context

World lore (`tmp/story_settings/world_info.md`, not committed) defines five magic-level bands
(學徒 0–15, 術師 16–30, 大師 31–70, 賢者 71–90, 主宰 90+) as both a display title and (per character
data cross-referenced in the approved design doc) a mechanical gate on which tier of spell a caster may
use, with an explicit override: owning an element's mastery skill unlocks every spell of that element
regardless of numeric level. No existing code implements either half.

## Goals / Non-Goals

**Goals:**
- `magic_rank_title` and `can_cast_spell_tier` are both pure, side-effect-free queries.
- The two are independent: `can_cast_spell_tier` never consults `magic_rank_title`'s output, and vice
  versa — this is deliberate (design doc D5) to avoid conflating a display fact with a mechanical gate.

**Non-Goals:**
- Does not implement per-element numeric proficiency tracking — both functions read the single global
  `magic_level` trait, per D5's explicit rejection of per-element levels (nothing in the approved
  character data requires them).
- Does not change how `magic_level` itself accrues (that's `magic-level-progression`'s territory,
  unchanged here).
- Does not implement the actual eight new elements' spells — that is each `spell-catalog-*` proposal's
  job; this change only builds the gate they call into.

## Decisions

- **Direct ownership only for the mastery override, no conferred-grant path.** `ConferredSkillGrant`
  (generalized by `conferral-generalization`) explicitly excludes gate-type effects — a "partial spell
  unlock" has no defined meaning. This change's `can_cast_spell_tier` therefore checks
  `entity.skills.owned_keys()` directly, never `entity.skills.conferred_grants()`.
- **Gate hook reuses the existing rejection category**, not a new `RejectReason` member — from the
  resolver's perspective, "you may not cast this" is one class of rejection whether the cause is
  "you don't own the skill" or "you don't meet its tier gate" (this mirrors how `preflight` already
  treats skill-ownership and skill-kind failures as the same rejection shape).
- **Bands are a fixed constant table**, not a formula, matching `magic-level-progression`'s existing
  precedent of expressing tuning as data rather than computed curves.
- **The resolver derives a spell's tier from its MP cost band**, via a new `spell_tier_for(skill)`
  helper in `world/skills/cost_tiers.py`. `SkillDef` deliberately has no tier field; the sibling
  `spell-catalog-*` changes guarantee each spell's tier is unambiguous from its MP cost band
  ("position + cost band" — the position is for human review, the cost band is the mechanical
  signal). `spell_tier_for` classifies only ACTIVE skills that carry both an element and an `mp`
  cost (an "elemental spell"), preferring the §4.3 column matching the skill's `TargetSpec` (`SELF`
  counts as single/direct) and falling back to the other column, since a few catalog costs sit in
  the opposite column of their tier. An elemental spell whose `mp` cost is missing, non-positive,
  or outside every band **fails closed**: `spell_tier_for` raises `ValueError` and the resolver
  converts it into the same ownership-style rejection, so a malformed spell can never slip through
  ungated. `monster_behaviour_policy` filters its candidate damage skills through the same gate, so
  a monster (magic level 0 in production) never wastes a turn on an elemental spell the resolver
  would reject; the spell-catalog recosts (e.g. `fire_ball` → 學徒) later re-open the two anchor
  spells to monsters by lowering their threshold to 0.
- **The 90/91 boundary resolves the lore's overlapping top bands.** The lore table writes 賢者 as
  71–90 and 主宰 as 90+; the sibling spell-catalog gate scenarios pin magic level 90 as *below*
  主宰 (level 90 without mastery is rejected for 主宰-tier spells), so the mechanical threshold
  table sets 主宰 at 91. `magic_rank_title` scans the literal bands in order, resolving the overlap
  at exactly 90 toward 賢者. With the human magic cap at 90, this makes "humans can rarely ever
  cast 主宰-tier spells" (world lore) a mechanical fact.

## Risks / Trade-offs

- [Risk] Wiring into `ActionResolver.preflight`/`resolve` touches a well-tested, eight-step pipeline
  (`action-resolution-pipeline` spec). A careless insertion point could break an existing scenario.
  → Mitigation: task list requires reading the full pipeline before inserting, adding the gate check
  as an additional condition in the *existing* skill-validation step rather than a new step, and
  running the full existing `action-resolution-pipeline` scenario suite before/after.

## Migration Plan

No data migration for existing entities — `can_cast_spell_tier` is a pure query evaluated at cast time,
not a stored fact. Lands after `skill-effects-typed-model`; before every `spell-catalog-*` change.

## Open Questions

None.
