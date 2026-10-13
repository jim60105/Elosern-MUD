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

- **WHEN** `exploration.move`, `exploration.look`, `exploration.interact`, or `exploration.target` is resolved (the first three frames were retired with the exploration tab root, whose root frame is now the footer scene overview beside the separate compass, and the target frame with the verb popover, whose place the client-local verb card took)
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
- **THEN** its live sources (panel `exploration`; `exploration.root` reads the committed overview without exit, person, or object rows; `exploration.suggestions` reads `context_actions.suggestions`) are exactly `exploration.root` `{}`, `exploration.navigation` `{}`, `exploration.wait` `{}`, and `exploration.suggestions` `{}` — of the five sources this scenario once named, `exploration.target` and `exploration.keywords` are retired and degrade like every unregistered source — the independent compass and dialogue exit rows (reading `local_map.current_node`), the presence rail's entries, and an interact target's verb rows are read through accessors outside the table and are never frames

### Requirement: Dynamic rows and payloads are verbatim from the panel while client-owned navigation rows are reproduced

Domain rows — entity lists, exits, targets, quest/board/shop entries, skill descriptors, and every action identifier and payload — SHALL come verbatim from the committed panel exactly as the existing menu builders produce them: the resolver SHALL NOT invent, reorder, filter, or relabel domain content beyond what the named builder already does.

#### Scenario: A resolved submenu keeps its back row

- **WHEN** `exploration.wait` resolves against an available panel
- **THEN** the menu holds the builder's server-authored wait rows plus the builder's `back` row, and the `back` row submits nothing

#### Scenario: Domain relabeling is absent by construction

- **WHEN** the presence rail's look entries or a target's verb rows resolve against a panel whose rows carry server-authored labels and disabled reasons
- **THEN** every domain row's label, sub-line, action identifier, payload, and disabled reason equal the committed panel's values

#### Scenario: Required navigation rows are reproduced, not fabricated

- **WHEN** a resolved menu needs the client-owned navigation and presentation rows that the shipped dock contract requires — the exploration overview's footer entries, the presence rail's and the verb card's builder rows, the services/creation root entries, `back` rows of submenus, the combat forfeit confirm/cancel pair, and disabled explanatory rows
- **THEN** those rows are reproduced by the same builders, and reproducing them does not count as fabrication

### Requirement: Unresolvable frames pop one level; only the root frame renders a degraded reason row

When a declarative frame resolves to the unresolvable marker as the current frame, the stack SHALL immediately pop one level and the parent frame SHALL restore focus to the key of the row that opened the popped frame; when consecutive top frames are unresolvable the pop SHALL cascade until a frame resolves, and when no frame resolves the stack SHALL end at the mode's root frame.

#### Scenario: A vanished target pops back to its parent

- **WHEN** a frame bound to one server-authored subject (a combat skill frame bound to its skill key) is open and a committed snapshot no longer lists that subject
- **THEN** the stack pops exactly one level and the parent frame restores focus to the vanished subject's former row position by the nearest-row rule

#### Scenario: Cascading loss returns to the root

- **WHEN** a committed snapshot makes the top two frames' identities unresolvable at once
- **THEN** both frames pop in one access and the next lower resolvable frame renders with restored opener focus

#### Scenario: An unresolvable root degrades in place

- **WHEN** the exploration panel enters its unavailable form while the root frame is current
- **THEN** the root renders one disabled row naming the server-authored reason, focus lands on it, and activating it submits nothing

#### Scenario: Only the root frame renders the degraded row

- **WHEN** a frame is unresolvable and the question is who shows a reason
- **THEN** only when the root frame itself is unresolvable — with no parent to return to — does the client render a single degraded row; that row is focusable and submits nothing

#### Scenario: The pop cascade is synchronous and bounded

- **WHEN** unresolvable top frames force a pop cascade
- **THEN** the cascade is bounded by stack depth and completes without any timer, animation, or deferred check

#### Scenario: An unresolvable root without a server reason shows the fallback

- **WHEN** the root frame is unresolvable and the marker carries no server-authored reason
- **THEN** the single disabled row's text is the local fallback 「畫面狀態已更新，請返回上層」

#### Scenario: Exceptions reach the stack rules as unresolvable

- **WHEN** a resolution exception reaches the stack rules
- **THEN** it is indistinguishable from an unresolvable marker
