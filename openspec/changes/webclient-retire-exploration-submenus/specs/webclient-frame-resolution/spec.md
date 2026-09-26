## MODIFIED Requirements

### Requirement: The descriptor registry implements the exploration family as a finite table

The registry SHALL implement exactly the exploration-family source table and nothing else in this change, each entry producing the menu its current push site produces today. Sources (panel `exploration`; `exploration.root` additionally reads `local_map.current_node`; `exploration.suggestions` reads `context_actions.suggestions`): `exploration.root` `{}`, `exploration.wait` `{}`, `exploration.target` `{identity}`, `exploration.keywords` `{identity}`, `exploration.suggestions` `{}` — resolvable only while the envelope status is `generating`, `ready`, or `degraded`; status `unavailable` resolves to the unresolvable marker so an open suggestions frame can honor the surface's no-pane rule. The services family (guild/board/quests/quest-detail/shop/stock/sell frames plus the abandon-confirm frame, keyed by `questIndex`), the combat family (`root`, `categories`, `category{categoryIndex}`, `group{categoryIndex, groupIndex}`, `skill{skillKey}`, `target{skillKey}`, `forfeit`), and the creation family (`root`, `presets`, `form{view}`, `confirm{kind, presetKey?}`) SHALL be added as further table rows by the later migration changes that cut their push sites over; a source absent from the implemented table SHALL resolve to the shared unresolvable marker without throwing, and every table addition SHALL be a spec-visible change.

#### Scenario: Every table source resolves from a live snapshot

- **WHEN** each table source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its current push site produces, with the same row keys, server-authored payloads, and titles

#### Scenario: An unregistered source degrades

- **WHEN** `resolve` is called with a source absent from the table
- **THEN** it returns the unresolvable marker and the caller can render or pop without catching an exception

#### Scenario: A retired exploration source degrades instead of resolving

- **WHEN** `exploration.move`, `exploration.look`, or `exploration.interact` is resolved (their frames were retired with the exploration tab root, whose root frame is now the scene overview)
- **THEN** each returns the shared unresolvable marker and produces no menu, so a stray push of one pops instead of resurrecting a pane

#### Scenario: A withdrawn suggestions envelope degrades like a lost identity

- **WHEN** `exploration.suggestions` is resolved while the committed envelope status is `unavailable`
- **THEN** resolve returns the unresolvable marker so the consumer-side rule can leave the frame, and a `generating` status instead resolves to the muted generating row menu

### Requirement: Dynamic rows and payloads are verbatim from the panel while client-owned navigation rows are reproduced

Domain rows — entity lists, exits, targets, quest/board/shop entries, skill descriptors, and every action identifier and payload — SHALL come verbatim from the committed panel exactly as the existing menu builders produce them: the resolver SHALL NOT invent, reorder, filter, or relabel domain content beyond what the named builder already does. Client-owned navigation and presentation rows that the shipped dock contract requires — the exploration overview's footer entries and its people/object chip builders' rows, the services/creation root entries, `back` rows of submenus, the combat forfeit confirm/cancel pair, and disabled explanatory rows — SHALL be reproduced by the same builders, and reproducing them SHALL NOT count as fabrication.

#### Scenario: A resolved submenu keeps its back row

- **WHEN** `exploration.wait` resolves against an available panel
- **THEN** the menu holds the builder's server-authored wait rows plus the builder's `back` row, and the `back` row submits nothing

#### Scenario: Domain relabeling is absent by construction

- **WHEN** a look or target frame resolves against a panel whose rows carry server-authored labels and disabled reasons
- **THEN** every domain row's label, sub-line, action identifier, payload, and disabled reason equal the committed panel's values
