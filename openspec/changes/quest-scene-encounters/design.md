# Design

## Context

See proposal.md for motivation and active-change conflicts. The approved source is `docs/superpowers/specs/2026-10-11-quest-scene-encounters-design.md` in full. Engine design sections 3, 7 and 11 retain deterministic ownership and deterministic-before-generative implementation order.

Observed implementation has `materialize_stage()` requiring an accepted in-progress quest, locating permanent destinations without occupants, and spawning instance occupants. `world/quests/compile/compiler.py` rejects all ESCORT objectives, permanent NPC requirements, and unauthorized runtime issuer keys. `GeneratedQuestStore` is currently one persistent Script containing issuance-keyed payloads. `resolve_issuer_key()` reads QuestIssuer and resolves either content or entity identity grammar. Reclamation deletes ordinary owned living occupants. Current dialogue uses authored tables plus guarded generative replies and durable pair history.

Main capabilities confirmed in `openspec/specs/` are scene-builder, scenario-director, quest-issuer-authorization, scripted-dialogue, npc-dialogue, webclient-dialogue-session and instance-reclamation. quest-blueprint's protected-entity publication guard remains intentionally unchanged. Persistent role, encounter lifecycle, and phase dialogue requirements get their own cohesive capabilities. No sibling proposal is required to validate or implement this change.

## Goals / Non-Goals

Build one complete deterministic package-to-encounter-to-conversation integration with retained exact actors and scoped commissions. Reuse existing prototype, characterization, trait, portrait, component configuration, narrative knowledge, quest registration and versioned presentation paths.

Exclude escort movement, protected-role production binding, reunion mechanics, shared exclusive-outcome settlement, confirmed dream dispatch, production exploration hooks and deployment decisions. Packages can represent distinct role-issued commission references and explicit shared outcome identifiers as validated planning data; execution of shared exclusive outcomes belongs to design 2. Source IDs are accepted as data without implementing design 3's authoring decision workflow. No migration or compatibility layer is added.

## Decisions

### Normalized generated persistence with database identity constraints

Extend the generated quest persistence boundary under world/quests with normalized package, role, encounter and binding records rather than an accepted-log placeholder or AI-owned state. Store immutable published normalized payloads separately from mutable binding/runtime rows. Database uniqueness covers package/source identity where supplied, package-role binding, and encounter activation identity scoped to package/scene/player. Runtime state carries pending/activated/cancelled/unavailable, activation tick and reason; role binding carries actual NPC identity and provenance; phase state carries selected phase and monotonic revision.

Use a persistent normalized root and existing generated registration restoration. The current issuance-list Script alone cannot enforce role-binding uniqueness; do not pretend a list scan supplies a database constraint. Use the repository's supported deterministic ORM persistence pattern, with schema declarations needed for new tables and constraints but no deployed-data migration or compatibility transform. Replayed source content returns its published version; differing content cannot overwrite it. Reuse existing actor only by explicit validated exact reference, never display name. Relationship declarations remain package references while knowledge is recorded through narrative owner APIs.

### Separate planning from runtime issuer settlement

The shared deterministic compiler validates package declarations and symbolic issuer roles without manufacturing a runtime issuer key. Existing direct-runtime-key compilation remains strict. Publication validates all package payloads before persisting and creates no actors or accepted records. On activation a rules-owned helper provisions only the declared component and commission scope on the exact bound actor, then resolves its actual issuer identity through the existing grammar and completes existing strict registration. Existing NPC references require explicit authority validation and cannot gain authority merely by being mentioned.

Remove permanent-occupant rejection only when package validation, exact ownership, and retention replacement contracts are implemented in both schema validation and deterministic compilation. Keep ESCORT publication rejection, quantity-one rules, unsupported failure-condition rejection, and protected-role binding guards. Generic phase conditions use supported committed facts only; reunion/escort condition names remain guarded until design 2 supplies real owning observations. Synthetic generic transitions establish this API now without implementing or claiming actual reunion mechanics.

### One shared deterministic materializer

Extract focused shared creation/initialization from the existing instance path rather than copy it. Stage requests retain accepted-current-stage checks. Encounter requests use published lifecycle eligibility, player, actual room and tick, and authoritative observations. Permanent scenes locate existing map rooms without description replacement. Materialize only required unbound roles; bound roles remain at actual locations. A departed, dead or deleted required actor yields a named unavailable outcome.

Within one transaction lock/revalidate runtime identities, validate prerequisites/locators/actors, create whitelisted actors, configure components, register exact authorized commissions, bind roles, set initial phases and write durable knowledge/events through owners. Compensate affected Evennia Attribute caches and process registration views using existing quest transition patterns on rollback. Fan-out and portrait callbacks run after commit; callbacks never own the sole activation identity. Repeat invocation reads durable identity and cannot duplicate an actor.

### Shared phase dialogue and freshness

Add a resolver alongside existing rules-owned dialogue definitions, supporting immutable authored definitions and validated generated role phases. Migrate greeting, keyword, presentation/topic, action validation and text consumers together; authored override/profile precedence remains intact. Generated hosts resolve complete current phase content. Topics retain existing menu limits, ordered identity and labels, and existing versioned capability payloads. The existing conversation panel stays version 2 and read-only; no client special case or new choice UI.

Registered deterministic phase conditions choose one complete phase; reject missing, overlapping, conflicting and automatic-cycle selections. Selection permission-filters per-role knowledge. A global quest fact cannot teach a remote actor a private event. Transition writes selected phase/revision through its deterministic owner, records permitted knowledge via narrative APIs, and refreshes live sessions through existing session helpers after commit. Preserve persona, append-only turns and previous frames.

Scripted effects name registered domain verbs and validated references. Both scripted choices and validated free-form intents use the same rules-owned authorization path with presence, phase/revision, knowledge and commission scope checks. Fixed prose has no mutation authority. Capture phase revision in free-form context freshness; compare before delivering speech, executing intent or appending turns/memory. Stale-phase rejection suppresses all three and refreshes current state, even where the older presence-only stale behavior keeps speech. Persona staleness remains independent.

### Retention precedes destructive cleanup

Role identity outlives stage release and terminal quest states. Require validated permanent retention locators for retained instance roles at publication. Maps reclamation transfers only retained actors still inside using movement hooks, removes ephemeral ownership and reclaims disposable objects in one transaction. Actors outside remain untouched. Preserve actor living state and history; never resurrect or clone. On failure restore caches and retain the room without destructive partial cleanup. Existing player/pin safety and promotion remain unchanged; party/follow and quest release cannot be bypassed, and future escort release remains guarded.

### Downstream operation contracts

These proposed operation names are the implementation interface contract, not claims that the functions already exist. Export them from the quest-owned package boundary; internal module organization may follow existing compiler conventions.

| Operation | Inputs | Successful result | Named non-success outcomes |
| --- | --- | --- | --- |
| `publish_scene_package` | Bounded canonical payload, owner identity, optional durable source/decision identity | Stable immutable package/version identity; replay returns the same publication | Invalid reference/locator/phase/effect/authority, unsupported guarded capability, conflicting source content |
| `lookup_story_role` | Package identity and exact role ID | Read-only definition and binding status, exact NPC identity if materialized, availability/provenance and scoped commission references | Unknown package/role; missing/dead/deleted/departed actor reported without repair |
| `activate_scene_encounter` | Player identity, package/scene identity, actual room, world tick and owner-authoritative prerequisite observations | Durable encounter identity/state, exact required role bindings and registered authorized commission references | Pending prerequisite, wrong locator, cancelled or unavailable actor; technical failure rolls back and leaves the same identity invocable |
| `transition_story_dialogue` | Package/role identity, exact participants, expected phase revision and committed observation provenance resolved through its owner | Selected permitted phase and next revision, unchanged baseline/history, post-commit session refresh | Stale revision, unsupported guarded observation, invalid participant/provenance or ambiguous selection |

Lookup is read-only. Publication writes definitions atomically without actor creation or quest acceptance. Activation owns its transaction and invokes rules-owned scoped issuer provisioning followed by existing strict registration; its returned commission references contain actual issuer keys and definition/issuance identities, never symbolic authority. A replay of activated state returns the original identity. Phase transitions join the owning committed observation transaction, with presentation deferred until commit. Callers cannot gain authority by supplying a fabricated observation mapping; the owner resolves provenance and current state before mutation. Designs 2 and 3 may consume these boundaries without introducing their mechanics or production callers here.

## Risks / Trade-offs

The current generated Script is deliberately smaller than normalized package persistence. New uniqueness constraints are required despite the single-player process; schema validation alone is insufficient across restart. Attribute caching and process-local registries need explicit compensation in addition to transaction rollback. Permanent-room occupancy is safe only once ownership and retention validation replace the old guard. Dialogue phase freshness must cover all consumers, particularly queued replies and reused topic IDs.

The eight-hour estimate and allocation are recorded in proposal.md. They depend on reuse of implemented subsystems and exclude production dispatch, escort mechanics, visual redesign and registry refactors. Conditions use a finite registry of supported state/knowledge predicates with explicit validation, without a general expression interpreter. Domain effects remain existing whitelisted verbs; this change adds authorization/context checks rather than new mechanics. Synthetic packages use supported non-escort quest objectives to exercise registration and conversation now. Actual reunion acceptance remains a design-2 integration criterion; this change tests its generic transition boundary without fake reunion completion or disabling guards.

## Verification and traceability plan

Use synthetic deterministic fixtures and real construction/interaction consumers. Cover both encounter orders, no accepted quest, reload and source replay uniqueness, unchanged actor state/history, exact relationships without knowledge leakage, truthful information transfer, fixed greeting/topic/free-form consumers, offline scoped commission actions, generic closure versus unresolved failure, stale choices/replies, and failures after creation/configuration/registration. Reclaim an instance and observe the same retained actor after terminal quest state. Reject ambiguous places, unauthorized existing issuers, removed actors, invalid phases and numeric/typeclass injection.

Each added requirement maps to meaningful assertion-bearing tests beside its owning package; modified requirements retain their canonical IDs with reviewed assertions. Generate IDs using tools.spec_traceability list against the equivalent post-delta spec tree rather than inventing IDs; register non-browser modules and browser methods in their exact shard manifests. No skipped downstream reunion test claims current coverage. Keep future guarded tests intact. Run focused owner tests and presentation tests, required observability/data lints, command documentation checks if text command behavior changes, mandatory contract gate and strict change validation. CI retains full evidence verification. Implementation must update relevant development docs and both command references if the command surface changes.
