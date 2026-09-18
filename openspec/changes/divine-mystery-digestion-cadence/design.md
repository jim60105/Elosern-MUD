## Context

`grant_skill_practice_xp()` in `world/rules/progression.py` is the single accrual entry point. It
already refuses a `nonlethal` (simulated) resolution, refuses PASSIVE skills, and claims
`(actor, skill_key, target)` in a transient module-level per-tick dedupe before awarding. The
divine-mystery redesign (`docs/lore/skill-trees/divine-mystery.md` §3) adds one further gate on top
of that, for one skill category only. See `proposal.md` — Why for motivation.

## Goals / Non-Goals

**Goals:**

- One brake, one authority, one gate site: the cadence lives beside the existing tick dedupe in the
  same function, so no caller learns a new rule.
- The brake survives a reload and rolls back with a failed commit.

**Non-Goals:**

- Any change to how much XP an accrual is worth, to the cap derivation, or to the freeform ladder.
- Any change to skill ownership or to the prerequisite gate. Acquisition stays exactly as the shipped
  lineage rules define it; the redesign deliberately dropped the 鑽研制 idea.
- Any "meaningfulness" predicate of its own (see D5).

## Decisions

### D1: Scope by `SkillCategory.DIVINE_MYSTERY`, not by `requires_divine_arts`

The flag is carried by the 情慾秘術 divine line too. Gating on it would silently slow that line's
progression, which the lore change holds constant on purpose. The category is the exact set the
cadence is designed for and the exact set the catalog change will populate.

*Alternative rejected:* a per-skill opt-in field on `SkillDef`. It would spread a single rule across
a dozen data rows and let a future node forget it.

### D2: Day identity is an absolute day ordinal derived from the world calendar

`WorldClock.calendar` yields a `WorldDateTime` (`year`, season, day, …) built from the `clock.yaml`
constants `days_per_season` and `seasons_per_year`. The claim stores a monotonic ordinal computed
from those same constants, so the brake means "a calendar day" rather than "N ticks" and stays
correct if tick length is ever retuned. The derivation reads the rulebook, never a literal.

*Alternative rejected:* `tick // ticks_per_day`. It couples a design-level rule to tick arithmetic and
silently changes meaning whenever the clock is retuned.

### D3: The claim is a persisted attribute inside the progression snapshot face

`entity.db.skill_practice_day` holds `{skill_key: day_ordinal}`. It is registered everywhere
`skill_proficiency` already is, so a rolled-back commit restores it byte-for-byte with the XP it
guards. Those places are, precisely: the dict-based `_snapshot_entity_state`/`_restore_entity_state`
pair in `world/rules/action.py` (the mechanism behind the `progression` surface, and the one the
combat round path reaches through `_snapshot_touched` — `world/rules/combat_session.py` holds no
attribute tuple of its own), plus the explicit attribute tuples in `world/rules/cast_settlement.py`
and `world/rules/clock.py`.

*Alternative rejected:* a transient module-level dict like the tick dedupe. A reload would reset the
brake, which turns a daily gate into a reconnect button.

### D4: The cadence gate runs before the tick claim

Order matters for the transient dedupe set, not for the outcome: a day-blocked call returns `False`
without taking a tick claim, so `practice_claims_for()` and `release_practice_claims()` keep
describing only claims that could have produced an award.

### D5: "Meaningful use" is not a new predicate

The lore text ("對真實、會被影響或改變狀態的目標生效才算數，對空處連發一律不計") describes a property the
shipped pipeline already enforces: accrual is reached only after targeting validation and only inside
a committing resolution. A cast at nothing is rejected before it gets here. The cadence therefore
consumes a day exactly when an award would otherwise happen, and invents no second notion of
meaningfulness.

A consequence, accepted deliberately: a use of a skill already saturated at its derived tip cap still
consumes the day. It accrues nothing either way, so the distinction is unobservable.

## Risks / Trade-offs

- **A day ordinal that disagrees with the clock's own season/year roll** → derive it from the same
  `clock.yaml` constants the clock itself loads, and test the season boundary and the year boundary
  explicitly.
- **A rolled-back commit burning the day** → the attribute rides the same snapshot tuples as
  `skill_proficiency`; a test asserts the attribute is byte-equal to its pre-action value after a
  rolled-back resolution.
- **The brake making a divine node feel dead in a single session** → intended. The lore prices the
  chains at 80–90 game days, and out-of-combat casting advances the world clock, so a player who
  wants to progress advances time rather than repeating a cast.
