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

- **WHEN** `exploration.move`, `exploration.look`, or `exploration.interact` is resolved (their frames were retired with the exploration tab root, whose root frame is now the people/object/footer scene overview beside the separate compass)
- **THEN** each returns the shared unresolvable marker and produces no menu, so a stray push of one pops instead of resurrecting a pane

#### Scenario: A withdrawn suggestions envelope degrades like a lost identity

- **WHEN** `exploration.suggestions` is resolved while the committed envelope status is `unavailable`
- **THEN** resolve returns the unresolvable marker so the consumer-side rule can leave the frame, and a `generating` status instead resolves to the muted generating row menu

#### Scenario: Suggestions resolve only under the three live statuses

- **WHEN** `exploration.suggestions` is resolved under any committed envelope status
- **THEN** it is resolvable only while the status is `generating`, `ready`, or `degraded`, and status `unavailable` resolves to the unresolvable marker so an open suggestions frame can honor the surface's no-pane rule

#### Scenario: The later families arrive as table rows from their migration changes

- **WHEN** the services, combat, and creation families are cut over
- **THEN** the services family (guild/board/quests/quest-detail/shop/stock/sell frames plus the abandon-confirm frame, keyed by `questIndex`), the combat family (`root`, `categories`, `category{categoryIndex}`, `group{categoryIndex, groupIndex}`, `skill{skillKey}`, `target{skillKey}`, `forfeit`), and the creation family (`root`, `presets`, `form{view}`, `confirm{kind, presetKey?}`) are added as further table rows by the later migration changes that cut their push sites over

#### Scenario: The exploration table is exactly five sources

- **WHEN** the exploration-family source table is declared
- **THEN** its sources (panel `exploration`; `exploration.root` reads the committed overview without exit rows; the independent compass and dialogue exit-row source read `local_map.current_node`; `exploration.suggestions` reads `context_actions.suggestions`) are exactly `exploration.root` `{}`, `exploration.wait` `{}`, `exploration.target` `{identity}`, `exploration.keywords` `{identity}`, `exploration.suggestions` `{}`

