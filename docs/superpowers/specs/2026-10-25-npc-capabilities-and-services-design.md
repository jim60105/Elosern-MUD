# NPC Capabilities and Service Presentation Design

**Date:** 2026-10-25
**Status:** Design approved in conversation; written specification awaiting user review.
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

## 11. Prototype and Observed Evidence

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

## 12. Implementation Acceptance and Verification

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

## 13. Non-goals

No player class system, new NPC profession vocabulary, capability bundle registry, general NPC registry, balance changes, new services, party eligibility changes, new commerce/examination workflows, historical save migration, or implementation work is authorized by this design document alone.

The next gate is user review of this written specification. Implementation planning follows that review; production implementation requires its own project workflow authorization.
