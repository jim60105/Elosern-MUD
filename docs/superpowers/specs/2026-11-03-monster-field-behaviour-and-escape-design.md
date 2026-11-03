# Monster Field Behaviour, Aggression, and Escape

**Date:** 2026-11-03  
**Status:** All four design sections approved in conversation; written-spec review remains a separate gate.  
**Scope:** The second of three approved monster-world redesigns. This document approves a design, not feature implementation.

## 1. Relationship to the three-specification project

The first specification, [Regional Monster Population and Encounter Configuration](2026-11-03-regional-monster-population-design.md), owns birth locations, compositions, density, delayed recovery, manual placement, stable combat identity, and whole-cell encounter membership. This specification owns movement after birth, monster-initiated engagement, and actual escape relocation. The third specification will approve weak candidate species and powerful boss content under the monster-creation guidelines.

The user requested completing the next specification rather than entering implementation planning after the first. Do not invoke an implementation skill, create implementation changes, or implement either design merely because these design sections have been approved.

### Confirmed decisions

| Topic | Approved rule |
| --- | --- |
| Activity extent | Explicit activity bounds, separate from birth geometry; no unlimited continent-wide random walk. |
| Group movement | Authored cohesive groups move together; solitary individuals move alone. A successful individual escape may leave its group. |
| Simulation | Global due events driven by game time, including unobserved areas; no wall-clock simulation or player-proximity freeze. |
| Settlement surroundings | Birth exclusions do not block movement. Existing terrain, gate, and access rules still apply. |
| Aggression | Evaluate immediately on either side's arrival and when time makes an authored condition true. No warning grace stage. |
| Encounter membership | Every living monster in the cell joins an ordinary field encounter; action recipients remain separately resolved. |
| Party destination | Prefer the preceding reachable location; otherwise choose an affordable legal adjacent destination. No destination is chosen for being monster-free. |
| Retreat duration | One existing combat round for the attempt, plus the normal successful movement duration. |
| Insufficient mental reserve | Retreat fails when no legal destination can be completed using the reserve available after the attempt round. No partial movement. |
| Re-engagement | Allowed for either side. No grace period, last-opponent blacklist, artificial safe destination, or immunity flag. |

## 2. Current integration boundaries

`WorldClock.advance` and `advance_bounded` already provide player-driven time, durable settlement, registered event sources, and snapshot compensation. `register_event_source` accepts a pure upcoming-boundary query, allowing interruptible waits to stop at an interactive event. `world/rules/mental_time.py` combines these boundaries with fatigue and sleep boundaries.

`typeclasses/exits.py` and `world/rules/movement_settlement.py` already wrap movement, physical travel pricing, party following, discovery, and publication in an atomic settlement. `charge_movement` advances time for a player-driven traversal, never for a monster or other NPC moving independently.

`world/rules/travel_cost.py` already computes distance- and terrain-dependent durations with integrated fatigue, rejects depletion strictly before arrival, and permits exact depletion at arrival. Its route-search-only fallback weight never authorizes a traversal. Reuse those execution semantics rather than adding a second escape calculator.

The current individual disengage effect in `world/rules/disengage.py` only marks the actor fled. Interactive party retreat in `world/rules/combat_session/rounds.py` likewise marks the present party fled without relocation. The new design must amend those location-preserving contracts. Retain their agility contests, existing eligibility predicates, confirmation authority, failure-round behavior, and designated examination outcomes unless this document explicitly changes the boundary.

## 3. Ownership and data contracts

| Owner | Responsibility |
| --- | --- |
| `world/lore/` | Immutable, validated activity and aggression declarations and explicit references from placement or variant configuration. No inferred executable behaviour from prose. |
| `world/maps/` | Persistent activity groups, monster positions, monster journeys, due activity transitions, home-population accounting, and room attachment when necessary. |
| `world/rules/` | Shared movement legality and pricing, physiology writes, player arrival history, retreat authority and contests, hostile combat admission, action resolution, and clock coordination. |
| `world/quests/` | Existing quest records and target identity. Movement does not rewrite a quest binding or declare a living target defeated. |
| Presentation | Actual positions, journeys, movement notices, and authoritative encounter state. No browser timer owns world evolution or encounter admission. |

Activity configuration is separate from the existing combat behaviour profile. Field aggression does not grant skills, resource pools, movement waivers, or new combat effects. Use explicit complete bindings; do not infer aggression, flight, or group counts from a species name or narrative.

An activity declaration identifies stationary, solitary-roaming, or cohesive-group policy; a bounded activity area; positive decision timing; and aggression conditions. Its geometry may be an explicit region intersection or a bounded distance around the declared home. Supported declarations must resolve to deterministic legal-cell predicates before publication. Unknown references, impossible bounds, malformed timing, and incompatible group policies reject at load.

A persistent group identifies its actual member IDs, home population or site owner, activity binding, current idle position or journey, next decision time, and deterministic decision sequence. A monster journey records stable source and destination locators, departure and arrival ticks, member IDs, and its committed traversal pricing/physiology plan. Location and state remain independent of materialized room IDs.

Use the first design's persistent individual identity throughout. Group membership controls movement only; it does not narrow whole-cell combat participation. A mixed-species composition may have one cohesive movement binding only when every member can lawfully complete its selected route.

## 4. Activity extent, cohesion, and finite populations

### 4.1 Ordinary activity

Each due idle group chooses to stay or begin one legal adjacent traversal using its saved selection seed and sequence. Its positive decision interval prevents zero-time movement loops. Staying is a valid scheduled outcome; repeated reads or reconnects never redraw it.

Ordinary wandering remains inside the group's authored activity area and follows the shared movement topology, including map bounds, impassable terrain, diagonal corner restrictions, lawful gates, and actual movement capabilities. Settlement birth exclusions are not topology and are never consulted as movement barriers. Being allowed into settlement surroundings does not invent an entrance through a city wall or authorize a locked gate.

A cohesive group selects one route and departs and arrives as one atomic unit. Use the same physical-duration rules and the slowest actual self-moving member; do not average speeds. If any required member cannot traverse or afford the complete route, the group stays and schedules another decision. Do not move a subset or detach members merely to make a wandering step succeed.

Stationary manual sites and quest encounters remain stationary unless their declaration explicitly enables movement. Activity cannot restore a cleared site, replace its bound identities, or silently move an examination opponent out of its designated encounter.

### 4.2 Escape outside ordinary bounds

Successful individual escape may choose a legal adjacent route outside the actor's ordinary activity bounds. It is still subject to physical topology, access, affordability, and active-battle protection. Escape must not fail solely because the nearest lawful refuge lies just beyond a home-range boundary.

A fleeing group member detaches without moving its former companions. After arrival outside its ordinary activity area, it prefers a legal adjacent step back into that area on its next ordinary activity opportunity. If none is possible, it waits and retries; do not teleport it home, delete it, or create a replacement. No unlimited new exploration policy is implied by this exception.

### 4.3 Population accounting amendment

A living ordinary individual retains its home-zone ownership while outside that zone, detached from a group, or in transit. Maintain two separate constraints for automatic births:

- Physical population inside a zone determines local density headroom, including foreign-owned and explicitly placed individuals there.
- The total living population owned by the zone, wherever its members are, cannot exceed that zone's ordinary upper population bound through automatic births.

A birth must fit both constraints, its wave limit, and the destination cell's limit. An emigrant never frees its home-owned slot merely by leaving. A visitor counts toward local headroom without changing home ownership. Do not double-count the same individual within either measure.

If the home-owned ceiling is reached while most members are elsewhere, an empty-looking birth zone does not request unlimited replacements. Its recovery waits for lawful headroom or returning population. A movement or journey state is not a kill or clear-out credit. This clause explicitly supplements the first specification's local-density budget.

## 5. Game-time journeys and scheduling

### 5.1 Departure, passage, and arrival

A monster's departure removes it from the source cell's present population and creates one durable journey. It is not yet a present occupant of its destination. On arrival, the same IDs attach to that destination's coordinate registry and to an existing room if one is active. No unobserved destination requires a room to be created.

Elapsed passage settles the committed travel plan through the existing physiology writer. Charge only elapsed time, exactly once; restarting, revisiting, and splitting clock advances must not charge the same interval again. A creature that lawfully has no optional physiology follows the existing no-physiology travel contract. Missing halves or malformed physiology fail closed; never substitute SP for mental reserve, fabricate a reserve, or treat corrupt state as an exemption.

A monster or NPC journey never advances the world clock by itself. A fled monster begins passage at the logical time of its resolved action, including the battle's round offset. Arrival becomes due after its priced route duration. If the battle continues, the journey can progress during the player's committed combat time without returning the monster to the old roster.

### 5.2 Event ordering and protection

Integrate birth, departure, arrival, and aggression facts through the existing clock and owned event-source mechanism. Do not introduce a second scheduler with its own time authority. Process due transitions chronologically, including events created by an earlier transition in the same advance.

At the same tick, apply lawful completed arrivals and committed births before contact evaluation, then admit eligible encounters before idle wandering departures. Resolve otherwise equal facts in stable owner/group/individual order. A contact cannot be avoided merely because an idle departure happened to be iterated first.

Active combat participants do not wander. Other groups cannot begin a route into a cell occupied by an active encounter; arrivals revalidate protection rather than adding reinforcements. An arrival blocked by a newly active encounter waits in its journey without becoming present in that cell, then revalidates at a later positive activity interval. It remains alive and home-owned throughout the wait.

Deferred combat-time settlement must carry the relevant historical encounter-protection intervals and each flee/departure occurrence time. Closing the session before clock catch-up must not permit creatures to wander retroactively into its battlefield during earlier combat rounds. A legitimate escaped individual's own protection ends at its departure time.

### 5.3 Interactive boundaries

The upcoming-boundary query is read-only and shares the same deterministic transition planning rules as settlement. It does not consume selection state, instantiate monsters, move groups, or create sessions. Forecasts must include contacts caused by intermediate departures, arrivals, and scheduled births, not only creatures already standing next to the player.

Interruptible wait, rest, and sleep stop at the first contact requiring combat. Apply physiology and recovery only through that accepted tick. Far-away maintenance remains internal and does not repeatedly return control to the player as though every distant movement were an encounter.

Normal player movement and successful retreat complete their already committed physical edge as an indivisible traversal. Mark the party as traversing for field-contact purposes; relocating a pooled room early inside the implementation must not expose the party at the destination before its arrival time or leave it attackable at both endpoints. Finish that edge's costs, then evaluate contact at arrival before another exploration action or route step.

## 6. Monster-initiated encounters

Aggression uses explicit conditions such as passive, hostile on contact, or hostile inside an authored defended area. It is not universal for the `Monster` type, does not scale with player progress, and does not infer a new ability from ecology prose.

Evaluate at player or monster arrival, at a relevant authored time/territory boundary, and before a new time-consuming exploration action if a lawful contact is already present. A newly born aggressive monster in the player's cell also creates a contact. Presentation reads never start combat.

When a condition holds, admit one ordinary hostile session through deterministic combat authority. Collect all living monsters in the cell in stable individual order, including passive, ambient, site, and quest individuals, as approved in the first specification. Preserve separate action recipients, player-party command authority, companion control, initiative, and action/resource rules.

Aggression starts normal combat; it grants neither a free damage effect nor a free extra opening turn. With an awake actionable party member, normal draft and round submission follows. Do not auto-play that member's choices.

Designated guild examinations and explicitly staged non-field encounters retain their specified opponent set and outcome rules. Their admission is not an ordinary hostile field contact.

### Sleep and lack of actionable allies

A hostile interruption ends voluntary sleep through the existing sleep owner and receipt transition, retaining the actual recovered reserve. It does not refill reserve or silently retain a completed sleep continuation.

Forced sleep keeps its wake threshold and receipt. Do not wake a forced sleeper merely to satisfy encounter admission. Awake companions can act under existing control rules. If nobody in the party can act but the ordinary combat outcome is not terminal, execute enemy-only rounds through the normal resolver and clock/physiology path until a party member can act or the battle ends. Sleep alone is not an automatic defeat or a protection from hostile actions.

This hostile-admission authority is distinct from a sleeping player's attempt to initiate voluntary combat. It must not weaken existing voluntary-action or movement sleep gates.

## 7. Player retreat destination and confirmation

### 7.1 Persistent previous-edge history

On a successful player-driven traversal, persist its stable source and destination locators under the player-control/movement owner. Wilderness locators include map identity and coordinates; persistent authored-room locators use durable room identity. Never persist a pooled wilderness room as the meaning of the previous cell.

The history is one actual completed edge, not an arbitrary earlier visited position. Require its destination to match the party's current logical location and its reverse route to remain physically legal. A failed movement or rolled-back settlement changes no history. A teleport or other nontraversal relocation invalidates that edge rather than retaining a cross-world retreat route. Apply the same rule to the active player-driven body and its present party under possession.

Capture the validated retreat edge with the confirmation's session/revision scope and revalidate it at execution. If invalid or unaffordable, select another legal adjacent route. Candidate evaluation must respect shared topology, locked access, movement restrictions, and the projected affordability after the attempt round. Never use a routing-only fallback price to admit escape.

A candidate is not required to be empty, peaceful, inside a birth zone, or outside a settlement birth exclusion. Do not prefer safety or blacklist the previous opponent. If several fallback routes qualify, choose reproducibly from stable candidates using the owning operation's deterministic selection state.

### 7.2 Party and carried members

Retreat remains one confirmed whole-party action. Every present member of the commander's team departs on success, including knocked-out companions covered by the existing carry-out rule. Remote companions do not influence route cost or move.

Actual self-moving members determine route speed and must afford the full route. Carried knocked-out members do not become fictitious walking travellers or need to be awake to be carried. Preserve their ordinary persistent condition and applicable physiology. This specification does not introduce a new encumbrance, carrying-capacity, or inventory-weight subsystem, nor authorize bypassing unrelated restraints.

## 8. Retreat energy, duration, and outcomes

### 8.1 Exact affordability

The user's additional requirement is mandatory. Retreat fails if mental reserve is insufficient to reach any legal adjacent destination. This is a combat-attempt failure, not a free preflight rejection or an attempt that partially relocates the party.

Before resolving success, use a read-only projection of the retreat attempt's one combat round, then apply the canonical execution travel planner to that projected state. Include fatigue-stage speed changes throughout the route. Do not spend or count the pre-round reserve twice, approximate from displayed percentages, or replace mental reserve with MP/SP.

Prefer the previous edge when legal and affordable. If it is unaffordable, try other lawful adjacent candidates. If no candidate can be completed, take the existing failed-retreat branch. A state whose reserve reaches exactly zero on arrival is affordable under the existing rule; apply forced-depletion posture and any resulting arrival encounter at the destination. Depletion strictly before arrival is not affordable.

Retain current movement-cost waivers only when the normal execution travel rules actually authorize them. Do not create a flee-specific speed boost, free-flight flag, or resource waiver. Malformed state is a named refusal/error, not proof of an ordinary failed agility roll or infinite energy.

### 8.2 Failed and successful attempts

If a legal affordable route exists, retain the current agility contest against the fastest eligible pursuer, using the slowest eligible allied actor. No pursuer still removes the dice contest, but does not make an impossible or unaffordable route succeed. No actionable ally retains the existing no-acting-ally terminal policy for a requested retreat.

An ordinary failure consumes one existing combat round and executes the existing enemy-only failure actions. The party stays entirely at its original logical position. Add no traversal time or movement-reserve charge. Do not roll and report success before discovering that the route cannot be paid.

A success consumes one attempt round, marks the complete departing party out of the old encounter, and completes the selected normal traversal. Charge the attempt round once and the normal movement plan once, including its distance, terrain, fatigue, and authorized waivers. Do not combine the new traversal charge with an unchanged second copy of the old terminal clock charge.

The old encounter's exit, confirmation receipt, movement, party following/carry-out, clock settlement, and final arrival history share one atomic durable operation. The party may not be marked fled with a committed source position, or moved with a still-active old session. Old combat participants are excluded from that encounter's regeneration exactly as under existing retreat; successful departure does not grant free healing or revival.

Guild-exam retreat still records examination failure. Use a lawful actual retreat edge from the examination location; never invent a wilderness position. Preserve existing examination opponent cleanup and receipt authority.

## 9. Individual monster escape

Retain resolver-driven innate flee and its current agility contest. World-mapped individual escape also requires a legal affordable adjacent route evaluated at the movement start after its action's round-time contribution. A successful agility roll alone cannot manufacture a destination or energy.

A failed individual attempt leaves position, activity membership, and fled state unchanged, apart from the normal costs and time of the attempted combat action. On success, the effect commits its fled state, detachment, source departure, and one priced journey together. It does not move the remaining enemies or end their battle prematurely.

The attempt occupies the actor's existing combat action and round; it does not add another global round for each fleeing enemy. Its journey duration is priced normally, but elapses through subsequent player-driven time rather than recursively calling `WorldClock.advance` from a monster action.

Standalone non-world combat calculations retain an explicit abstract battlefield context; they must not invent map routes or expose an abstract flee as a completed world relocation. Production mapped combat requires the world escape context. Migrate its consumers and contract tests without a silent location-preserving fallback.

## 10. Re-engagement and presentation

No successful escape creates invulnerability, an aggression cooldown, a last-encounter ban, or immunity to the previous participants. Natural physical separation during traversal is not a grace timer. On legal co-location after arrival, every applicable contact rule is available again immediately.

The player may follow a fled monster and fight it again after reaching its actual location. An escaped monster may later return through lawful activity and fight again. A player retreat may arrive among different monsters, or among earlier opponents that lawfully reached the destination first. The new encounter uses current actual occupants and preserved individual resources.

During transit, neither endpoint lists the traveller as present. Map/view/travel logs report actual departure and arrival, not a future-position monster. A journey remains visible to authorized GM inspection as a journey; it never becomes a fake local target or a new spawn. Revalidate stale browser/text targets against actual presence.

Publish the final committed arrival and resulting exploration/combat mode as one coherent update. Do not briefly expose an actionable exploration frame between an aggressive arrival and its new session. Any automatic travel continuation stops before another edge when an encounter is admitted.

## 11. Atomicity, replay, and observability

Every group departure/arrival and every escape operation commits location, coordinate registration, group membership, journey progress, home ownership, resources, clock state, session state, and operation receipts together. Cache compensation must cover Evennia's mutable attribute and room/contents surfaces as well as database state.

On an unexpected construction, relocation, physiology, encounter-admission, or later settlement failure, restore the complete owning operation and re-raise with its operational event. Do not report a successful escape while logging that relocation failed. A temporarily blocked scheduled arrival waits under its explicit journey state; it is not reported as arrived and is not converted into a new individual.

Replaying a committed operation does not move, charge, detach, or create a second session. Retrying a rolled-back operation uses the same deterministic selection state and legal candidates. Reads, reconnects, and reloads cannot advance the activity sequence or replace a stored journey.

Use named imports from `world.observability`. Emit committed boundary events for movement departure/arrival, aggression admission, and escape outcome, with available zone/site, group, individual, source/destination, session, and tick identifiers. Rollback must discard success events. Preserve the existing exception and credential-handling rules; do not introduce a parallel logging facade.

## 12. Specification changes and verification

Implementation must use the repository OpenSpec workflow, explicitly depending on the first specification's individual identity, population ownership, and whole-cell admission changes. Update the old no-relocation disengage/party-retreat contracts, affected clock/skip/sleep and movement contracts, monster activity and journey contracts, travel interruption, quest target observation, and browser/text encounter surfaces. This document does not modify main specifications itself.

Update command documentation when movement, retreat availability, or encounter context changes. Preserve exact test-shard ownership and use canonical requirement IDs from the existing traceability tool. New tests must establish observable boundaries, not source strings, aliases, forwarded copies, or a duplicate production balance table.

| Scenario | Required evidence |
| --- | --- |
| Global activity | An unobserved actual group changes logical position without creating wilderness rooms; restart does not redraw its route. |
| Cohesion and topology | A mixed group departs/arrives together; one member's blocked or unaffordable edge prevents the entire ordinary step. Corner restrictions and locked gateways are honored. |
| Bounds and escape | Ordinary wandering stays inside its activity area; a lawful escape may cross the boundary and later use an actual return edge. Settlement birth exclusions do not block movement. |
| Finite home ownership | Repeated departures and in-transit individuals retain home-owned headroom; empty birth cells cannot create unlimited additional population. Visitors block local births without changing their owner. |
| Passage | The same IDs disappear from the source, remain absent at the destination before arrival, then arrive once. Elapsed reserve is charged once across restart and partitioned advances. |
| Aggression | Both player arrival and monster arrival create one correctly scoped normal encounter, preserving repeated names, single-target effect boundaries, and initiative. Passive contacts do not initiate it. |
| Waiting and sleep | A long wait/sleep stops at an intermediate hostile contact, retaining only actual recovery. Voluntary interruption completes its receipt; forced sleep is not bypassed and enemy-only rounds use real resolution. |
| Deferred combat time | No outside group retroactively enters an earlier active battlefield during terminal clock catch-up. A monster's own flight begins at its real round offset. |
| Previous location | Pooled-room recycling, possession, gate crossings, failed movement, teleport, and reload cannot redirect retreat to an unrelated earlier location. |
| Reserve boundaries | Insufficient post-attempt reserve fails without relocation; a sufficient alternative neighbor can replace an unaffordable previous edge; exact arrival depletion succeeds and applies its real posture. |
| Failed retreat | One failure round and normal enemy actions occur, with no traversal time, movement payment, or partial party movement. |
| Successful retreat | One attempt round plus the exact normal traversal cost is committed once; knocked-out companions arrive with the party, without healing or receiving an invented walking state. |
| Individual flee | A real monster departs its old battle and later arrives at a legal neighbor with preserved identity/resources; remaining enemies continue their original encounter. |
| Re-engagement | The player reaches a fled monster and can initiate again; an aggressive arrival after party retreat can immediately create a new encounter with no immunity bypass needed. |
| Failure and replay | Inject failure after actual departure, physiology, or session writes; reload and live caches restore the source state. Retry/replay creates no duplicate journey, payment, group split, or session. |
| Equal elapsed time | With the same external events, one interval and several equivalent intervals produce the same activity, arrival, population, and resource state. |

Implementation smoke must exercise actual group movement, a live monster's arrival-triggered encounter, an interrupted wait, failed energy admission, a successful paid party retreat, a real enemy flee journey, and subsequent re-engagement, followed by committed reload. Use synthetic fixtures and existing real owners without live LLM or network services. Run the smallest relevant tests and actual consumer paths, observability lint alongside changed logging tests, and `uv run --locked python -m tools.contract_gate` before handoff. Full managed browser and complete traceability evidence remain CI-owned.

## 13. Review and continuation

This written specification and the first specification's home-population amendment must be committed and explicitly reviewed. The user selected the next design document rather than implementation planning; the remaining third content specification stays in scope. No feature implementation is authorized by this document. Resume `writing-plans` only when the user requests the planning transition after the required written-spec review.
