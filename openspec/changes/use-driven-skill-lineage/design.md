# Design: use-driven-skill-lineage

Implements D4 (§8), D5 (§9), D6 (§10) of
`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md`.

## Context

After A (static rename) and B (XP engine retirement), practice proficiency is
the only growth counter, its formula reader (`growth_rate_multiplier`) is
readerless, and the cast gate is interim (ownership + MP). The registry holds
every fire-tree key already (`fire_arrow` … `phoenix_eternal_flame`,
`infernal_wrap`, `hellfire`, `world_ending_blaze`, `fire_mastery`); only the
edges are new content. `SkillDef` is a frozen dataclass validated at import.

## Goals / Non-Goals

- Goals: prerequisite DAG + validation; one gate; generalized accrual; caps +
  dedupe; ladder re-anchor; auto-seed.
- Non-Goals: proficiency combat bonuses (rejected in review), branching
  content (code supports n-ary DAG; content stays linear), panel/UI (change D),
  declared-practice writer (change E), shared-XP-per-family (new registry
  field = new change).

## Decisions

### DC1: `SkillPrerequisite` on `SkillDef`, validated at registry load

`@dataclass(frozen=True, slots=True) class SkillPrerequisite: skill_key: str;
min_proficiency: int` (≥ 1). `prerequisites: tuple[SkillPrerequisite, ...] =
()`. Five load rules (design §9.3): keys exist; graph acyclic (topo-sort, the
exception names the cycle); thresholds are ints ≥ 1; no-prereq = root;
reverse-edge map computed and cached at import. Rationale: fail at import,
never at play; the cached reverse map is what makes tip-cap lookup O(1).

### DC2: one predicate, every call site

`can_use_skill(entity, skill) -> bool` in `world/rules/progression.py`:
ownership, then every declared edge (owned + `skill_proficiency_level ≥
min_proficiency`). It replaces the interim gate at `ActionResolver`
step-1/preflight/resolve, shared preview + submission revalidation, both skill
menus, and `default_attack_policy`. Mastery override paths stay deleted —
主宰-tier entry is the prerequisite path (AND semantics), and the five
`cost_tiers` bands remain display-only data labels. Rejection surfaces the
missing prereq + required level (data from the registry) through the existing
rejection interface.

### DC3: accrual formula and transaction seam

Every successful ACTIVE resolution stages `grant_skill_practice_xp(actor,
skill_key, target=...)` inside the existing action snapshot/restore face:
`SKILL_PRACTICE_XP_PER_USE × RACE_REGISTRY[race].learning_multiplier ×
element_affinity_multiplier(entity, skill.element)` (physical /
non-elemental → 1.0; the affinity reader is B's surviving pure query) `×
growth_rate_multiplier(entity)`. Storage unchanged (`skill_proficiency` float
XP, `level = floor(xp / 50)`). PASSIVE never accrues; `nonlethal` skips. The
conferred-buff pull path regains its live reader (edits B's
`buff-handler-integration` wording).

### DC4: caps + per-tick dedupe (anti-grinding)

`cap(S)` = max `min_proficiency` over consuming edges, else
`PROFICIENCY_TIP_CAP` (yaml, 10). Grant saturates: once
`level ≥ cap(S)`, XP stops. Dedupe key `(actor, skill_key, target)` at most
once per world-clock tick, in a transient module-level dict cleared on tick
change — never persisted, never snapshotted (rollback-safe: a rolled-back
action may legitimately re-dedupe). AOE counts once per distinct target;
out-of-combat casts advance the clock so consecutive casts land on different
ticks. Rationale: grinding a fully-consumed node yields exactly zero, killing
the "fireball at the air" pathology mechanically, and the dedupe state being
transient means it cannot corrupt any atomic snapshot face.
The saturation rule lives in ONE internal primitive — `award_practice_xp(entity,
skill_key, xp)` clamps storage at `cap(S)` and is the only writer of
`skill_proficiency` for accrual purposes. `grant_skill_practice_xp` computes the
multiplied per-use amount and calls it; `declared-practice-skip`'s hourly
settlement SHALL call the same primitive with its closed-form amount, so
per-use and booked practice can never diverge at cap boundaries.

### DC5: freeform ladder re-anchor

Eligibility keeps the `<element>_mastery` key-presence check (direct
ownership only); the allowed scale set then reads the skill's own proficiency:
0.25 unconditional, 0.5 ≥1, 1.0 ≥3, 2.0 ≥6, 4.0 ≥10 (yaml ladder constants).
Interaction with DC4 is intentional: a cap-5 mid-tree skill tops out at
scale 2.0; only canopy skills (default cap 10) reach 4.0. Deterministic,
rendered by the (future D) panel, nothing hidden.

### DC6: import auto-seed inside the all-or-nothing transaction

For every owned skill whose declared edges are unsatisfied, seed each
prerequisite's proficiency to exactly the required value (never above). Runs
before schema range validation so malformed imports still reject
all-or-nothing; explicit imported `skill_proficiency` always wins. NPC scene
builder shares the helper. Rationale: imported grandmasters own deep skills
and must be able to use them without inventing a practice history.

## Risks

- Gate regressions across menus: mitigated by making preview/menus/policy all
  call the one predicate; scenario-level tests per surface.
- Cap saturation surprising players: rendered as 「見頂」 by change D;
  cap is always ≥ any single consuming edge, so a capped skill never blocks a
  child.
- Dedupe dict growth: cleared on tick change; keyed by small tuples; bounded
  by one tick's distinct actions.

## Migration Plan

One-shot cutover, no shims (unreleased). Land registry content (edges) in the
same change as the validator — an edge without a validator would ship
unvalidated data.

## Open Questions

None blocking: sibling-fire edges are authored as示意調值 in the design and
may be playtested freely (they are data, not structure).
