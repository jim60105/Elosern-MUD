## ADDED Requirements

### Requirement: Codex entry titles are the registry's display names

Each entry's `title` SHALL be the `display_name_zh` of its card, which every category declares as its
first card field, so a race entry is titled by its race name (人類, never `human`) and a guild rank
entry by its rank name (`F 級`). The entry `key` SHALL stay the opaque registry key. The payload
schema is unchanged.

#### Scenario: A race entry is titled by its display name
- **WHEN** a holder who discovered a race receives the panel
- **THEN** that entry's `title` equals the race's registry `display_name_zh`, its `key` is the opaque
  race key, and the key appears in no visible field value

## MODIFIED Requirements

### Requirement: The codex drawer renders the panel in two navigation levels

The codex drawer SHALL render only the committed `lore_codex` panel. It SHALL present a category
strip carrying one control per shipped category plus an aggregate control covering every discovered
entry, an entry list for the selected category, and the selected entry's card. Navigation between
these levels SHALL be local to the client: selecting a category or an entry SHALL dispatch no action
and SHALL trigger no fetch, because the panel already carries every discovered entry and its rendered
card.

The card SHALL render the panel's card fields in the order the panel supplies them, with no field
added, reordered, or truncated by the drawer and every field value verbatim. Each field SHALL be
named by the drawer's closed readable vocabulary for the declared card fields (名稱, 描述, 首都,
地貌, 例證), never by its raw field identifier, which stays only a non-visible hook; a field outside
that vocabulary SHALL be named by the neutral 資料 and keep its value.

#### Scenario: Selecting a category filters locally
- **WHEN** the player selects a category control
- **THEN** the entry list shows exactly that category's entries and no request is dispatched

#### Scenario: Selecting an entry shows its card
- **WHEN** the player selects an entry
- **THEN** its card renders exactly the panel's field list in the panel's order, each value verbatim
  under its readable field name and no raw field identifier visible, and no request is dispatched

#### Scenario: The aggregate control shows everything discovered
- **WHEN** the player selects the aggregate control
- **THEN** every discovered entry across every category is listed
