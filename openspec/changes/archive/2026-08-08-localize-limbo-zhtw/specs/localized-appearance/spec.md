## ADDED Requirements

### Requirement: The shared appearance layer renders Traditional Chinese frames

The object-appearance layer SHALL render its presentation frames in Traditional Chinese for every
entry path: the text look command (localized 「看」), the character's `at_look` hook, and the
webclient `explore.look` action SHALL all produce the same zh-tw appearance. The room frame SHALL
label its exits as 「出口」 (never `Exits:`), its contents/characters sections with zh-tw headers
(never `Characters:` or `You see`), and the default description of an un-described object SHALL be
zh-tw (never `You see nothing special.`). No English frame string SHALL appear in the appearance
of a room or object.

#### Scenario: The text look command shows a zh-tw frame

- **WHEN** a player uses the localized 看 command in a room with an exit
- **THEN** the output shows the room's zh-tw name and description, a 「出口」 line listing the exit
  names, and no `Exits:` or other English frame string

#### Scenario: The webclient look action shows the same zh-tw frame

- **WHEN** a webclient player triggers the explore-look action in the same room
- **THEN** the appearance equals the text 看 output — zh-tw name, description, and 「出口」 line —
  with no English frame string

#### Scenario: The at_look seam stays intact

- **WHEN** a player looks while the onboarding arrival beat is active
- **THEN** the look still flows through the character's `at_look` hook (the look beat completes as
  before) and the presented appearance is the zh-tw frame
