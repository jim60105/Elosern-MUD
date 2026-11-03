# Regional Monster Population and Encounter Configuration

**Date:** 2026-11-03  
**Status:** Design sections approved in conversation; written-spec review required before implementation planning.  
**Scope:** The first of three approved monster-world redesigns. This document approves behavior and ownership, not an implementation or individual new species.

## 1. Approved project decomposition

The complete request covers population placement, field behavior, combat relocation, and monster content. The user approved separate design, plan, and implementation cycles, starting with this population change.

| Subproject | Deliverable |
| --- | --- |
| Regional population and encounter configuration, this document | Authored ecology zones, sparse population, solitary and group compositions, mixed species, density budgets, delayed replenishment, settlement birth exclusions, manual placement, real-entity observation, whole-cell engagement, removal of tier-example spawning and quest-driven provisioning. |
| Field movement, aggression, and escape | Game-time wandering, authored aggression, enemy escape to an adjacent cell, and successful party retreat to the preceding location. Either side may engage again; no re-engagement immunity or encounter blacklist. |
| Weak candidates and powerful bosses | Creation-guideline review and complete definitions for weak candidates, including goblin, slime, and giant-rat prototypes, and powerful boss content. Existing example names confer no approval. |

The second subproject depends on the new population ownership and identity model. New content enters placement only after its own approval and executable definitions. The first subproject uses existing approved species and does not wait for those new definitions.

### Original-request disposition

| Item | Disposition |
| --- | --- |
| 1. Solitary and multiple monsters | This design, through authored encounter compositions and count ranges. |
| 2. Sparse settlement surroundings | This design, through sparse ecology zones and automatic-birth exclusions. The user selected no simulated patrols or periodic culling. |
| 3. No births against city walls | This design, for automatic population births. Explicit manual and quest placement remains an approved exception. |
| 4. Reserve future habitats | This design. Unconfigured ground remains outside automatic generation. |
| 5. Manual bosses and strays | This design supplies explicit composition and lifecycle configuration. New powerful creature definitions belong to the content subproject. |
| 6. Wandering | Field-behavior subproject. Birth exclusions will not become movement barriers. |
| 7. Monster-initiated combat | Field-behavior subproject, using the whole-cell participation contract approved here. |
| 8. Enemy escape relocation | Field-behavior subproject. |
| 9. Player escape to the preceding location | Field-behavior subproject; retain the existing whole-party retreat authority and allow later combat. |
| 10. Undefined weak monsters | This design stops automatic use of undefined examples. Their full creative definitions belong to the content subproject and remain in the approved overall scope. |
| 11. Remove the capital introductory-hunt guarantee | This design. |
| 12. Different species can be born at the same cell | This design; selection depends on the birth occurrence rather than coordinates alone. |
| 13. Density management | This design, measured in living individuals. |
| 14. Regional populations with delayed recovery | This design; no kill-, visit-, view-, or quest-triggered refill. |
| 15. Mixed-species combat | This design, including repeated same-name individuals. Every living monster in the cell joins an ordinary field engagement. |

## 2. Existing behavior and replacement boundary

The inspected implementation contains two ambient branches in `world/maps/wilderness_population.py`:

- A capital-entry hunting band and fallback tier-example population selected from coordinates. Main specification `wilderness-monster-population` still guarantees low-tier monsters within distance three of the capital's east-gate approach.
- Species-backed `AmbientPlacementRule` rows in `world/lore/monster_placement.py`. They support multiple variants and quantities, but maintain that quantity at each covered coordinate and immediately fill vacant slots. Selection is fixed by coordinates and slot.

`MonsterSite` already owns authored nests, camps, and a boss site, with one-shot or game-time recovery. Species and variants already have registry identity and a deterministic construction owner. These ownership and construction mechanisms remain authoritative.

`world/maps/monster_provisioning.py` supplies missing ordinary hunt targets at quest acceptance. Current quest specifications also restrict published hunt quantity by one coordinate's supply. Both contracts conflict with the approved ecological population model.

`world/rules/combat_session/battlefield.py` currently builds its roster using display names and rejects duplicate participant names. `world/rules/combat_initiation.py` currently uses one target list for both encounter membership and the opening effect. A single-target opening therefore engages one monster. Both boundaries must change to support repeated same-species individuals and whole-cell combat.

This is a clean replacement of coordinate-bound ambient slots. Do not retain a tier-example fallback, a hunting-band exception, coordinate-slot observation aliases, or quest provisioning behind a compatibility switch. Do not implement wandering, aggression, escape relocation, new monster abilities, or a full ecological simulation in this subproject.

## 3. Ownership and interfaces

| Owner | Responsibility |
| --- | --- |
| `world/lore/` | Frozen, validated ecology zones, compositions, settlement birth-exclusion policy, and manual placement declarations. No mutation. |
| `world/maps/` | Population state, birth scheduling and selection, world-coordinate registration, owned cleanup, manual-site lifecycle, and read-only living-population projection. |
| `world/rules/` | Existing species-individual construction, combat identity and encounter admission, effect resolution, clock coordination, and cross-system quest acceptance. |
| `world/quests/` | Quest records, progress, and explicit target bindings under existing authority. No ambient provisioning or implicit site recovery. |
| Presentation | Read actual entities and authoritative previews. Never create prospective monsters or duplicate population rules. |

The population owner accepts an ecology-zone key and a game-time settlement interval, and returns committed birth/departure facts through existing settlement and observability conventions. Its read interface accepts cells and returns actual living entities with persistent identities, positions, public labels, and canonical threat facts. Reads create and reconcile nothing.

Manual-site reads remain side-effect-free. A quest binding does not transfer population or site ownership. General construction continues through `construct_species_individual`; placement code must not duplicate species balance values.

## 4. Ecology-zone and composition authoring

An ecology zone has a stable key, a parent geographic region, explicit bounded geometry in the existing wilderness coordinate system, and an eligible composition pool. Start with bounded rectangles intersected with the parent region and the shared map-validity rule; arbitrary procedural world coverage is outside this design. Zone geometry is authored independently of which rooms have materialized.

The declaration carries lower and upper individual-density values, a per-cell automatic-birth capacity, a recovery delay, a replenishment interval, and a maximum number of individuals born in one wave. Density values use integer individuals per one hundred eligible birth cells. Their source declarations are the balance authority; documentation and tests must not maintain a duplicate approval table.

A composition contains weighted, explicit variant references and inclusive count ranges. It may describe one solitary individual, a same-species group, or several species in one group. Every sampled composition is placed together in one cell. Group ranges must reflect approved ecology; a prose mention of flocking never becomes a runtime count by inference.

Composition weights and ranges determine births within the authored pool. An occurrence selects its position, composition, and counts anew. Coordinates alone do not permanently select a species. A later birth can select the same species again, but is not required to do so. Living individuals are never replaced merely to realize a new random selection.

Reject unknown keys, incompatible habitat references, invalid geometry, nonpositive weights or timing, invalid counts, negative densities, and impossible density or composition bounds before publishing the registry. Ordinary ecology zones must not overlap. Multiple compositions belong in one zone rather than competing owners over the same ground. Manual sites and quest placements may overlap a zone.

Initially author bounded zones for the existing regional species placements inside their approved habitats. Remove region-wide implicit coverage. There is no requirement to give every approved species an ambient zone; species may remain site-only. Unconfigured areas, including areas intended for future content, receive no automatic population. Do not reserve future habitat by inventing unresolved species references or placeholder creatures.

## 5. Settlement birth exclusions

Use the current published settlement geometry, not capital-specific coordinates. For footprint settlements, measure Chebyshev distance from the complete footprint, so its exterior adjacent ring is excluded. A point-shaped settlement uses its published anchor cell as the distance source. A configured buffer must exclude at least the immediate neighboring cells; larger maintained surroundings may have a larger authored buffer.

Only actual inhabited settlements receive this policy. Dungeon entrances and other nonsettlement anchors do not automatically become safe settlements. Resolve the settlement category from authored map identity rather than inferring it from a name.

A cell is eligible for an ordinary birth only when it is inside its ecology zone and parent region, passes `is_valid_wilderness_cell`, and lies outside every applicable settlement birth exclusion. The area used for density is this eligible birth-cell set. Broad, strongly populated zones must not be used to circumvent the settlement-surroundings safety intent immediately outside the minimum exclusion ring.

The user explicitly selected birth exclusion only. Wild creatures may later wander into settlement surroundings. This approval does not invent traversable routes into a city or bypass existing terrain and exit rules; those movement details belong to the field-behavior design.

Explicit manual and quest placement bypasses the automatic birth-exclusion and automatic density checks. It still requires a valid placement surface, approved species and variants, and the placing owner's lawful lifecycle. Ordinary population maintenance never culls these exceptions. Do not add guard patrols, simulated guard battles, or periodic population deletion.

## 6. Density and replenishment

### 6.1 Individual budgets

For an eligible birth-cell count `E`, derive the lower population bound by rounding `E * lower_density / 100` upward and the upper bound by rounding `E * upper_density / 100` downward. Require a positive usable interval for each enabled, nonempty ecology zone. Use integer arithmetic.

Count living monster individuals inside the zone, including ambient, manual, site, and quest individuals, against available ordinary birth headroom. One group of five contributes five. A separate per-cell check counts all living occupants at the candidate birth cell. An explicit placement can exceed either ordinary limit; such excess blocks further ordinary births and never authorizes removal of living entities.

The upper bound is an automatic-birth ceiling. Falling below the lower bound requests recovery. Reaching the lower bound ends that recovery episode; a final complete composition may place the population anywhere up to the upper bound. Do not require an exact population that forces group splitting or arbitrary deletion.

Authoring validation must establish that legal complete compositions can recover an otherwise unobstructed zone to its density interval. Headroom, wave budget, and cell capacity must permit a composition when below the lower bound. If a composition does not fit the remaining headroom, select among legal fitting outcomes; do not truncate it below its declared count minima.

### 6.2 Game-time recovery episodes

On the first committed deficit below the lower bound, record a recovery time no earlier than the deficit occurrence plus the zone's recovery delay. Further losses do not trigger immediate births and do not continually restart an already pending recovery episode. This is regional recovery, not a one-kill/one-replacement queue.

Once due, a wave samples complete legal compositions within the current density, per-cell, and wave limits. It creates at most the authored wave budget and schedules another wave after the positive replenishment interval if the population remains below the lower bound. A kill itself is never a spawn trigger.

Use the game-time occurrence of a combat loss, including its recorded round offset, rather than backdating it to the pre-combat clock tick. Earlier rounds must not accidentally satisfy a delay for a monster defeated in a later round. Births cannot enter an active combat cell, replace session participants, or append enemies to an already persisted encounter.

If terrain, manual occupancy, session protection, or another lawful constraint leaves no birth candidate, create nothing and retry at the next replenishment interval. Do not put creatures outside the zone, against a wall, or over capacity to satisfy a target. Recovery is eventual when lawful space is available and the player is not continuing to deplete the population.

World time advances only through existing player-driven clock mechanisms. Long advances process due waves chronologically under the same rollback boundary; splitting an equal time interval across calls must not change the result when all other events and state are equal. No wall-clock worker runs the population.

### 6.3 Persistence and initialization

Persist initialized state, the seed used by population selection, generation sequence, recovery due time, and settlement progress through the population owner. Use a stable seeded selection discipline with distinct draw purposes, not process-randomized Python hashes or global unrecorded randomness.

Initial world population is a one-time owner operation using the same placement and density constraints. It records initialization with the created individuals. Restart, source reread, room preparation, and player arrival must not repeat initial filling. Existing valid individuals retain identity, consumed resources, and state.

Each ordinary individual carries its home ecology-zone ownership separately from its current coordinate. No identity or ownership marker encodes a cell as a permanent generation slot. Wilderness registration remains authoritative when no room is materialized; activation only attaches existing individuals.

Retire unsupported ambient-example creation and its source contracts. No automatic broad save reset, online data migration, or backward-compatible slot reader is approved. Never delete or reinterpret foreign-owned entities during the cutover. Existing development data requiring repair must use the project's explicit GM repair/reset procedures rather than hidden startup mutation.

## 7. Manual placement and site lifecycle

Extend the existing manual placement mechanism to express complete compositions, including mixed variants, same-variant groups, and a solitary stray. Retain stable site ownership and explicit one-shot or game-time recovery declarations. A one-shot site remains cleared; a recovering site creates fresh identities only when its condition matures.

Ordinary deficit processing never fills, restores, or clears a manual site. A quest cannot early-recover a site. A hand-authored quest scene may explicitly create its own defined encounter under existing quest authority; that exception does not restore automatic replenishment at ordinary regional-hunt acceptance.

Manual placement can specify an approved stronger variant, but this design does not approve any new boss profile or use a name such as “boss” to invent power. The content subproject supplies the requested powerful creatures and their final authored placements.

## 8. Whole-cell engagement and stable combat identity

### 8.1 Encounter membership and effect recipients

All ordinary field engagement routes collect every living, co-located `Monster` in deterministic persistent-ID order. This includes ambient, site, and quest-owned monsters. Dead or absent entities are excluded. This is an explicit participation rule, independent of species, ownership, or a generated group marker.

Separate the encounter enemy roster from the opening action's concrete recipients. For `A + A + B`, a single-target opening against one `A` admits all three enemies but preflights and seeds the action only against the chosen `A`. Area effects retain their existing targeting and faction rules. Companions retain the same command authority, opening-order policy, costs, and draft semantics.

Candidate preview and committed admission use the same roster and recipient rules. Session creation and opening admission remain atomic. Apply the rule to text engagement, browser engagement, exploration casts, and companion-initiated casts. Preserve designated participants in guild examinations and existing explicitly staged non-field combat; do not sweep unrelated monsters into those modes.

### 8.2 Same-name participants

Use persistent individual identity for interactive battlefield membership, turn order, fled/knockout references, target selection, action bookkeeping, and session restoration. Display names must not serve as identity. Follow identity through consumers rather than changing the construction label or appending generated suffixes to monster names.

Two individuals with the same variant and label remain independently targetable and retain separate HP, resources, AI observations, effects, flee status, and quest defeat credit. Public menus and text selection may disambiguate labels using their existing concrete entity-reference mechanisms. Renaming or reordering individuals cannot redirect a selection or merge participants.

Migrate every affected combat consumer in the owning OpenSpec changes. Preserve ordinary pure-combat testing through explicit fixture identities; do not keep a production name-key fallback or a second legacy battlefield path. The identity work is a prerequisite of group delivery, not unrelated refactoring.

## 9. Quest and introductory-content cutover

Regional species hunts may be accepted while fewer living targets exist than the required quantity, including zero current targets. Validate species, variants, geographic scope, issuance, rank, and an actual lawful ecological or explicit authored supply source. Do not advertise hunts for species with no permitted source.

Remove acceptance-time ordinary-target guarantees, legal-capacity refill calls, and the requirement that a regional hunt's total quantity fit one cell's supply. A hunt may be completed across several encounters and recovery waves. Its existing deadline remains in effect; acceptance guarantees neither an immediate target supply nor completion before the deadline. UI and prose must not promise otherwise.

Keep bound clear-out semantics separate. Acceptance reads and binds the site's standing identities under existing site lifecycle rules. A cleared or unpopulated site is not generated on demand, and recovered newcomers do not substitute for an older bound set.

Remove the capital introductory hunting band and every contract that relies on weak monsters being guaranteed immediately outside its gate. Update affected introductory quest descriptions and tutorial assumptions. Ordinary quests that remain valid do not gain a replacement capital-start guarantee.

No tier example, visual-only species declaration, untranslated example name, or test fixture becomes a formal combat species. The first implementation uses current approved species. Goblin, slime, giant-rat, and powerful-boss candidates undergo their separate content cycle under [Monster Creation Guidelines](../../lore/monster-creation-guidelines.md).

## 10. Presentation, failure boundaries, and observability

`population_view`, local/area maps, sight-change observations, travel interruption, quest destinations, and GM population inspection read actual living individuals. Remove prospective coordinate-slot monsters from population facts. A scheduled future birth is not a visible entity or an immediate encounter. Threat and grade remain registry-derived.

A wave is one all-or-nothing write. If construction, registration, scheduling, or a later write fails, restore the complete wave, counters, due state, world-coordinate registry, room attachments, relevant caches, and the surrounding clock transaction. Snapshot mutable Evennia surfaces because a database rollback alone does not restore their in-process values. Retrying the same failed wave must make the same selection and leave no duplicate or half-group.

Distinguish invalid authoring, unavailable world state, and temporarily blocked birth space. Invalid authoring rejects before publication. Temporary unavailability never invokes a fake fallback species or an out-of-zone birth.

Use the existing `world.observability` facade with named imports. Committed population changes and blocked recovery decisions emit bounded events with available zone, region, individual, species, variant, cell, and tick identifiers. Commit-only callbacks must not report rolled-back births. Reads and unchanged reconciliation emit no mutation events. Do not log player-facing prose or secrets.

## 11. Specification and consumer impact

This design does not edit current main specifications. The implementation plan must use the repository OpenSpec workflow, with individually executable changes and explicit dependencies for the identity prerequisite, population owner, and consumer cutover. The existing active change `scope-test-settlement-sync` is outside this design's edit scope.

Amend or replace the relevant contracts in `wilderness-monster-population`, `monster-site-placement`, `field-combat-initiation`, `player-combat-session`, `quest-blueprint`, `quest-lifecycle`, `guild-quest-board`, and affected population-view, travel, and map capabilities. Update the approved monster data model's former acceptance-time supply guarantee through explicit design amendment when that behavior is implemented. Do not leave contradictory guarantees in authoritative documentation.

Affected implementation consumers include `world/maps/wilderness_population.py`, provider room preparation and bootstrap, manual-site settlement, `world/maps/monster_provisioning.py` callers, quest supply checks and definitions, combat reconstruction and initiation, command/browser engagement adapters, and population-based presentation. Remove obsolete helpers and tests that establish coordinate slots, example monsters, duplicate-name rejection, immediate replacement, or single-target-only encounter membership.

Update player command documentation when availability or engagement semantics change, including `docs/game/commands.md` and `docs/game/command-reference.md`. Keep test shard ownership and requirement traceability current. Obtain requirement IDs from the existing traceability tool; no fabricated IDs or empty coverage claims.

## 12. Verification requirements

Use synthetic species, variants, zones, and settlement geometry for mechanism tests. Expected results must come from independently known inputs. Production integrity checks validate references, topology, profile obligations, habitat relations, and legal placement without a duplicate species, density, or balance table.

| Boundary | Required observable evidence |
| --- | --- |
| Sparse coverage | Unconfigured ground creates nothing; configured zones retain empty cells and remain inside density and geometry bounds. |
| Settlement exclusion | Automatic births never occur in the prohibited exterior ring or buffer, including a noncapital settlement. Explicit legal placement there succeeds and survives ordinary maintenance. |
| Solitary/group composition | Authored count boundaries hold; multiple identical variants and mixed compositions construct as distinct individuals without partial groups. |
| Whole-cell combat | A real `A + A + B` encounter admits all three through text/browser-equivalent authoritative entry; a single-target opening changes only its selected recipient. |
| Identity | Same labels do not reject engagement, merge AI/effect state, redirect targets after rename, or duplicate death credit. Restoration preserves individual membership. |
| Recovery | Killing creates no immediate replacement. Re-entry, map reads, and accepting an undersupplied hunt create nothing. Before/at-due boundaries and consecutive waves establish delay, per-wave bounds, and eventual density recovery. |
| State reuse | Room recycling and reload retain the same living IDs, current resources, birth sequence, and due time. Initialization does not run again. |
| Capacity and ownership | Manual overpopulation prevents additional automatic births without deleting or modifying foreign individuals. One-shot and not-yet-due sites stay cleared. |
| Failure | Inject a failure after an actual individual and registration write; reload and live caches match the pre-wave state. A retry yields the same legal selection without a duplicate. |
| Timing | Combat loss timestamps do not borrow earlier-round time; equal clock advancement partitions preserve due-wave outcomes when external events are unchanged. |
| Quest behavior | An undersupplied legitimate regional hunt accepts without creating an individual; bound clear-outs retain identity and recovery restrictions. |
| Unknown content | Undefined tier examples never reach automatic construction; current valid construction still uses the approved registry and literal stats. |

Implementation smoke must exercise real construction, placement, map/view consumption, encounter selection, committed defeat, clock-driven recovery, and reload. Tests alone are insufficient evidence. Use the smallest relevant Evennia, command, presentation, or browser labels; register any new test modules or browser methods in their owning manifests. Run observability lint with focused tests whenever a logging path changes, plus `uv run --locked python -m tools.contract_gate` before handoff. Full managed browser and complete evidence verification remain CI-owned.

## 13. Written-spec review gate

All five design sections were approved in conversation. This written document must be committed and explicitly reviewed by the user before invoking `writing-plans`. That transition creates a plan for this first subproject only. Neither design approval nor plan creation authorizes feature implementation.
