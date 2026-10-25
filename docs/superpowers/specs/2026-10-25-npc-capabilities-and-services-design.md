# NPC Capabilities and Service Presentation Design

**Date:** 2026-10-25
**Status:** Approved. Decomposed into ten OpenSpec changes documented in section 11.
**Scope:** Remove NPC profession blueprints and NPC titles; declare capabilities directly; expose contextual services through a consistent interaction menu. Player titles and progression remain unchanged.

## 1. Context and Goals

Elosern is a single-player, browser-first text RPG with an AVG-style exploration stage, keyboard and pointer controls, and a deterministic core that remains playable offline. The service menu supports deliberate exploration tasks rather than time-critical combat decisions.

The existing profession registry is an assembly-time indirection over capability components. NPCs declare one profession but can possess multiple capabilities. Profession blueprints also carry binding, schedule, and tier defaults. Runtime service gates already inspect component instances rather than the profession registry.

Several unrelated concepts currently share profession-like language. The guild counter's `GuildExaminer` component accepts examination requests, while a separate qualification table selects persistent adventurers as actual examiners. Adventurer records also write an unused profession label. NPC titles provide another independent identity field; the GM portal's profession summary is itself derived from component labels.

The approved design removes these redundant representations. Authored capabilities describe functionality; service binding describes where functionality is available; existing names, descriptions, and persona content describe the person.

Success means an author can inspect a single NPC declaration to determine its capabilities, and a player can select an NPC to discover and open its services without learning internal component terminology.

## 2. Decisions and Alternatives

### 2.1 Direct capability declarations

Adopt direct, explicit capability declarations. Reject replacement capability bundles, which would retain expansion, overlap, and override semantics. Reject inferring capabilities from place types, which would couple locations to functionality and complicate traveling service providers.

An NPC can have zero or more capability types, with at most one instance of each type under the existing component slot model. Capabilities carry their own required configuration. There is no primary profession, secondary profession, replacement profession label, or automatic profession inference.

### 2.2 One interaction card with groups

Adopt one existing person-focus interaction card, with common interactions first, conditional interactions next, and services last. Reject a separate service tab because it adds navigation and hides one category while the other is visible. Reject service badges as the primary interface because they do not provide availability reasons or complete actionable labels.

Do not add a new persistent HUD panel, global service window, or intermediate service-selection modal.

## 3. Ownership and Responsibilities

| Unit | Responsibility | Dependencies |
|---|---|---|
| Authored capability declarations | Specify capability types, configuration, and applicable binding | Existing component vocabulary and domain registries |
| Capability validation and assembly | Validate complete input and install the declared component configuration | Deterministic core and Evennia components |
| Service projection | Derive contextual service entries and reasons | Capability instances, existing domain rules, actor and viewer context |
| NPC service-list UI | Render entries and emit selections | Server-produced descriptors and existing interaction-card controls |
| Existing service flows | Validate and execute trading, registration, examinations, and other domain operations | Existing deterministic owners |

No new module under `world/ai/` may apply state changes. Persistent component configuration remains owned by the deterministic core. The UI never grants permission or calculates service eligibility independently.

The service projection is derived data, not another persisted list or independently maintained NPC registry. Static presentation metadata may associate a supported capability or explicit dialogue-service entry with its player-facing label and route. It must not duplicate per-NPC capability declarations.

## 4. Authored Data and Assembly

### 4.1 Capability configuration

Remove `profession` from imported NPC records, place-host declarations, service-host rows, and persistent-adventurer definitions. Remove the profession rulebook, parser, expansion rules, and blueprint override machinery.

Every configured capability supplies its own required identifiers and fields. The importer and service-host construction path share capability validation and assembly rather than maintaining blueprint and explicit-component variants.

Each service-bearing capability explicitly declares `person` or `place` binding. A place-bound capability must resolve exactly one valid anchor room. A person-bound capability must not carry an anchor. Different capabilities on one NPC may use different bindings.

This requirement applies to bound service capabilities. It must not turn an ordinary narrative dialogue component into a service or force unrelated scene dialogue to acquire service settings.

Schedules and literal trait initialization remain explicit inputs to their existing owners. Remove profession-provided schedule and tier defaults without removing the schedule or tier systems themselves.

### 4.2 Validation and atomicity

Validate the complete authored batch before persistence. Reject unknown or duplicate capability types, missing required fields, malformed bindings, conflicting anchor data, and unresolved or ambiguous room references. Import and assembly failures must roll back the complete operation.

Preserve existing schema constraints, including age bounds, literal imported base stats, reference validation, and identifier integrity. Do not weaken existing checks as part of the cutover.

### 4.3 Stable service-host identity

A synchronized host has an explicit stable authored identity independent of capability type, order, display name, and component-level service identifiers. Reuse existing canonical host identifiers where available; do not introduce a general-purpose NPC identity system.

Host lookup must no longer inspect the first capability. Reordering, adding, or removing capabilities must not create another host. Preserve duplicate-host integrity checks and fail-closed behavior.

For source-managed hosts, synchronization converges the managed service-capability set to the declaration. Add missing capabilities and remove obsolete managed capabilities. Do not delete unrelated components.

Update only authored configuration fields. Preserve subsystem-owned runtime state such as stock and restock progress, and preserve location, inventory, relationships, and other game state except where an existing, separately owned lifecycle operation explicitly requires a change. Repeated synchronization must be idempotent.

Capability assembly must not take over naming, trait initialization, scheduling, or commerce lifecycle responsibilities.

## 5. Guild Examinations and Persistent Adventurers

Remove the examiner profession blueprint. Rename the existing counter component and its authored type from examiner terminology to examination-reception terminology, reflecting its actual request-handling role. Migrate all callers and remove the old name without aliases.

Keep these responsibilities separate:

- The counter's examination-reception capability accepts requests and identifies the branch.
- The existing examination qualification table chooses a persistent adventurer for the target rank.
- The selected adventurer participates in the examination under existing examination rules.

Examiner qualification does not automatically grant a counter service to the adventurer. Preserve examination availability, costs, scheduling, skill selection, and results unless a change is strictly required by the naming and declaration cutover.

Remove the unused profession field from persistent-adventurer definitions and stop writing `db.profession`. Keep character identity, equipment, skills, residence, schedules, and the independent qualification table. Do not consolidate these into a new generic character registry.

## 6. NPC Identity, Players, and Companions

Remove the independent NPC title field from authoring, imports, creation, readers, editing surfaces, and presentation. Stop composing titles into NPC display names across exploration, dialogue, party, inspection, and management surfaces. Do not merge old title text into the name or add a replacement short-role field.

Preserve narrative roles in existing descriptions, persona cards, and dialogue where they remain in-character. Scenario NPC free-text roles and NPC tiers remain separate concepts; this design does not remove them.

Player titles, guild ranks, merit, social identities, skills, and character creation remain unchanged. Do not introduce player service capabilities or classes.

Companions use the ordinary NPC capability rules. Joining, leaving, or possession does not grant or remove capabilities. Existing invitation eligibility, party capacity, commander resolution, possession restrictions, and schedule/autonomy silencing remain unchanged. A place-bound service pauses away from its anchor; a person-bound service still obeys existing co-presence and permission rules.

This change does not make currently ineligible service NPCs recruitable.

## 7. Contextual Service Projection

For the selected NPC and current acting/viewing context, project service entries with stable semantic identity, player-facing label, availability, an explanatory reason when unavailable, and a route to an existing service flow.

A component may expose multiple service entries. A dialogue component alone does not imply a service. Dialogue-based services require an explicit association to an existing supported dialogue entry; do not parse prose or infer services from names, roles, titles, or descriptions.

General interactions such as look, talk, invite, possession, and existing persona actions remain outside the service list. Existing eligibility and disclosure rules still apply.

Distinguish service-entry availability from operation-specific eligibility. A provider away from its shop may expose a paused entry. An unaffordable product is explained inside the shop rather than making the entire shop appear unavailable. Preserve existing domain decisions about where a flow can be entered.

Opening a route identifies the selected NPC explicitly. Never substitute another provider in the room. The deterministic command boundary must revalidate the target, co-presence, capability, binding, and applicable permissions when the operation is submitted.

No client-supplied enabled flag authorizes an operation.

## 8. Player Menu and Numbering

### 8.1 Order and invariant slots

Use these groups in this order:

1. Common interactions: `1．交談`, `2．查看人物`.
2. Existing conditional interactions in deterministic order.
3. Contextual service entries in deterministic order.
4. The existing unnumbered return control, also available through Escape.

Keep the first two positions across NPCs. An unavailable common interaction retains its position and reason rather than allowing another action to occupy the slot. Preserve eligibility checks for the underlying action.

Conditional interactions and services receive subsequent numbers. Their numbers may differ between NPCs because their available sets differ. Do not allocate global reserved numbers for every possible service.

Paused entries retain their place and number. Display digit shortcuts only for positions 1 through 9. Later entries remain accessible through scrolling and keyboard navigation without creating another numbering scheme. Do not advertise a digit shortcut that activates a different row.

Use stable entry identities for selection and focus. A state refresh must not submit an operation chosen from an obsolete menu mapping. An update to the set of entries requires a fresh selection against the updated list.

### 8.2 States

| State | Presentation and behavior |
|---|---|
| No services | Omit the service group; retain ordinary interactions |
| Service available | Actionable player-facing label opening its existing flow |
| Service paused | Retain entry and number; show an explicit pause label and inline reason; allow focus but no execution |
| Service information unreadable | Show `服務資訊暫時無法讀取。`; expose no stale actionable service rows; do not treat this as an empty list |
| NPC departs or becomes unavailable to interact with | Close that NPC's card and prevent stale service actions |

The service-list component does not perform purchases, start combat, or bypass existing confirmations. Selecting an entry opens the appropriate existing workflow.

### 8.3 Input, focus, and readability

Support pointer selection and the existing keyboard composite. Arrows move selection, Enter/Space activate, digit shortcuts activate their labeled rows, and Escape returns. Home/End preserve the shared card's first/last-row behavior, including End selecting the trailing return row.

Use a visible focus treatment. Disabled entries remain focusable within the composite so their reasons can be read. Pause and error distinctions need text rather than color alone or hover-only explanations. Group headings must be exposed to assistive technology, not generated only through CSS.

Closing a service flow restores focus to its originating entry while the NPC, card, and entry remain valid. Otherwise use the card's valid fallback or the existing presence-rail fallback. Closing a card returns focus to its originating presence entry when possible. Departure uses the existing fallback because that entry is gone.

Follow existing text scaling, scrolling, localization, motion settings, and stage layout. Do not introduce decorative notification or animation systems. Keyboard operation is required; this design does not add new controller support beyond existing platform input support.

The text-client command surface must provide equivalent service discovery and availability reasons through existing inspection/interaction conventions. If command syntax or aliases change, update both command references in the same implementation change.

## 9. Management Presentation

Remove the NPC title editor/field and the duplicate profession summary. Present player-facing services with availability and reasons, and retain capability configuration details for technical inspection, including bindings and anchors.

Keep player-visible capabilities and management diagnostics distinct. The management view may inspect configuration without pretending to be a player authorized to perform a service. Any player-context preview must use the same contextual projection rules.

The game and GM frontends retain their existing import boundary. Share server-side semantics, not Vue components across those application trees.

## 10. Cutover and Documentation

Perform a clean cutover of all affected producers, consumers, tests, authoring examples, and current capability specs. Remove obsolete profession APIs, component names, NPC title composition helpers, comments, and compatibility exports rather than retaining shims.

Do not add data migrations or legacy-input support. Old stored profession/title attributes are inert and no longer read; rebuilding or cleaning historical stored data is outside this change. Source-managed hosts still use the convergent synchronization contract above.

Update current main specifications, authoring and management guides, relevant logging documentation if events change, and affected active proposal artifacts. Historical archived changes and older design documents remain historical evidence. This design explicitly supersedes profession-blueprint decisions and NPC-title decisions where they conflict; it does not replace the architectural source of truth or unrelated identity contracts.

## 11. Change Decomposition

### 11.1 Scope authority and sequencing

This document is the single scope source for the ten OpenSpec changes below. Proposing them accepted the plan; production edits still require the project apply workflow. The project is unreleased, so no save migration, legacy input reader, renamed-component alias, profession bundle, or new gameplay service is authorized.

| ID | Change | Direct prerequisites | Tasks | Runnable outcome |
|---|---|---|---:|---|
| R | `npc-examination-reception` | none | 3 | New reception slot everywhere; qualified adventurers remain separate and receive no profession writes |
| H | `npc-service-host-identity` | R | 4 | Existing canonical profile identity owns reuse and managed reconciliation; live state survives |
| D | `npc-direct-capability-declarations` | H, `authored-dialogue-generated-packages` | 6 | Import, place, roster, and generated issuer producers use complete validated plans; profession machinery is deleted |
| S | `npc-plain-name-presentation` | H | 4 | All title readers, composers, and editor header fields disappear while remaining creators stay valid |
| N | `npc-title-authoring-removal` | D, S, `authored-dialogue-generated-packages` | 4 | All remaining title schemas, validators, and writes disappear from final static and generated producers |
| T | `npc-targeted-service-flows` | R, `webclient-settlement-alignment` | 5 | Current drawers, six mutations, and the ordinary-abandon payload retain an exact provider; rank becomes independently navigable |
| P | `npc-contextual-service-projection` | N, D, T, `authored-dialogue-generated-packages`, `authored-dialogue-content-guild` | 5 | Derived contextual service descriptors, explicit source associations, and real existing route handoffs work in the current flat card |
| X | `npc-service-text-parity` | P | 4 | Inspection, discovery, and explicit provider command suffixes use the same projection and authority |
| U | `npc-interaction-service-card` | S, P, X, `authored-dialogue-reading-client`, `authored-dialogue-unread-notices`, `webclient-immutable-adoption` | 5 | Production grouped card has fixed common slots, accessible reasons, and stale-entry and focus safety |
| G | `npc-service-management-inspection` | N, P | 4 | Independent GM service descriptions, context-required availability, and technical binding and anchor diagnostics |

The batch carries 44 implementation tasks. Direct new-change edges are R to H, H to D, H to S, D to N, S to N, R to T, N to P, D to P, T to P, P to X, S to U, P to U, X to U, N to G, and P to G. All other precedence is transitive. A valid sequence, respecting active prerequisite completion, is R, H, D, S, N, T, P, X, U, G. G can start once its own dependencies finish, and X with U can be scheduled independently, subject to shared documentation and manifests.

Each step replaces an existing owner rather than adding a compatibility layer. R keeps one valid renamed profession expansion mechanism until D removes it. H consumes resolved plans until D changes the input shape. S removes presentation reads before N removes producers. T migrates every current provider action producer and consumer together, so no old payload fallback is needed. P adds working routes to the existing flat card before U changes grouping. X completes text parity without turning services into a new domain implementation. No change ends with an unwired route, fake backend, or disabled placeholder for later work.

### 11.2 New-change source conflicts

The next table lists every non-manifest overlap in source ownership. Pairs absent from it are disjoint in production code and carry no extra semantic dependency beyond the graph above. Every pair still serializes shared documentation, `.github/evennia-shards.json`, `.github/browser-shards.json`, showcase ownership, and traceability registrations instead of overwriting a sibling edit.

| Conflict group | Shared source family | Change pairs |
|---|---|---|
| Component vocabulary and configuration | `typeclasses/components.py`, `profession_config` and `profession_assembly` before deletion, `npc_capabilities` after cutover, service binding fixtures | R-H, R-D, H-D, D-P |
| Guild deterministic authority | `guild_exams.py`, `human_guild_hosts.py`, `guild_adventurers.py`, guild and registration service gates | R-N, R-T, R-P, R-X, T-X |
| Host and authoring carriers | `guild_economy.py`, `guild_config`, settlement places and shops, import schema, validation, and loader | H-N, D-N, H-S |
| NPC name and identity consumers | `typeclasses/npcs.py`, `npc_identity.py`, `world/rules/dialogue.py`, `party_scope`, command item messages | S-N, S-P, S-X |
| Current service read and action surfaces | `service_view.py`, `service_actions.py`, services serializer, UMD validators, and menu builders | R-T, R-S, S-T, T-P, T-U, P-U |
| Dialogue source and selection | common codec and shape, `dialogue_sources`, `dialogue.py`, generated package schema | N-P, P-X, P-U |
| Game interaction models | exploration presenter, UMD validator and menu, frame resolvers, `presence.js`, `use-person-focus`, `ChoiceCard`, `AppClient` route handoff | S-P, S-U, T-P, T-U, P-U, X-U |
| Independent management | `web/gm/readers/npcs.py` and GM reader fixtures | R-S, R-G, S-G, N-G, D-G |

Host creation always remains in the deterministic core. Nothing under `world/ai/` applies capability configuration or commerce state. Opening a service is a read and navigation step; existing domain owners alone perform registration, trade, examinations, enrollment, and commission effects.

### 11.3 Active changes and integration contracts

Every name below was present in `openspec list --json` during planning. Presence in that list is not proof of implementation. Wait for a named semantic prerequisite to finish before applying the dependent change. Other entries constrain source integration without being hidden implementation dependencies.

| Active change | Semantic dependency for this batch | Overlap and integration contract |
|---|---|---|
| `authored-dialogue-generated-packages` | before D, N, and P | `packages.py`, generation and prompt, `scene_package` and compile, `dialogue_sources` and `dialogue.py`. D first adds explicit generated issuer plans, N removes title without losing those plans, then P adds service-bound dialogue and associations. Preserve topic effect authority, source-aware IDs, phase retirement, and immutable package publication |
| `authored-dialogue-content-guild` | before P | `guild_staff.topic_04` report association and the guild deterministic report exception. P adds explicit source metadata after the body rewrite, keeping its topic ID and granting no extra reading, affinity, or effect reward |
| `authored-dialogue-content-lower-hospitality` | none | Existing inn and tavern prose grants no gameplay entitlement. Preserve baseline topics and profile identity, and infer no service from lodging or tavern wording |
| `authored-dialogue-content-lower-civic` | none | Bathhouse and guardhouse prose stays narrative and creates no real service |
| `authored-dialogue-content-middle-tools` | none | Existing merchant components remain trade authority; topic prose does not grant trade |
| `authored-dialogue-content-middle-exchange` | none | Same profile and topic ownership; merchant-hall prose stays informational |
| `authored-dialogue-content-upper-faith` | none | ChurchHost enrollment and the sanctum merchant stay distinct; no service is inferred from temple prose |
| `authored-dialogue-content-upper-civic` | none | Drill-yard, academy, and watch topics promise no training, examination, or guard service backend |
| `authored-dialogue-content-ciaran-commons` | none | Homes and dialogue stay narrative; no automatic attendant service appears |
| `authored-dialogue-content-ciaran-crafts` | none | Shipped merchant functionality stays owned by direct Merchant declarations |
| `authored-dialogue-content-ciaran-fare` | none | Shipped merchant functionality stays; no prose or service inference |
| `authored-dialogue-refresh-lifecycle` | none, serialize shared writers with R, H, S, T, and P | `guild.py`, examinations, NPC move and delete hooks, possession and time callbacks. Retain post-commit owner discovery, old-context retirement, and current actor re-resolution. New provider navigation does not replace these refresh owners |
| `authored-dialogue-reading-client` | before U | `dialogue_reading.js`, transport, dialogue view, `AppClient`, and return to choices. Service, opening, and refusal deliveries create no formal reading receipt and no optimistic eligibility |
| `authored-dialogue-unread-notices` | before U | `dialogue.py`, availability, pushes, reading client and toasts, `DialogueChoices`. Preserve deduplication, deferral, and non-focus-stealing notices when services open or close |
| `webclient-delta-contract` | transitive before T through settlement alignment | Protocol metadata, constants, and fixtures. Preserve exact-base E/R/B, `removed_panels`, and staged mode and dialogue checks. Panel schema changes do not alter envelope semantics |
| `webclient-publication-baseline` | transitive before T | Coordinator, dispatcher, ingress, and current push candidates. `services.open` read results stay private and target-correlated, and provider mutations use existing canonical publication helpers |
| `webclient-publication-settlements` | transitive before T | Causal callback groups and NPC cleanup. H rollback and U departure respect after-commit boundaries and retain no causal tokens |
| `webclient-publication-codec` | no additional dependency, serialize protocol and constants fixtures | Keep panel-local bounds and general publication preflight. Add no transport protocol and relax no envelope limit |
| `webclient-publication-assembly` | no additional dependency, serialize receiver fixtures | Do not expose incomplete service panels or adopt metadata before multipart completion |
| `webclient-sync-recovery` | transitive before U through immutable adoption | Transport, generation, and result gate. Service responses from an obsolete transport or card are discarded, and no local retry grants gameplay authority |
| `webclient-movement-alignment` | transitive before T through settlement alignment | Relocation identity and causal settlement. Reused-host synchronization no longer relocates NPCs, and real movement or departure keeps existing committed lifecycle publication |
| `webclient-settlement-alignment` | before T | `service_actions` examination start and terminal receipt classification. Preserve committed checkpoint facts and the schedule-only no-mutation result |
| `webclient-immutable-adoption` | before U | Presence, interaction, HUD, view, and frame resolvers. Store rendered mapping signatures and origin focus only in client-owned mutable state, never decorate frozen panels, and do not reset on same-content alignment |
| `webclient-sync-functional-smoke` | no additional dependency, serialize browser fixtures and manifests | Keep its large-publication and recovery smoke ownership. U adds a separate focused real NPC shop and reception smoke without replacing full synchronization acceptance |

### 11.4 Amendment contract for still-active proposals

The proposal run left existing active proposals and current main specifications unchanged. The following amendments belong to the owning apply tasks, so the applying change carries the supersession text into the targets it touches. Archived changes and this approved design stay unedited.

| Owner | Still-active targets | Amendment to add at apply |
|---|---|---|
| D | `authored-dialogue-generated-packages` | Commission roles explicitly author direct person-bound `quest_issuer` configuration with complete scoped `service_id` and `issuer_key`. `RoleDefinition.capabilities` and `RoleSpawn` carry a validated plan into deterministic activation and `provision_scoped_issuer`; missing or conflicting plans reject atomically. Narrative-only dialogue stays unbound. |
| N | `authored-dialogue-generated-packages` | NPC characterization excludes title. Require `display_name` and persona while retaining role, tier, the age pair, portrait, canonical identity and digest, and generated package authority. No title field is accepted, serialized, prompted, or written. Apply title removal after generated packages and before contextual service projection. |
| N | all ten `authored-dialogue-content-*` changes named above | Host functionality uses explicit capabilities and canonical profile identity, with no profession and no independent NPC title field. Keep authored narrative voice and roles inside existing persona, description, and dialogue prose, and preserve topic IDs. Prose never grants a service. This amendment requests no baseline body rewrite |
| P | `authored-dialogue-generated-packages` | The optional services association list uses exact key, topic ID, and label rows with same-source, same-phase canonical topic IDs and existing deterministic supported effects. It grants no effect, reading completion, or additional authority at projection or open time, and invalid associations reject the complete source or package. |
| P | `authored-dialogue-content-guild` | Keep `guild_staff.topic_04` as the deterministic report and list entry. Declare the explicit `guild_report_dialogue` association after content authoring, and let the association grant no registration, turn-in reward, or formal reading completion. |
| T | `webclient-settlement-alignment` | Provider-dependent service actions, including ordinary guild abandonment, carry `npc_id` and resolve that exact provider. Private escort abandonment retains `quest_id` alone, and canonical record classification rejects shape confusion. Preserve start, terminal, and schedule-only causal settlement classification; `services.open` stays a private read. |
| U | `authored-dialogue-reading-client`, `authored-dialogue-unread-notices`, `webclient-immutable-adoption` | NPC service navigation preserves source-aware reading receipts and contexts, ignores opening, service, and refusal completion, defers notices without focus theft, and keeps menu signatures and focus origins outside immutable committed presentation. Late provider responses cannot reopen retired cards. |

Remaining active publication and lifecycle changes need integration preservation only. No planned behavior or delta requirement is superseded. Do not mark them completed, rewrite their authorship, or invent semantic dependencies to avoid ordinary shared-file coordination.

### 11.5 Acceptance coverage

| Design sections | Owning changes and permanent evidence |
|---|---|
| 4.1, 4.2 direct input, mixed binding, atomicity | D validates exact schema, types, kwargs, references, and anchors, and import with roster share one core. An invalid last row and a faulted add, update, or remove roll back the database and handler caches |
| 4.3 host identity and reconciliation | H tests canonical identity through reorder, add, remove, and empty plan, duplicate ownership rejection, and unchanged stock, restock day, location, inventory, and relationships. Whole-row lifecycle stays separate |
| 5 examination and unused profession | R tests reception against qualification and the absence of adventurer profession writes. T preserves target reception with an independently selected actual adventurer and schedule-first existing eligibility |
| 6 identity and companions | S removes every identity reader and composer, and N removes all producer fields and writes. Player title and scene role, tier, name, age, and portrait behavior stay, and no service capability changes current recruitment or possession eligibility |
| 7 contextual services | T performs the explicit provider read and action cutover. P covers exhaustive real-service mapping and explicit source associations with hidden, locked, phase, and stale validation, and no prose inference |
| 8.1 numbering and mapping | U fixes talk and look, conditional order, service order, paused positions, digits limited to 1 through 9, and fresh selection after mapping changes |
| 8.2 states | P and U distinguish none from unreadable, keep zero stale service rows, show disabled reasons, and close the card on departure |
| 8.3 inputs and focus | U provides real labeled groups, focusable disabled rows, pointer and keyboard Home, End, Enter, Space, and Escape, service return, and the rail fallback. X adds text discovery and targeting parity and updates both references |
| 9 management | G uses existing GM primitives with context-required availability and complete configuration diagnostics, without impersonation or game Vue imports |
| 10 cutover and documentation | Every owner changes its current deltas, documentation, tests, and callers and removes its obsolete APIs. N, P, T, and U amend still-active artifacts as specified in 11.4. No history rewrite, compatibility shim, or data migration |
| 12 prototype limitations | U replaces CSS-only headings with accessible real headings and keeps the prototype control strip out of production. Existing backend flows are exercised, and synthetic overflow stays explicitly test-only |
| 13 verification | Each owner has focused commands, and new tests are named as proposed additions. U runs an actual production merchant purchase and reception route smoke with AI disabled. Final implementation contract gate, shard ownership, and relevant logging checks are required, while full browser and evidence suites stay CI-owned |

### 11.6 Planning verification record

The final proposal verification batch reported all ten changes valid under `openspec validate <change> --strict`, complete required artifact closures, and `os-phase <change>` reporting `phase=proposed primary=master branch=none worktree=none`. The first strict pass rejected seven changes for omitted or renamed historical scenario headings; their complete updated scenarios were restored and only those seven failed validations were retried, all successfully. Historical scenario names are retained for OpenSpec replacement identity while their WHEN and THEN bodies express the approved new behavior. No gameplay test, build, lint, formatter, or prototype rebuild ran during planning. Unchecked tasks are intended implementation work and do not claim implementation occurred.

### 11.7 Independent review disposition

One blocking whole-batch rubber-duck critique reviewed all proposals, designs, tasks, and deltas against this document and the current code. It found six blockers, all adopted in proposal follow-up commits. Ordinary guild abandonment now has provider-bound input discriminated by the canonical record, separate from host-free private escorts. Dialogue services now open and focus without topic selection, so opening a generated commission accepts no quest. D and P now define the explicit generated capability carrier with a real publication, activation, and provisioning path. T restores the complete host-resolution requirement and the independently selected reception rank gate. X names the actual shop stock, buy, and sell and guild examination command owners and adds command-authority deltas. U immediately retires committed lost-target correlation even under submission locks.

Both nonblocking notes were also adopted. `services.open` uses an exact `{npc_id, services}` result wrapper within current field, depth, string, and byte limits. Association keys fit the final prefixed key, and aggregate capacity rejects before publication instead of truncating. No second independent review was requested; final strict validation is separate mechanical evidence and does not claim gameplay verification.

## 12. Prototype and Observed Evidence

The exploratory prototype lives under `docs/design/npc-service-menu/` and is isolated from the production app. Its Storybook title is `Design/NpcServiceMenu`.

The ten stories cover the interactive scenario, no services, available services, paused services, unavailable talk, fixed numbering with conditionals, service-read failure, departure, an already-open service flow, and overflow.

The prototype uses real stage, presence, choice-card, and drawer components with synthetic NPCs and clearly labeled simulation controls. Demonstration panes do not implement trading or examinations and dispatch no game commands. Synthetic overflow entries demonstrate layout rather than promise additional gameplay services.

Observed verification before this document was written:

- `pnpm run build-storybook` succeeded.
- `pnpm run showcase-coverage` succeeded for the existing frozen game and GM manifests; prototype stories are outside that component manifest.
- `uv run --locked python -m tools.contract_gate` passed.
- Browser interaction exercised service opening and Escape return with restored selection, paused-service non-execution, unavailable talk retaining its slot, conditional ordering, unreadable-service presentation, overflow navigation, and departure with focus returning to the presence rail.
- Settled screenshots confirmed no-service and overflow layouts. Existing entrance/exit animation must be allowed to settle before evaluating row visibility.

Prototype limitations to resolve in production integration:

- Group headings are currently visual CSS output; production needs accessible group labels.
- The prototype-only control strip is pointer-operated while the card's existing keyboard focus trap is active. This is not a production navigation requirement; named stories allow direct access to those simulated states.
- The service panes are expressly navigation demonstrations, not implementations or proof of deterministic authorization.

This evidence establishes the prototype behavior only. It does not establish backend cutover correctness or substitute for implementation verification.

## 13. Implementation Acceptance and Verification

Implement and verify these consumer-visible outcomes:

- Multiple capabilities work independently, including mixed person/place bindings on one NPC.
- Complete authored-input failure rolls back all persistent writes; duplicate types and invalid anchors are rejected.
- Reordering capabilities preserves host identity. Repeated synchronization creates no duplicate NPC, removes obsolete managed capabilities, and preserves commerce/runtime state.
- Existing service targets remain correct when more than one provider is present. Faults and stale menus cannot bypass domain validation.
- Examination reception selects the expected qualified adventurer without granting that adventurer a counter capability.
- All NPC identity surfaces omit independent titles; player title behavior is unchanged.
- Fixed menu slots, paused reasons, absence versus read failure, overflow, keyboard focus, service return, and departure work on the actual integrated surface.
- Text-client service discovery and management inspection agree with the same capability and availability semantics.

Use the smallest relevant pure-logic, Evennia integration, component, and browser checks under existing project conventions. Add permanent tests for uncertain behavior, boundaries, rollback, and stale-target failures; do not add source-text or fixture-echo assertions. Update shard ownership and traceability when their owned tests/specs change. Logging changes require observability lint and focused tests in the same verification batch.

Run the actual integrated service path in a focused smoke scenario, not only isolated tests or the prototype. Run the project contract gate and applicable strict OpenSpec validation before implementation handoff. Full browser and complete traceability-evidence suites remain CI-owned.

## 14. Non-goals

No player class system, new NPC profession vocabulary, capability bundle registry, general NPC registry, balance changes, new services, party eligibility changes, new commerce/examination workflows, historical save migration, or implementation work is authorized by this design document alone.

This document authorizes planning only. Production implementation proceeds through the OpenSpec apply workflow for each change in section 11.1 and requires its own project authorization.
