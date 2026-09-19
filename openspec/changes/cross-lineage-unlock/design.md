## Context

See proposal.md — Why. The load-bearing facts this design has to sit on, all verified against master:

- **Ownership and usability are already separate.** `can_use_skill()` checks ownership *then* prerequisite thresholds; `SkillHandler.base_owned_keys()` reads `entity.db.skills` (`{"active": [...], "passive": [...]}`) plus the innate set. Adding a key to that storage is the whole of "granting a skill".
- **`award_practice_xp()` is the sole writer of `db.skill_proficiency`.** Two callers reach it: `grant_skill_practice_xp()` (per-use) and the booked-hourly settlement. No other code path can move a proficiency level.
- **`grant_skill_practice_xp()` already runs a before/after snapshot** around the award and appends `unlock_line(candidate)` per newly usable skill into the caller-owned `unlocks_out` list. `world/rules/action/costs.py` owns that list and stages the lines after its transaction commits.
- **Only ACTIVE skills accrue practice.** `grant_skill_practice_xp()` returns `False` for `skill.kind is not SkillKind.ACTIVE`, so every PASSIVE node in the registry sits at level 0 permanently.
- **Proficiency caps are derived, not authored.** `proficiency_cap(key)` is the max `min_proficiency` over the edges consuming `key`, or `PROFICIENCY_TIP_CAP` (10) when nothing consumes it. Every element tree's spell roots (`fire_arrow`, `water_bolt`, `gale_step`, …) therefore cap at **3**.
- **`MARTIAL_ARTS` entries must declare `group is None`** — pinned by `skill-category-registry::category-group-vocabulary-is-closed-per-category`, asserted in `world/skills/tests/test_skill_registry.py`. There is no data dimension separating the sword line from the shadow line.

## Goals / Non-Goals

**Goals:**

- One table shape that expresses both shipped rule kinds (grant a passive) and the future kind (open a tree by granting its roots) without a schema change in between.
- Every unsatisfiable rule is a load-time crash, never a silently dead row.
- Zero new side effects on any read path.
- The three shipped rules reproduce the lore page's acquisition conditions exactly.

**Non-Goals:**

- No `line` field on `SkillDef`. No new lineage tree. No revocation. No proficiency grants. (See proposal.md — Non-goals.)
- No change to how the unlock *line* is worded or delivered — this design reuses `unlock_line()` and the existing `unlocks_out` sink verbatim.

## Decisions

### D1. Two scope forms — declarative and explicit — instead of a registry schema change

A clause's `scope` is either `{category: <c>, group: <g>?}` or `{keys: [...]}`.

The element rules need grouping by element, which `group` already provides. The sword rule needs the nine sword-line keys, which **no** registry field distinguishes — `MARTIAL_ARTS` is spec-bound to `group is None`. The alternatives were:

| Option | Verdict |
| --- | --- |
| Add `line: str \| None` to `SkillDef` | Rejected. Reopens `skill-category-registry`'s closed group vocabulary and its census tests for one rule, and creates a second grouping dimension whose only member would be 劍術/影流. |
| Reuse `group` for martial lines | Rejected. Directly contradicts a shipped spec requirement and its test. |
| **Explicit `keys` list in the clause** | **Chosen.** Costs nine strings in a data file, validated against `SKILL_REGISTRY` at load. When a martial `line` dimension is eventually justified on its own merits, the clause rewrites to the declarative form with no engine change. |

An explicit `keys` scope forms exactly one group: "these nodes, as one line". That keeps `distinct_groups` meaningful and uniform across both forms.

### D2. Validation is load-time and total, driven by `proficiency_cap()`

The reachability check is the one that earns its keep. A clause at `min_level: 5` over a scope whose nodes all cap at 3 is silently dead forever — and given that every element tree's roots cap at exactly 3, this is the mistake an author will actually make. So the loader computes, per group, `max(proficiency_cap(k) for k in group)` and requires at least `distinct_groups` groups to clear `min_level`.

The PASSIVE trap needs the opposite treatment, and an earlier draft of this design got it backwards. `fire_mastery` and its seven siblings are `ELEMENTAL_MAGIC` carrying the **same** `group` as their tree's spells (`fire_mastery.group == "fire"`, verified against the registry). Two of the three shipped rules must scope across all eight element trees to count `distinct_groups`, which means they cannot narrow by `group` — so they unavoidably sweep in all eight mastery passives. A loader that *rejected* a scope containing a PASSIVE node would therefore reject the shipped table itself, contradicting this change's own "the shipped table loads" requirement.

The rule is therefore split by how the node was named:

- A **declarative** scope (`{category, group?}`) samples `ACTIVE` nodes only. The author described a set; the engine gives them the members of that set that can actually hold proficiency. This is stated in the spec rather than left implicit, so "any node in the fire tree" has a written meaning.
- An **explicit** `keys` scope naming a PASSIVE node is **rejected**. Here the author typed that key deliberately, so it is an authoring error and the fail-closed posture applies.

Alternative considered: a `kind` filter on the scope, defaulting to `active`. Rejected as a knob with exactly one useful setting — no rule can ever want a PASSIVE condition source, because no PASSIVE node can leave level 0.

### D3. Push at the award, never pull at the read

Evaluation is called from `grant_skill_practice_xp()` after `award_practice_xp()`, and from the booked-hourly settlement after its award, so the two practice entry points cannot diverge.

The rejected alternative is deriving grants inside `SkillHandler.owned_keys()`. It is tempting — no storage write, always consistent — and it is wrong twice over:

1. `owned_keys()` is called from combat preview, `status_query`, and the no-create read paths. A derivation that grants would make a *preview* write to the database.
2. `world/skills/handler.py` deliberately imports nothing outside `world.skills`. Reading proficiency there would drag `world.rules.progression` into that module's closure and invert the layering.

Evaluation is also naturally rate-limited: practice accrual already dedupes by `(actor, skill_key, target)` per world-clock tick, so repeated casts cannot spin the evaluator.

### D4. Evaluate only the rules a given award could have changed

A full table sweep on every practice award is wasteful and gets worse as the table grows. The loader builds a reverse index from `skill_key → rule ids whose clauses sample that key`; an award for `skill_key` evaluates only those rules, then skips any whose grants the entity already owns in full. With three rules this is an optimisation; with a table that opens trees it is the difference between a constant and a linear cost per cast.

### D5. Grants land in the `passive`/`active` list matching the granted skill's kind

`db.skills` is two lists and `base_owned_keys()` concatenates them, so either list would *work*. Writing by `SkillDef.kind` keeps the stored shape honest for the character panel and the import round-trip, which do read the two lists separately. Granting is append-if-absent; an already-owned key is a no-op, which is what makes re-evaluation idempotent and makes preset-granted keys (薇歐蕾特 ships with two of the three) collide harmlessly.

### D6. No-cycle rule is enforced structurally, not by traversal

Because grants may never appear in any clause scope (spec requirement), the grant graph has depth 1 by construction and no cycle detection algorithm is needed — a set intersection between "all granted keys" and "all scoped keys" at load is sufficient and total. This is stricter than acyclicity, deliberately: the lore page's constraint 5 wants every tree opening to be a decision the player paid for, not a chain reaction.

## Risks / Trade-offs

- **An entity whose proficiency was seeded by import, not practice, never triggers a rule.** → Accepted and intended. The character loader seeds prerequisite proficiency inside its transaction without routing through `grant_skill_practice_xp()`, so an imported character does not retroactively collect grants. Imports already declare ownership explicitly, which is the authoritative path for an authored character; rules exist for *earned* acquisition. Called out here so it is not later mistaken for a bug.
- **Grants are invisible until the next practice award.** → Accepted. A player who is already past a threshold when the table ships receives the grant on their next qualifying cast, not at login. No backfill migration is written (zero users; pre-release).
- **The nine sword keys are duplicated between the data file and `docs/lore/skill-trees/cross-lineage-unlock.md`.** → Mitigated by load-time validation against `SKILL_REGISTRY`: a renamed or retired sword key crashes the load rather than silently shrinking the rule. Drift against the *doc* stays a review concern, as it is for every other catalog in this project.
- **Evaluation runs inside the practice award's transaction.** → The grant is a single attribute write on the same entity the award just wrote, so it shares the award's commit boundary. The announcement lines follow the existing discipline: staged into the caller's sink, delivered only after the caller's transaction commits.

## Open Questions

None. The table shape, the three rules' thresholds, and the balance intent are all ratified in `docs/lore/skill-trees/cross-lineage-unlock.md`.
