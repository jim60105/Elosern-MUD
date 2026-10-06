## Context

Design §4 keeps `typeclasses/monsters.py::Monster` and layers identity on it. Today `threat_tier` is a
freely assignable `AttributeProperty`, `apply_monster_tier()` reads
`world.rules.traits.initial_trait_config_for_monster_tier` (tier band at a position; low/mid zero out
MP/SP/`magic_power`), the step-7 defeat entry in `world/rules/action/event_log.py` carries
`target_id` + tier, and `world/quests/planner.py` counts distinct dbrefs within one EventLog only —
identical events presented in two batches can double-count. Sibling changes (site placement, quest
objectives) will be the first callers that pass species identity, so this change owns construction,
resolution, and counting identity.

## Goals / Non-Goals

**Goals:** validated construction; variant-resolved tier/danger; honest interim numerics; duplicate-safe
counting. **Non-Goals:** no spawning or placement policy (`monster-site-placement`), no quest selector
semantics (`monster-quest-objectives`), no portrait change, no balance numbers, no skills.

## Decisions

**D-I1 Construction lives in `world/rules/`, not `world/lore/`.** Lore stays read-only (single-writer
rule); the constructor validates against the registries and applies traits, which is mutation, so it
sits in the rules package beside the existing trait machinery, and every spawn path (placement, quest
provisioning) calls it. `Monster` itself gains only fields plus guarded accessors.

**D-I2 Tier/danger are derived reads for species-backed individuals.** Rather than duplicating the
variant's tier into a writable `threat_tier`, the existing `threat_tier` attribute becomes read-through
for species-backed individuals: reads resolve from the variant record; a write that contradicts the
variant raises. Tier-only individuals keep the plain attribute. This keeps the ~66 existing
`threat_tier` consumers (presenter, art view, event log, planner, population) untouched while making the
new invariant "no contradictable truth" real for identity-bearing individuals. Storing a copy would
recreate exactly the drift the design forbids; an abstract read-only attribute would break tier-only
callers.

**D-I3 Interim numerics = the declared tier band, explicitly recorded.** Balance approval (external
prerequisite) has not landed, so `combat_profile=None`. The only approved numeric source today is
`MONSTER_TIER_REGISTRY` band construction at the variant's declared tier — the same engine tier-only
monsters use, so species individuals are no stronger than what the world already ships. The boundary
event names `numeric_source` (`approved_profile` or `interim_tier_band`) so any consumer or auditor can
see which rule built an individual. When approval lands, the profile path replaces the interim path with
no caller change. Inventing per-species numbers is forbidden by both the design and the bestiary's
approval scope.

**D-I4 No player scaling exists structurally.** The constructor signature accepts no player, level, or
clock input at all — scaling is unrepresentable rather than "checked to be absent", which keeps a future
temptation from silently threading a player through.

**D-I5 Dedupe lives in the quest record, keyed on dbref.** The planner already counts distinct dbrefs
per EventLog; the gap is across presentations. The record gains a small
`counted_defeat_ids`-style set per current objective (cleared on stage transition like the existing
bindings), so a redelivered event is idempotent by identity. Dbref is the persistent individual identity
the design names; display names and tiers are explicitly excluded, and the species/variant fields added
to the entry feed *selector matching* (objectives change), not dedupe.

**D-I6 Additive event fields only.** `target_defeated` keeps `target_id` and tier; species/variant keys
are added when present, so every existing consumer (XP, beats wire, HUD gestures) is byte-compatible and
no wire vocabulary changes — the `webclient-combat-beats` kind vocabulary is untouched.

## Risks / Trade-offs

- Read-through tier for species individuals touches `Monster` semantics; mitigated by the tier-only
  path being untouched and by focused typeclass tests covering both shapes in one suite.
- The interim tier-band rule could be mistaken for permanent balance truth; mitigated by the recorded
  `numeric_source`, the spec wording, and the tasks requiring the interim path to be deleted-by-replacement
  (not branched forever) when approved profiles land.
- Per-record counted-id sets grow with objective quantity only (bounded by the quantity cap), not world
  size.

## Open Issues

None; the balance-approval change replaces D-I3's interim source and is tracked as an external
prerequisite in the proposal.

## Implementation Dispositions

Two review rounds ran against this change — one on the plan, one on the finished
diff. Every finding either changed the implementation or is recorded here as an
explicit disposition; none was left implicit:

- **Both registry references are validated.** `resolve_variant` checks the
  species registry *and* the variant registry before the cross-species check: the
  synthetic kit patches the two registries independently, so variant-registry
  membership plus the owner check alone would accept a species key that resolves
  nowhere.
- **Derived truth stores nothing (D-I2 taken literally).** `threat_tier` is
  `autocreate=False` and stores no copy for a species-backed individual: reads
  resolve from the variant on every read, and *any* assignment is rejected rather
  than only a contradicting one, because a stored copy is exactly the drift the
  decision forbids once the registry changes. The construction entry point
  therefore assigns identity only. The rejected write raises
  `MonsterTierConflictError`; every construction failure raises
  `MonsterConstructionError`, so one named family covers the whole entry point.
  `autocreate=False` is what makes the no-copy rule structural — with Evennia's
  default autocreation the object-creation path would store a `None` tier that
  survives into species-backed state — and it is the one deliberate, documented
  delta on the tier-only path (a never-assigned tier-only individual carries no
  stored attribute; its tier still resolves to `None`).
- **The boundary event fires on durable commit** (`transaction.on_commit`, the
  existing rules-boundary contract), so a construction rolled back with its
  caller leaves no log fiction. It is emitted for both numeric sources with
  `numeric_source` naming the rule used.
- **`location` is not a construction parameter.** Placement stays with the
  placement change; the entry point takes identity, an optional display label
  (identity is never inferred from it), and the band position.
- **`apply_monster_tier` refuses a species-backed individual**, so the tier path
  can never silently overwrite an approved profile.
- **Identity writes are guarded, not conventional.** `species_key`/`variant_key`
  are validated on write (one registered pair, written variant-first), so a
  half-assigned or mismatched identity cannot be entered through the class API at
  all — the validated entry point is the only writer that produces a complete
  identity.
- **Derived reads never raise.** A variant record retired from the registry
  degrades the tier and danger-grade reads to the same optional absence a
  tier-only individual has, instead of raising out of a read that rendering,
  examination, and combat depend on (the tier is read as optional at ~66 sites).
- **The create/assign/apply sequence is one atomic block of its own.** A failure
  anywhere in it — including inside Evennia's creation hooks — leaves no row
  behind and surfaces as the named construction error, rather than relying on the
  caller's transaction for the no-half-built-individual guarantee.
