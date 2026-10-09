## ADDED Requirements

### Requirement: The guild board is organized by difficulty grade tabs

For a registered holder, the guild counter tab SHALL offer one vertical icon tab per key of the guild section's
`rank_ladder`, in ladder order, each showing that grade's seal, listing only that grade's board offers, and
showing its offer count. Grades above the holder's rank SHALL be marked locked, grades with no offers SHALL be
dimmed, and the holder's own grade SHALL be marked. The client SHALL derive no grade order or rank rule of its
own.

#### Scenario: Every grade has a fixed tab
- **WHEN** the counter tab renders for a registered E-rank holder with a seven-key ladder
- **THEN** seven grade tabs render in ladder order, and their positions never depend on which grades currently have offers

#### Scenario: A grade tab lists only its offers
- **WHEN** the player selects the F tab while the board holds two F and two E offers
- **THEN** only the two F offers are listed

#### Scenario: The default grade has work
- **WHEN** the counter tab is first shown for an E-rank holder whose board has F offers but no E offers
- **THEN** the F tab is selected, and when no grade at or below E has offers, the E tab is selected

#### Scenario: Grades above the holder's rank are locked
- **WHEN** an E-rank holder views the D tab
- **THEN** the D tab carries the locked mark and its list states that this grade opens after a promotion, with no rows

#### Scenario: A locked grade never implies hidden offers
- **WHEN** a locked grade tab is selected
- **THEN** no offer row, offer detail, or accept action renders, and the tab shows no offer count

#### Scenario: An eligible empty grade says so
- **WHEN** an E-rank holder views an E tab with no offers
- **THEN** the tab is dimmed and its list states that no offers of that grade are posted

#### Scenario: The holder's own grade is marked and named
- **WHEN** the grade tabs render
- **THEN** the holder's own grade carries the own-grade mark, and its tooltip names it as the holder's rank

### Requirement: The counter tab shows the rank card above the board

For a registered holder, the guild counter tab SHALL render the guild rank card, unchanged in content and
behavior, at the top of the board list column whenever the guild section carries a `rank` object, and the promotion examination request
SHALL keep dispatching exactly as before.

#### Scenario: Rank above the board
- **WHEN** a registered holder opens the counter tab in front of an examination counter
- **THEN** the rank card renders above the grade's offer list with its merit meter and examination request

#### Scenario: The examination request is unchanged
- **WHEN** the player activates an enabled examination request in the counter tab
- **THEN** exactly one `guild.exam_request` with the next-rank payload is submitted

### Requirement: Selecting a board offer shows its detail and the accept action

Selecting an offer SHALL show the same detail layout as a quest: the category, name, objective line and note,
grade, an acceptance condition naming the grade, the deadline or 無期限, `branch_label` as the commissioner with
the flavor prose, and the reward with counter settlement. The action bar SHALL render the offer's `accept`
descriptor as the primary action, and when it is disabled SHALL show its reason instead of an enabled control.

#### Scenario: An offer shows what accepting commits to
- **WHEN** the player selects an F offer with a 72-hour deadline and an item reward
- **THEN** the detail shows its objective and note, 接取後 3 日, the branch label, its flavor, and the item with quantity

#### Scenario: Accepting dispatches the descriptor once
- **WHEN** the player activates the enabled accept action on a selected offer
- **THEN** exactly one request with the descriptor's action and `{definition_key}` payload is submitted

#### Scenario: A disabled accept shows its reason
- **WHEN** the selected offer's accept descriptor is disabled because the quest is already active
- **THEN** the action bar shows the descriptor's reason and no enabled accept control

#### Scenario: An accepted offer appears in the book once
- **WHEN** an acceptance commits
- **THEN** the new quest appears in the quest book's in-progress tab and is not listed anywhere in the counter tab as a held quest

### Requirement: An unregistered holder sees registration instead of the board

When the guild section reports the holder as unregistered, the guild counter tab SHALL render no grade tabs
and no board. It SHALL instead render a registration card carrying the `registration.register` descriptor as its
primary action, or that descriptor's disabled reason.

#### Scenario: Registration replaces the board
- **WHEN** an unregistered holder opens the counter tab in front of a clerk
- **THEN** a registration card with the register action renders, and no grade tab, board row, or rank card renders

#### Scenario: Registering dispatches once
- **WHEN** the player activates the enabled register action
- **THEN** exactly one `guild.register` request is submitted, and the board with grade tabs appears only after the commit
