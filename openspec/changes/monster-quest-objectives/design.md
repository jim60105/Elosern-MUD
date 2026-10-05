## Context

Design §6 approves two hunt semantics on the existing quest runtime (`world/quests/`): regional species
hunts and strict bound clearing, plus three separate authored fields on quest records. Today
`QuestObjective` selects by `monster_tier` or `requires_bound_targets`, `world/quests/planner.py`
aggregates distinct dbrefs per EventLog, bound clearing binds dbrefs at materialization
(`scene_builder`), and `world/quests/describe.py` renders tier/quantity or "bound targets". This change
adds the species-hunt selector, the acceptance-time availability guarantee routed through the placement
owners, and the authored prose fields — without a second quest engine.

## Goals / Non-Goals

**Goals:** both hunt semantics explicit in data; transactional acceptance provisioning through existing
managers; three separate authored fields; strict binding; synthetic-fixture behavior tests.
**Non-Goals:** no shipped bestiary-named production hunts (blocked on balance approval), no AI blueprint
selector (the compile boundary can carry the new objective only when its schema owner says so —
out of scope here), no new commands, no changes to rewards, deadlines, settlement, or protected-entity
failure.

## Decisions

**D-Q1 The hunt is a new selector family on DEFEAT, not a new ObjectiveKind.** The completion mechanic
is still "count defeats"; only the selector differs. A new kind (`SPECIES_HUNT`) would fork the planner,
binding, describe, and compile paths for one field set. `QuestObjective` gains
`region_key`/`species_key`/`countable_variant_keys` which are legal only together and mutually exclusive
with `monster_tier`/`requires_bound_targets` — exactly how `item_key` already scopes to ACQUIRE.
Validation lives in `definitions.py` registration, matching the existing "validate before play" rule.

**D-Q2 Ordinary-eligibility is derived, countability is authored.** The countable set may include
stronger variants (design: general hunts MAY count eligible stronger ones), so it's an authored tuple.
The *ordinary-eligible* set used for the acceptance guarantee is derived: the ordinary variants inside
the countable set (registry `ordinary_variant` field), which is why registration requires at least one
ordinary variant among countable variants — otherwise the "guarantee ordinary targets, never force the
stronger" contract would be unrepresentable. No name parsing anywhere (design §3).

**D-Q3 Provisioning is a manager call, not a quest-side spawn.** The acceptance path (rules-owned
cross-system flow) calls the ambient/site managers' own ensure API with (region, species, ordinary
variant set, needed count); managers decide legality under capacity/ownership/site state and return the
provisioned identities or a shortfall. The quest layer never moves individuals (single-writer rule). The
whole acceptance — guarantee, provisioning result, record write, affinity (board path) — is one
`transaction.atomic()`, so shortfall rolls back everything; refusal is a named rejection reason, aligned
with the existing all-or-nothing lifecycle rule ("Quest planner failure rejects the complete action").

**D-Q4 Region scoping reads the individual's location at defeat time.** The planner resolves the
defeated individual's location → wilderness region (the provider already owns coordinate→region); a
defeat outside the region simply doesn't match, no bookkeeping needed. Individuals that existed only
transiently still resolve via the event's dbref identity read inside the same commit (they're not yet
deleted), keeping counting deterministic within the transaction.

**D-Q5 Rationale and flavor are stored on `QuestDefinition`, rendered by existing surfaces only.**
Both prose fields ride the existing payload/compile validators as bounded zh-TW strings; the OOB quest
log panel keeps its frozen schema version untouched (the detail view is a text command; panel rows keep
their `detail`/`objective_line` fields — adding rationale/flavor to the panel is a wire change nobody
requested). `docs/game/commands.md` + `command-reference.md` update in this change because `guild show`
/`guild list` output gains sections (player-visible surface).

**D-Q6 Production bestiary hunts stay unshipped.** `world/quests/catalog.py` keeps its tier-based
introductory hunt; a species hunt naming a real region/species would be content whose numbers are
unapproved. The change ships the mechanism + synthetic-fixture proof; shipping real hunts is the balance
approval change's job. This keeps the "never fake it" rule and the offline-loop contract both intact.

## Risks / Trade-offs

- Acceptance-time provisioning could let a player farm guaranteed spawns by accept/abandon; mitigated:
  provisioning only tops up to *authored capacity* — the same ceiling ambient would hold anyway — and
  abandoned/failed quests release bindings as today, so farming is bounded by capacity, not quest churn.
- The planner's region resolution adds a location read per defeat entry; bounded (one entry per kill)
  and inside the existing transaction.

## Open Issues

None; the AI blueprint schema may later adopt the hunt selector through its own change.
