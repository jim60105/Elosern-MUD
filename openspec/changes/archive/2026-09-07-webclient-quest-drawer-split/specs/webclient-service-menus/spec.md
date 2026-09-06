# Delta spec: webclient-service-menus (webclient-quest-drawer-split)

## ADDED Requirements

### Requirement: The quest drawer separates the player's quest book from the guild counter

The quest drawer SHALL render two distinct surfaces. The quest book SHALL render from the
`quest_log` panel and SHALL be present whenever that panel is available, regardless of any local
service host. The guild counter SHALL render from the `services` panel's `guild` section and SHALL be
present only when that section is available. Each surface SHALL be its own component reading its own
panel; neither SHALL read the other's panel for its own content.

The quest book SHALL list every stored record. The guild counter SHALL carry registration, the quest
board for accepting new quests, and guild rank with the promotion examination, and SHALL NOT re-list
the holder's accepted quest records, so no quest is presented twice in one drawer.

#### Scenario: The quest book renders away from any clerk
- **WHEN** a holder with stored records opens the quest drawer in a room with no guild staff
- **THEN** the quest book lists every record and the guild counter is absent, replaced by an explicit
  marker stating the counter needs a clerk

#### Scenario: Both surfaces render in front of a clerk
- **WHEN** the same holder opens the drawer in front of a guild clerk
- **THEN** the quest book lists every record and the guild counter additionally renders registration,
  the board, and rank

#### Scenario: A quest is never listed twice
- **WHEN** the drawer renders with the guild section available and the holder holding active quests
- **THEN** each accepted quest appears exactly once, in the quest book, and the counter lists none of
  them

#### Scenario: Neither surface invents the other's data
- **WHEN** one panel is available and the other is not
- **THEN** the available surface renders normally and the unavailable one renders its honest absent
  marker with no fabricated rows

### Requirement: Counter-only quest actions appear on a book row only when the counter offers them

Abandon and turn-in SHALL be rendered on a quest book row only when the `services` panel's guild
section carries a quest row with the same `quest_id` and that action is enabled there. Matching by
`quest_id` SHALL be the only join between the two panels. Tracking SHALL be rendered from the
`quest_log` row's own descriptor and SHALL be available regardless of any host, because
`guild.quest_track` is host-independent by contract. The book SHALL NOT synthesize an abandon or
turn-in descriptor, and SHALL NOT enable one whose counter-side descriptor is disabled.

#### Scenario: Away from a clerk only tracking is offered
- **WHEN** the quest book renders with no guild section available
- **THEN** each in-progress row offers tracking, and no row offers abandon or turn-in

#### Scenario: At the counter the row gains its counter actions
- **WHEN** the same rows render with the guild section available
- **THEN** an in-progress row additionally offers abandon and a completed unclaimed row additionally
  offers turn-in, each dispatching the counter-side descriptor's exact action and payload

#### Scenario: A disabled counter action is not enabled by the book
- **WHEN** the counter-side turn-in descriptor is disabled with an already-claimed reason
- **THEN** the book row renders that disabled state and its reason rather than an enabled control

#### Scenario: A book row with no counter-side match offers no counter actions
- **WHEN** a private commission's row renders while a guild clerk is present
- **THEN** it offers tracking only, because the guild section carries no row with that quest ID

### Requirement: The quest book discloses each quest's commissioner and settlement

Each quest book row SHALL render the issuer label from its `quest_log` row and SHALL indicate whether
the quest settles at a counter or on completion, so a player can tell a guild commission from a
private one and knows whether a return trip is required. The row SHALL render the reward line when
the panel carries one and SHALL render nothing in its place when the panel carries `null`.

#### Scenario: A guild quest shows its counter requirement
- **WHEN** a row whose settlement is `counter` renders
- **THEN** it shows the issuing guild label and indicates the reward is claimed at the counter

#### Scenario: A private commission shows automatic settlement
- **WHEN** a row whose settlement is `auto` renders
- **THEN** it shows the commissioner's label and indicates the reward settles on completion

#### Scenario: A missing reward line renders nothing rather than a placeholder
- **WHEN** a row's `reward_line` is `null`
- **THEN** no reward text and no placeholder appears on that row

## MODIFIED Requirements

### Requirement: The quest browser exposes the tracking toggle
The quest book SHALL render, on each quest row, a tracking control that dispatches
`guild.quest_track` for that row's `quest_id`: labelled and enabled as tracking for an
`in_progress` row whose `tracked` is false, as untracking for a row whose `tracked` is true, and
disabled with a stable reason otherwise. The control SHALL be present regardless of any local
service host, because tracking is host-independent by contract.
Keyboard and pointer activation SHALL submit the same
action identifier and payload through the same dispatch entry and gates. The control SHALL render
only from the committed row's `tracked` field, and the row's presented tracking state SHALL
change only when a commit carrying the new field lands.

#### Scenario: Tracking from the browser dispatches once
- **WHEN** the player activates a tracked-false active quest row's tracking control
- **THEN** exactly one `guild.quest_track` request with `{quest_id, tracked: true}` is submitted and the row flips only on the commit

#### Scenario: Completed rows offer no tracking
- **WHEN** a completed quest row renders
- **THEN** its tracking control is disabled with a stable reason and dispatches nothing

#### Scenario: Tracking works with no clerk present
- **WHEN** the player activates the tracking control on a row while standing away from any guild
  staff
- **THEN** exactly one `guild.quest_track` request is submitted and the row flips on the commit
