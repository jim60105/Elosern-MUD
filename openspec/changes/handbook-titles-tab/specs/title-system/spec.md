## MODIFIED Requirements

### Requirement: The codex OOB payload and WebClient window are server-authored
The `title` OOB schema v1 SHALL carry `{schema_version, fixed_rows, epithet_rows, equipped, full_title, unlocked, total, pending_ballot}` unchanged. The WebClient SHALL render it in the handbook's titles tab: the live full title, fixed titles by category, epithets and the pending ballot. Every intent SHALL be forwarded verbatim, and the client SHALL evaluate no gate rule.

#### Scenario: Locked cards offer no affordance
- **WHEN** the titles tab renders a row whose `unlocked` is false
- **THEN** the row shows its locked state and hint, and activating its equip control causes no state change and emits no intent

#### Scenario: The remove button follows the flag
- **WHEN** an epithet row carries `can_remove = false`
- **THEN** no 移除 control renders for it, and the client evaluates no gate logic itself

#### Scenario: The clergy tab renders and an unknown category is rejected
- **WHEN** a payload with 聖職-category rows reaches the panel, and separately a payload whose row category is outside the extended enum
- **THEN** the first renders under its rail entry with the ladder rows, and the client validator rejects the second rather than rendering it

#### Scenario: The 異名 block renders equip marks and server-driven removal
- **WHEN** the titles tab renders the epithet rail entry
- **THEN** each row can be equipped from the detail footer, the equipped epithet is marked, and the 移除 control renders from the row's server-computed `can_remove` flag with no client-side rules

#### Scenario: The 提名中 tab carries the ballot and there is no unequip control
- **WHEN** the titles tab renders G's pending ballot
- **THEN** the ballot rail entry presents it with the accept and decline controls, and no 卸裝 control exists anywhere in the tab

#### Scenario: The category enum stays mirrored across all its faces
- **WHEN** the title category enum is checked
- **THEN** the Python `TitleCategory`, the presentation mirror, the client `constants.js` validator enum, and its protocol test agree, and the panel validator rejects a payload carrying a category outside the extended closed set

#### Scenario: The preview tracks every equip
- **WHEN** an equip request succeeds
- **THEN** the live full-title preview updates
