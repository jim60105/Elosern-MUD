# Spec Delta

## Purpose

Define derived contextual service discovery bound to a selected NPC and the existing deterministic workflows, with honest availability and safe execution.

## ADDED Requirements

### Requirement: Service discovery derives from selected-provider capabilities
Contextual services SHALL be derived from the selected NPC's capabilities and explicit supported dialogue associations for the current actor/viewer. Entries SHALL have stable semantic identity, a player label, availability/reason and an exact selected-provider route. General interactions SHALL remain outside this list.

#### Scenario: Supported mapping
- **WHEN** merchant, staff, reception and clergy capabilities are present
- **THEN** shop, guild registration/board/report, examination and enrollment routes use their existing deterministic workflows; no new gameplay service appears

#### Scenario: One component exposes several entries
- **WHEN** staff capability is projected
- **THEN** registration, board and report are independent entries in deterministic order

#### Scenario: No inferred dialogue service
- **WHEN** a narrator or drill instructor discusses examinations without a supported explicit association
- **THEN** no examination or other service is inferred from prose, labels or role

#### Scenario: Commission authority alone
- **WHEN** an NPC carries only quest-issuer authority with no public supported topic association
- **THEN** no fabricated commission service is listed

### Requirement: Service availability differs from operation eligibility
Entry availability SHALL preserve current route-entry domain rules, binding, schedule, co-presence and control permissions. Operation-specific costs, stock, registration, merit and quest eligibility SHALL remain owned by the existing flow, unless the current domain explicitly gates entry.

#### Scenario: Poor customer can inspect shop
- **WHEN** a co-present permitted shopper cannot afford any product
- **THEN** the shop entry opens and product-level reasons remain inside the shop

#### Scenario: Off-anchor provider
- **WHEN** a place-bound service is co-present away from its anchor
- **THEN** its entry remains in order as disabled with an inline reason while independent person-bound services retain their gates

#### Scenario: Schedule-first exam
- **WHEN** a registered below-merit player asks at functioning reception while the qualified adventurer is absent
- **THEN** the examination flow retains its existing schedule-first result without a fake disabled-merit entry

### Requirement: Empty service information and unreadable information are distinct
Successful empty projection SHALL report no services. Unreadable projection SHALL report a distinct failure with zero stale actionable entries and the message 服務資訊暫時無法讀取。 Ordinary interactions SHALL remain available independently.

#### Scenario: No services
- **WHEN** a normal NPC has no service entries
- **THEN** the services state is none and the service group is absent

#### Scenario: Read failure
- **WHEN** current service data cannot be projected
- **THEN** state is unreadable, stale service rows are removed and common interactions remain

### Requirement: Explicit dialogue services retain source and execution authority
Dialogue services SHALL reference an existing supported deterministic entry by explicit same-source association. Projection and execution SHALL preserve disclosure, binding and phase/context authority; opening a route SHALL grant no gameplay effect or formal reading completion.

#### Scenario: Bound report dialogue
- **WHEN** the guild report association references its current supported topic
- **THEN** opening selects that exact host/topic through existing context checks without automatic turn-in

#### Scenario: Invalid association rejects atomically
- **WHEN** an association is duplicate, dangling, cross-phase or names an informational unsupported topic
- **THEN** the complete source snapshot/package and authored assembly reject before persistence

#### Scenario: Source changes before selection
- **WHEN** an opened generated service loses its phase/source authority
- **THEN** submission rejects without effect, receipt or stale private scene

### Requirement: Selections always revalidate the exact provider
Execution SHALL re-resolve the selected visible co-present NPC and validate its current capability, binding and applicable permissions. A client enabled flag or another provider's presence SHALL confer no authority.

#### Scenario: Selected provider departs
- **WHEN** another valid same-class provider remains after the selected host leaves
- **THEN** the submitted selection rejects without choosing the remaining host or changing game state

#### Scenario: Control or capability changes
- **WHEN** the acting body or provider capability differs from render
- **THEN** current deterministic validation rejects unauthorized execution
