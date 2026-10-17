## ADDED Requirements

### Requirement: A cast across sides asks for confirmation first
Aiming a hostile skill at the player's own side, or a beneficial skill at the opposing side, SHALL stay allowed, and the client SHALL ask once for confirmation before sending it. The trigger SHALL use only the version-6 descriptor's `hostile` and `beneficial` facts and the chosen targets' committed `team`; the payload and server validation SHALL stay unchanged.

#### Scenario: The trigger is a static predicate
- **WHEN** the client evaluates a submission
- **THEN** it is cross-side exactly when `hostile` is true and the target set contains a `party` participant (the actor's side, the actor included), or `beneficial` is true and it contains a `foes` participant; no damage or healing amount, formula or prediction takes part

#### Scenario: The target set of each form
- **WHEN** the client evaluates a submission
- **THEN** the target set is the focused candidate for SINGLE, the actor for SELF, the explicit selection for AREA, every candidate of the shorthand's side for an AREA shorthand (`all-enemies` → `foes`, `all-allies` → `party`, `all` → both), and empty for NONE; Attack (`basic_attack`) is a SINGLE skill whose descriptor carries `hostile: true`

#### Scenario: A harmful skill aimed at an ally asks first
- **WHEN** the player confirms Attack on a companion in the stage target step, by Enter, by its digit, and by a pointer click on its figure
- **THEN** no `combat.cast` is sent; a question card reading `確定要對友方使用〈基本攻擊〉？` opens centred in the stage's `choices` anchor with the focus on its safe answer 否; activating 是 sends exactly one `combat.cast` byte-identical to the payload the same choice sends without the question

#### Scenario: A harmful skill aimed at the actor asks first
- **WHEN** the player confirms a hostile SELF skill, and a hostile SINGLE skill (a debuff, a drain or a sexual stimulus) on the controlled figure
- **THEN** a question card reading `確定要對自己使用〈<skill label>〉？` opens before anything is sent

#### Scenario: A restorative skill aimed at a foe asks first
- **WHEN** the player confirms a healing skill, and separately a skill applying a buff-polarity buff, on a foe
- **THEN** a question card reading `確定要對敵方使用〈<skill label>〉？` opens before anything is sent

#### Scenario: A group or selection asks once if any member is cross-side
- **WHEN** the player confirms a hostile AREA skill with one foe and one companion selected, the same skill with `all`, the same skill with `all-enemies`, and a beneficial AREA skill with `all-allies`
- **THEN** the first two open one question naming 友方, and the last two send at once with no question

#### Scenario: A skill that both harms and restores applies each fact to its side
- **WHEN** the player confirms a skill carrying `hostile: true` and `beneficial: true` on a foe, on a companion, and with `all`
- **THEN** the first asks naming 敵方, the second naming 友方, and the third once naming 友方與敵方

#### Scenario: Same-side use never asks
- **WHEN** the player confirms Attack on a foe, a healing skill on a companion, a skill whose descriptor carries `hostile: false` and `beneficial: false` (movement only) on a foe, a buff skill on a companion, a debuff skill on a foe, a NONE skill, Flee, and the Forfeit confirmation
- **THEN** each sends exactly as before with no question card

#### Scenario: Cancelling returns to the target step
- **WHEN** the question card is open and the player activates 否, activates its close control, or presses Escape
- **THEN** nothing is sent, the card closes, the stage target step is current again with the same focused position, the same selection, the same dim and markers, and DOM focus returns to `#action-dock`; one later Escape pops the target frame as before

#### Scenario: The question keeps the stage and the keys consistent
- **WHEN** the question card is open
- **THEN** the stage keeps the target step's dim, lit set and markers unchanged, the collapsed command card is inert beneath the question card, no dock key (arrows, digits, Enter, Space) moves or activates the target step, no pointer on a figure's hit area or a prompt chip focuses, moves or sends anything (the hit areas and chips take no pointer while the question is open), and the question card traps focus among its controls as the room cards' question does

#### Scenario: The question is accessible
- **WHEN** the question card opens
- **THEN** it is a modal dialog labelled by its question text, so assistive technology announces `確定要對友方使用〈基本攻擊〉？`, and its first focused control is 否

#### Scenario: A change under the question cancels it
- **WHEN** the question card is open and a committed `context_actions` replacement removes or disables the pending skill or drops one of its chosen targets (or the chosen shorthand) from the candidates, a combat round starts playing, or the committed mode leaves combat
- **THEN** the question card closes without sending and DOM focus goes to the mode's focus home (`#action-dock` in combat), never the document body; on a replacement the target step returns with the existing selection repair; a replacement that leaves the pending skill, its targets and its shorthand valid keeps the question open; the server's validation still decides every sent cast

#### Scenario: Confirming returns focus to the dock
- **WHEN** the player activates 是
- **THEN** exactly one cast is sent, the question card closes, and DOM focus is on `#action-dock`, never the document body

#### Scenario: An unresolvable target fails closed
- **WHEN** a hostile or beneficial submission names a target identity that no committed participant row carries
- **THEN** the client asks with the question naming 友方與敵方 instead of sending at once

#### Scenario: A locked submission waits
- **WHEN** a mutation is in flight while the question card is open
- **THEN** 是 is disabled with the stated reason, 否 and the close control still work, and nothing is sent until the lock releases and the player activates 是
