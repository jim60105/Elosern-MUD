# Quest Scene Encounters and Persistent Story NPCs

Date: 2026-10-11

Status: Conversation design approved; written review pending.

## 1. Purpose and approved decisions

Extend the existing quest blueprint compiler and deterministic SceneBuilder so a
player can meet generated characters before accepting their commission. Preserve
those characters and their memories after the quest ends.

The motivating request is a dream direction about meeting a girl at the south
gate and helping her find her mother. The player may instead visit the mother's
location first and meet her looking for her daughter. Neither encounter requires
quest acceptance or a prior encounter with the other character.

Approved product decisions:

- Extend the quest scene pipeline rather than create a separate NPC generation
  engine.
- Publish validated scene and character definitions first. Materialize a
  character when a scene requiring that character activates.
- Give each encounter its own prerequisites. Do not impose a girl-first order.
- Retain materialized named characters, identities, and memories after completion,
  failure, or abandonment. Death and other committed outcomes remain real.
- Define dialogue for all reachable story phases when constructing the package.
  Successful reunion and closure lead to everyday conversation.
- Provide a fixed opening greeting and scripted topic choices in the existing
  NPC conversation window, alongside LLM free-form dialogue. The existing guard's
  topic buttons are the interaction model; no separate choice interface is added.
- LLM output is validated data. It never supplies executable code, mechanical
  numbers, typeclass paths, or mutation authority.

This is the first of three sequential designs. The second defines escort and
reunion mechanics. The third connects confirmed dream requests to published
packages and production encounter activation. This document defines the scene,
identity, and dialogue contracts those designs consume.

## 2. Current implementation and contract changes

`world/quests/scene_builder.py::materialize_stage()` requires an in-progress
accepted quest. It creates occupants only for instance destinations; permanent
anchor/grid destinations are located without spawning or binding. Its NPC
prototype is the plain `NPC` typeclass, and repeated named roles across stages
currently have no entity-reuse contract.

Scripted greetings, keyword responses, and exploration topic buttons currently
read the authored `DIALOGUE_TABLE`. Free-form dialogue requires `LLMNPC`.
`QuestIssuer` is the sole private-commission authority, currently provisioned
through authored imports. Compilation requires an existing authorized issuer.

Implementation must amend the affected current requirements in `scene-builder`,
`scenario-director`, `quest-issuer-authorization`, and the dialogue capabilities.
In particular, permanent occupant spawning and validated runtime issuer
provisioning must become explicit contracts. Never remove these guards without
implementing their replacement validation and ownership rules. Escort publication
remains guarded until the second design's protected-role flow is implemented.

The architectural source of truth remains
[the engine design](2026-07-29-ai-mud-engine-design.md). Knowledge and memory follow
[the narrative cognition design](2026-10-03-narrative-memory-cognition-design.md).

## 3. Architecture and ownership

A validated quest scene package contains quest requirements, reusable role
definitions, pre-acceptance encounters, and phase-aware dialogue definitions.
Pre-acceptance encounters are scene lifecycle records, never fabricated active
`QuestRecord` instances. Unaccepted remains represented by absence from the
player's accepted quest log.

| Owner | Responsibility |
| --- | --- |
| `world/ai/` | Propose characterizations, scenes, dialogue, and quest requirements as bounded data. |
| `world/quests/` | Validate and persist scene packages; materialize scenes through the existing builder; own scene activation and role-to-entity bindings; register commissions through existing quest APIs. |
| `world/rules/` | Apply character initialization and component configuration through deterministic helpers; authorize interactions and execute allowed dialogue effects. |
| `world/maps/` | Own rooms, instance lifecycle, and retention transfers before instance reclamation. |
| `world/narrative/` | Own events, initial knowledge and later memories, dialogue history, and eventual dream/director orchestration. |
| Presentation | Read the current greeting, topics, free-form availability, and committed scene state through existing presentation surfaces. |

Share the existing prototype, characterization, trait, portrait, and binding
construction paths. Extract focused deterministic helpers where needed; do not
copy the spawner or grow a second compiler. Authored lore registries remain
immutable sources for shipped content and balance. Generated content lives in
the persistent generated-scene store, not in mutated lore registries.

## 4. Persistent data contract

Use a normalized persistent scene-package root with immutable validated payloads
and separately mutable runtime bindings. Extend the existing generated quest
persistence boundary rather than placing this data in an AI module or in the
accepted quest log. Role/scene binding records belong to `world/quests/` and need
database-enforced uniqueness so restart cannot create duplicates.

| Record | Required meaning |
| --- | --- |
| Package | Stable package identity, immutable published version, owner, source request/decision when present, validated quest and scene payload, publication status. |
| Role definition | Package-local role ID; validated characterization and tier; named-character retention policy; first-scene references; permanent retention locator; optional explicit existing NPC reference. |
| Relationship | Typed relation between role IDs, such as parent/child, with reciprocal consistency and no inference from names. |
| Initial knowledge | Role-owned, provenance-bearing facts/claims. Relationships and world planning do not grant unlimited knowledge. |
| Encounter | Stable scene ID, validated locator, explicit prerequisites, role references, and bounded initial presentation. |
| Role binding | Stable package/role identity mapped to one actual NPC identity, with materialization provenance and current availability. |
| Encounter runtime | Pending, activated, cancelled, or unavailable state; activation identity/tick and relevant reason. |
| Dialogue definition | Role-specific phase definitions, conditions, greetings, topic choices, fixed responses, allowed domain effects, and free-form context. |
| Dialogue runtime | Selected phase and monotonic revision, separate from immutable persona and historical dialogue. |

Define a role once and reference it from multiple encounters and stages. Permit
explicit existing-NPC references only after identity, ownership, compatibility,
and authority validation. Never reuse an NPC based on its display name or fuzzy
text similarity. Future packages may explicitly reference a retained NPC.

Published payloads are immutable. Reprocessing a source returns its existing
package; revising a future plan cannot overwrite a materialized character's
identity, history, or baseline persona. Package-local role identity survives
stage progression and terminal quest states. A dialogue phase revision does not
create a new character or erase old conversation frames.

Apply existing schema size, prose, characterization, and menu bounds. Ages remain
within `0..10000` and applicable existing race bounds. Traits and rewards remain
registry-derived; the model never selects mechanical magnitudes.

## 5. Publication and materialization

### 5.1 Publication

Validate the entire proposed package before publication, including locators, role
and scene references, relationship consistency, initial knowledge, dialogue phase
coverage, issuer declarations, allowed effects, and existing mechanical constraints.
Resolve named places through existing map authorities. An unknown or ambiguous
south gate is a named validation failure; no nearest-place substitution occurs.

Split planning validation from activation-time entity authorization. A validated
symbolic issuer role is a planning reference, not an authorized runtime issuer
key. Preserve the existing strict issuer check at commission registration.

Persist the validated package without creating NPCs, accepting a quest, granting
progress, or publishing future secrets to the player. Publication makes its
encounters eligible for the production activation caller supplied by design 3.

### 5.2 Encounter activation

The activation boundary consumes player identity, package/scene identity, the
actual room and world tick, and authoritative prerequisite observations. It does
not call an LLM. Reuse existing rooms without creating a duplicate south gate or
overwriting shared room descriptions to install an encounter.

In one transaction:

1. Lock/revalidate the encounter and unique role bindings.
2. Validate current prerequisites, locator, and referenced entity availability.
3. Reuse bound actors at their actual locations or create the scene's unbound
   actors through whitelisted prototypes and the existing initialization path.
4. Configure declared components through rules-owned helpers. For an issuer,
   grant only the explicitly validated commission scope, resolve the actual
   issuer key, and complete strict registration using the bound entity.
5. Commit role bindings, encounter state, initial dialogue phase, and durable
   events/knowledge through their owning APIs.

Do not teleport a previously bound NPC back to its original encounter location
on re-entry. A departed, dead, or deleted actor cannot be recreated to repair the
story. Missing required actors produce a named unavailable outcome.

Restore affected Evennia attribute caches and in-process registration views on
rollback, following existing quest transition compensation patterns. Defer
presentation fan-out until commit. Database success must not depend on a
transient callback recording the only durable activation identity.

### 5.3 Independent encounters

The girl and mother have independent pre-acceptance scenes. Visiting either
location first may activate that scene, provided its declared prerequisites hold.
Materialize only roles required for the activated scene; a relation to an
unmaterialized role remains a valid reference to its published definition.

Mother-first interaction uses her own initial knowledge and searching context.
The girl does not acquire that conversation unless an actual information
transfer occurs. The mother's presence and searching dialogue do not require
autonomous roaming; a general roaming/agent system is outside this design.

A repeated activation returns existing state. Reconnect, restart, repeat entry,
and duplicate source processing cannot create another girl or another mother.

## 6. Dialogue phases, greetings, and topic choices

Every reachable phase must have a complete per-role dialogue definition before
publication. It includes an opening greeting, a bounded ordered set of scripted
topics with fixed responses, free-form situation/goals, and an offline response.
Topics are the existing NPC conversation-window choices. They are distinct from
LLM-generated action-option cards.

| Situation | Mother | Daughter |
| --- | --- | --- |
| Separated, no reunion | Searching context and only personally known clues. | Seeking her mother; the declared help request may be available. |
| Escort accepted, still separated | Changes only when she learns relevant information. | Acknowledges committed acceptance and the observed journey. |
| Actual reunion committed | Reunion acknowledgment. | Reunion acknowledgment. |
| Reunion closure committed | Everyday greeting and topics; remembers separation and help. | Everyday greeting and topics; remembers the escort. |
| Abandonment/failure without reunion | Context consistent with continuing separation and her knowledge. | Context consistent with the actual unresolved outcome. |
| Relevant death or other terminal loss | Living characters use outcome-appropriate content. | A dead character is not interactable or regenerated. |

These are the motivating package's required situations, not a hard-coded
mother/daughter state machine for every quest. Each package declares finite
phase IDs and transitions using registered deterministic conditions. Reject
missing, ambiguous, cyclic automatic, or conflicting phase selection. Arbitrary
expressions and generated condition code are forbidden.

Use authoritative committed state to select a phase, then permission-filter
per-role content. A remote NPC's phase cannot reveal an unlearned fact merely
because a global quest stage advanced. Reunion transitions notify the actual
participants and record their knowledge. Design 2 owns those event conditions.

Extend one shared dialogue-definition resolver to support both immutable authored
rows and validated generated phase definitions. Migrate greetings, scripted
responses, topic affordances, action validation, and text interaction consumers
to this resolver. Do not special-case the girl in the webclient or mutate
`DIALOGUE_TABLE` at runtime.

Conversable generated roles use a whitelisted `LLMNPC` construction path with
the scripted-dialogue capability needed by the existing topic interaction.
Unrelated monsters and non-conversable prototypes are not globally converted.

Opening the conversation displays the current fixed greeting without calling a
model. Choosing an informational topic returns its fixed current response
without calling a model. A choice with an effect names a registered domain verb
and validated references; execution rechecks presence, knowledge, phase, and
commission scope. A label or fixed line cannot itself award progress or items.
Use the same deterministic effect path for a validated free-form intent.

Free-form dialogue combines baseline persona, current permission-filtered phase
context, and existing memories/history. Changing a phase does not overwrite the
persona or reset memory. Source phase revision participates in context freshness;
a reply generated for an obsolete phase cannot deliver speech, apply an intent,
or append memory. Refresh the current phase instead of accepting stale output.

A phase transition refreshes the existing conversation window's greeting/topic
model and invalidates obsolete choice capabilities through the established
versioned surface/freshness contract. Never reinterpret a previously displayed
choice as a new phase's action. Preserve historical dialogue as history.

Fixed and generated dialogue must remain in character and in Traditional Chinese.
Topics and responses may not expose commands, mechanics, UI instructions, hidden
locations, or private dream-authoring content. Successful closure removes the
old commission option; reopening the window must show everyday topics.

## 7. Character retention and scene cleanup

Do not release role identity when releasing a stage binding. Completion, failure,
and abandonment retire the quest/scene interaction as appropriate, but retained
named characters remain ordinary live NPCs with their existing memories.

Permanent rooms gain only validated package-owned occupants. Package teardown
never deletes unrelated objects or resets an actor that is now retained.
Unactivated cancelled definitions can be discarded according to source lifecycle;
no NPC exists for those definitions.

An instance package must declare a validated permanent retention destination for
each retained named role. Before room reclamation, `world/maps/` transfers any
such actor still inside the reclaimed instance through existing movement hooks
and removes its ephemeral ownership. Actors already outside remain where they
are. Retention transfers and cleanup commit together; failure prevents destructive
reclamation and records a named error. Never clone the actor or resurrect it.

The transfer preserves NPC identity, persona, phase, memories, and actual living
state. Party/follow and quest bindings remain owned by their respective systems;
design 2 defines escort release, and cleanup cannot bypass those APIs.

## 8. Error handling and observability

Reject invalid references, locations, phase coverage, unsupported effects,
forged authority, and numeric/typeclass injection before writes. Activation-time
changes in prerequisites or entity availability return an explicit reason with
no partial scene. Technical activation failure keeps the scene unactivated and
safe to invoke again using the same identity; do not add a separate retry engine.

All operation logs use `world.observability` with stable English event IDs and
context containing package, scene, role, player, NPC, room, tick, and source IDs
where available. Record publication, activation, authorization settlement,
phase changes, retention transfers, and failures. Preserve the existing exception
and credential rules. Player prose belongs in bounded context or protected
transcripts, never in event identifiers.

## 9. Acceptance and verification

Use deterministic synthetic data and existing fixture conventions. Keep permanent
tests focused on consumer-visible identity, knowledge, transitions, and rollback.

1. Publish one package with independent mother and daughter encounters. Execute
   both visit orders through real construction and interaction; both preserve
   the declared relationship without requiring quest acceptance.
2. Repeat activation, leave/re-enter, and reload committed bindings. Observe one
   entity per role and unchanged persona, living state, and prior memory.
3. Use real generated-character greeting/topic/free-form consumers. The current
   topics and fixed responses appear in the existing conversation window. Model
   services disabled do not disable greetings, topics, or allowed deterministic
   commission interactions.
4. Commit reunion/closure through the deterministic event boundary supplied by
   design 2. Both actual participants switch to everyday greetings/topics and
   retain their prior memories. Abandonment without reunion never selects the
   successful everyday phase.
5. Deliver an obsolete choice and settle a reply captured before a phase change.
   Neither applies an effect or appends an obsolete exchange.
6. Prove a mother-first conversation cannot disclose unknown daughter location or
   private dream text, and later truthful information transfer can change what
   she knows.
7. Fail after creation, component configuration, and registration writes. Reload
   and observe no orphan actors, partial bindings, or stale issuer registrations.
8. Finish/abandon a quest and reclaim an instance. Retained named actors remain
   interactable at legitimate locations, with the same identities and memories.
9. Reference an ordinary unauthorized NPC, an ambiguous place, and a removed
   bound actor. Each is rejected without granting authority or spawning a repair
   actor.

For implementation handoff, run focused Python/Evennia and dialogue presentation
tests, relevant observability and data lints, command documentation tests when
text command behavior changes, and the mandatory contract gate. Register added
test modules/methods in the proper shard manifests and trace meaningful main-spec
requirements. A representative runtime smoke must exercise construction,
conversation, commission registration, and committed reload; a schema-only test
is insufficient. No live LLM is required for deterministic acceptance.

## 10. Interface to the remaining designs

Design 2 consumes stable role bindings, exact actor identity, authorized
commission references, and phase-transition APIs. It supplies authoritative
acceptance, escort, reunion, closure, failure, and release observations.

Design 3 supplies validated packages from confirmed requests, durable source
identity, encounter eligibility, and production activation on actual exploration
boundaries. It cannot autoaccept a commission or mark reunion from generated
prose. This first design does not claim that the current dream path is wired.

No autonomous NPC agent framework, arbitrary action scripting, unrelated registry
refactor, or compatibility migration is introduced.
