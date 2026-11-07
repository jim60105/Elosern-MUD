## MODIFIED Requirements

### Requirement: The descriptor registry implements the exploration family as a finite table

The registry SHALL implement exactly the exploration-family source table and nothing else in this change, each entry producing the menu its current push site produces today. A source absent from the implemented table SHALL resolve to the shared unresolvable marker without throwing, and every table addition SHALL be a spec-visible change.

#### Scenario: Every table source resolves from a live snapshot

- **WHEN** each table source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its current push site produces, with the same row keys, server-authored payloads, and titles

#### Scenario: An unregistered source degrades

- **WHEN** `resolve` is called with a source absent from the table
- **THEN** it returns the unresolvable marker and the caller can render or pop without catching an exception

#### Scenario: A retired exploration source degrades instead of resolving

- **WHEN** `exploration.move`, `exploration.look`, `exploration.interact`, `exploration.target`, `exploration.wait`, or `exploration.suggestions` is resolved (the first three frames were retired with the exploration tab root, the target frame with the verb popover, whose place the client-local verb card took, and the waiting and suggestions frames with the scene overview, whose places the client-local wait card and then-retired suggestions card took)
- **THEN** each returns the shared unresolvable marker and produces no menu, so a stray push of one pops instead of resurrecting a pane

#### Scenario: A withdrawn suggestions envelope degrades like a lost identity

- **WHEN** the committed `context_actions` payload of the retired suggestions surface is inspected after the envelope's removal
- **THEN** the client exposes no suggestions accessor and the exploration dock therefore presents no suggestion content and no 建議 pill

#### Scenario: Suggestions resolve only under the three live statuses

- **WHEN** the client's presentation code is inspected for a reader of the retired `context_actions.suggestions` envelope
- **THEN** no such reader exists — no status branch and no card content can be produced from a field the panel no longer carries, and the exploration dock renders only its compass and readout

#### Scenario: The later families arrive as table rows from their migration changes

- **WHEN** the services, combat, and creation families are cut over
- **THEN** the services family (guild/board/quests/quest-detail/shop/stock/sell frames plus the abandon-confirm frame, keyed by `questIndex`), the combat family (`root`, `categories`, `category{categoryIndex}`, `group{categoryIndex, groupIndex}`, `skill{skillKey}`, `target{skillKey}`, `forfeit`), and the creation family (`root`, `presets`, `form{view}`, `confirm{kind, presetKey?}`) are added as further table rows by the later migration changes that cut their push sites over

#### Scenario: The exploration table is exactly five sources

- **WHEN** the exploration-family source table is declared
- **THEN** its live sources (panel `exploration`; `exploration.root` resolves to an empty menu under the exploration panel gate) are exactly `exploration.root` `{}` and `exploration.navigation` `{}` — of the five sources this scenario once named, `exploration.target` and `exploration.keywords` are retired, and `exploration.wait` and `exploration.suggestions` with them, each degrading like every unregistered source — the independent compass and dialogue exit rows (reading `local_map.current_node`), the presence rail's entries, an interact target's verb rows, and the place card's room look row are read through accessors outside the table and are never frames

### Requirement: Dynamic rows and payloads are verbatim from the panel while client-owned navigation rows are reproduced

Domain rows — entity lists, exits, targets, quest/board/shop entries, skill descriptors, and every action identifier and payload — SHALL come verbatim from the committed panel exactly as the existing menu builders produce them: the resolver SHALL NOT invent, reorder, filter, or relabel domain content beyond what the named builder already does.

#### Scenario: A resolved submenu keeps its back row

- **WHEN** the verb card's accessor reads an available exploration panel and a present target with server-authored rows
- **THEN** it holds the builder's verb rows without the builder's `back` row, which the card replaces with its own trailing `✕ 返回`, and no back row submits anything

#### Scenario: Domain relabeling is absent by construction

- **WHEN** the presence rail's look entries or a target's verb rows resolve against a panel whose rows carry server-authored labels and disabled reasons
- **THEN** every domain row's label, sub-line, action identifier, payload, and disabled reason equal the committed panel's values

#### Scenario: Required navigation rows are reproduced, not fabricated

- **WHEN** a resolved menu needs the client-owned navigation and presentation rows that the shipped dock contract requires — the place card's room look row, the presence rail's and the verb card's builder rows, the services/creation root entries, `back` rows of submenus, the combat forfeit confirm/cancel pair, and disabled explanatory rows
- **THEN** those rows are reproduced by the same builders, and reproducing them does not count as fabrication

## REMOVED Requirements

### Requirement: Suggestions frames are status-driven: generating never pops, unavailable exits to the root
**Reason**: The suggestions surface is retired end to end; no client accessor reads a `context_actions.suggestions` envelope, so no status-driven card lifecycle remains to specify.
**Migration**: None. The wait card's open/close contract is owned by `webclient-room-actions`.
