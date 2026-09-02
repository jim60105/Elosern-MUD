# webclient-frame-resolution Specification

## Purpose
TBD - created by archiving change webclient-frame-resolver-registry. Update Purpose after archive.
## Requirements
### Requirement: Frame descriptors resolve to committed-state menus at access time

The store SHALL own a frame resolver registry that maps a frame descriptor `{source, params}` to a menu derived from the committed presentation state at the moment of the call. A resolver SHALL read only committed panels (the state the protocol reducer has atomically committed under the revision gate) and SHALL NOT read router frame copies, component state, or any other cached menu data. Resolving the same descriptor twice across two committed states SHALL return menus reflecting each state respectively; resolving the same descriptor twice against one committed state SHALL return deep-equal menus and SHALL NOT mutate store, model, or committed state. Later table waves (combat selection preservation through the existing `rebuildForPanel` seam) SHALL declare any permitted model-state exception as a spec-visible amendment with its own idempotency scenario. A resolver that throws SHALL be caught by the registry and reported as unresolvable rather than propagating to callers.

#### Scenario: Resolution follows committed state

- **WHEN** a descriptor is resolved, a newer committed snapshot replaces the panels it names, and the same descriptor is resolved again
- **THEN** the second menu reflects the newer committed panels and no row from the superseded state remains

#### Scenario: Resolution is pure against one committed state

- **WHEN** the same descriptor is resolved twice against the same committed state through the bridge-exposed resolver
- **THEN** both results are deep-equal and the committed state, router state, and model state are unchanged

#### Scenario: A throwing resolver degrades instead of crashing

- **WHEN** a registered resolver raises on a well-formed descriptor
- **THEN** `resolve` returns the shared unresolvable marker and no exception reaches the caller

### Requirement: The descriptor registry implements the exploration family as a finite table

The registry SHALL implement exactly the exploration-family source table and nothing else in this change, each entry producing the menu its current push site produces today. Sources (panel `exploration`; `exploration.move` additionally reads `local_map.current_node`; `exploration.suggestions` reads `context_actions.suggestions`): `exploration.root` `{}`, `exploration.move` `{}`, `exploration.look` `{}`, `exploration.interact` `{}`, `exploration.wait` `{}`, `exploration.target` `{identity}`, `exploration.keywords` `{identity}`, `exploration.suggestions` `{}` — resolvable only while the envelope status is `generating`, `ready`, or `degraded`; status `unavailable` resolves to the unresolvable marker so an open suggestions frame can honor the surface's no-pane rule. The services family (guild/board/quests/quest-detail/shop/stock/sell frames plus the abandon-confirm frame, keyed by `questIndex`), the combat family (`root`, `categories`, `category{categoryIndex}`, `group{categoryIndex, groupIndex}`, `skill{skillKey}`, `target{skillKey}`, `forfeit`), and the creation family (`root`, `presets`, `form{view}`, `confirm{kind, presetKey?}`) SHALL be added as further table rows by the later migration changes that cut their push sites over; a source absent from the implemented table SHALL resolve to the shared unresolvable marker without throwing, and every table addition SHALL be a spec-visible change.

#### Scenario: Every table source resolves from a live snapshot

- **WHEN** each table source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its current push site produces, with the same row keys, server-authored payloads, and titles

#### Scenario: An unregistered source degrades

- **WHEN** `resolve` is called with a source absent from the table
- **THEN** it returns the unresolvable marker and the caller can render or pop without catching an exception

#### Scenario: A withdrawn suggestions envelope degrades like a lost identity

- **WHEN** `exploration.suggestions` is resolved while the committed envelope status is `unavailable`
- **THEN** resolve returns the unresolvable marker so the consumer-side rule can leave the frame, and a `generating` status instead resolves to the muted generating row menu

### Requirement: Dynamic rows and payloads are verbatim from the panel while client-owned navigation rows are reproduced

Domain rows — entity lists, exits, targets, quest/board/shop entries, skill descriptors, and every action identifier and payload — SHALL come verbatim from the committed panel exactly as the existing menu builders produce them: the resolver SHALL NOT invent, reorder, filter, or relabel domain content beyond what the named builder already does. Client-owned navigation and presentation rows that the shipped dock contract requires — the exploration/services/creation root entries, `back` rows of submenus, the combat forfeit confirm/cancel pair, and disabled explanatory rows — SHALL be reproduced by the same builders, and reproducing them SHALL NOT count as fabrication.

#### Scenario: A resolved submenu keeps its back row

- **WHEN** `exploration.move` resolves against a room with two exits
- **THEN** the menu holds exactly the two server-authored exit rows plus the builder's `back` row, with payloads identical to the committed panel's

#### Scenario: Domain relabeling is absent by construction

- **WHEN** a look or target frame resolves against a panel whose rows carry server-authored labels and disabled reasons
- **THEN** every domain row's label, sub-line, action identifier, payload, and disabled reason equal the committed panel's values

### Requirement: An unresolvable descriptor yields the shared degradation marker with the server-authored reason

A descriptor whose identity or index is absent from the committed panel, whose panel is in an unavailable form, or whose resolver threw SHALL resolve to a shared unresolvable marker `{unresolvable: true, reason}`. Where the committed panel carries a server-authored `reason.message`, the marker's `reason` SHALL be that message verbatim; otherwise the marker's `reason` SHALL be null and the local fallback string 「畫面狀態已更新，請返回上層」 SHALL only be chosen by the consumer when rendering. The marker is data: resolving an unresolvable descriptor SHALL never throw, and pop-versus-disabled handling belongs to the consumer-side stack rules, not the registry.

#### Scenario: Identity loss reports the server message

- **WHEN** a target descriptor names an `identity` the committed `exploration` panel no longer lists and the panel carries `reason.message`
- **THEN** resolve returns the unresolvable marker whose reason equals that server-authored message

#### Scenario: Missing server message leaves the reason null

- **WHEN** an unresolvable descriptor's panel carries no authored message
- **THEN** resolve returns the unresolvable marker with a null reason

