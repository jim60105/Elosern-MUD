## ADDED Requirements

### Requirement: Player-facing text names the reserve 精力
Every player-facing surface that names a body's mental reserve SHALL call it 精力: the status panel's fatigue row, the travel refusal for predicted pre-destination depletion, the sleep-handoff candidate label shared by the text and browser clients, and the player command documentation. No player-facing text SHALL use 精神儲備. Fatigue stage labels SHALL stay unchanged.

#### Scenario: The status row names 精力
- **WHEN** the status panel renders a fatigue row for 艾倫 at 80% with the stage label 精神充沛
- **THEN** the row reads `艾倫：精力 80%（精神充沛）` and does not contain 精神儲備

#### Scenario: The travel refusal names 精力
- **WHEN** a departure is refused because a present traveller is predicted to exhaust the reserve before the destination
- **THEN** the refusal message is exactly `隊伍成員的精力不足以支撐這趟旅行。`

#### Scenario: The handoff candidates name 精力
- **WHEN** the sleep-handoff list offers the return to the owner's body at 100% and an awake companion 清醒同伴 at 100%
- **THEN** the labels read `回到自己的身體（精力 100%）` and `接手 清醒同伴（精力 100%）` in both the text listing and the browser roster

#### Scenario: Stage labels are unchanged
- **WHEN** a body is at any fatigue stage
- **THEN** its stage label is still one of 精神充沛, 輕度疲勞, 中度疲勞, 重度疲勞, 強制睡眠, or 沉睡

#### Scenario: The player docs use 精力
- **WHEN** `docs/game/commands.md` and `docs/game/command-reference.md` are searched for 精神儲備
- **THEN** there is no match, and the `狀態` entry's 說明 names 精力 together with 疲勞階段 and 無法行動
