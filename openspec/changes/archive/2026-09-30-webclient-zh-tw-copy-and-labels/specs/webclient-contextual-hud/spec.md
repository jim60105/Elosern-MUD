## ADDED Requirements

### Requirement: Client help and finite display vocabularies are localized

The client-owned help reference, the combat detail's skill target type and element, and the party
drawer's guidance SHALL read in Traditional Chinese rather than English prose or raw identifiers.
Literal key names (Enter, Esc, Tab, Space, Shift, PageUp, PageDown, Home, End, arrows, digits) and
literal command syntax (`help`) SHALL stay verbatim, rendered as key caps and code; protocol
identifiers, payloads and user-authored content SHALL NOT change.

The help reference SHALL group its rows by where the keys act (指令列, 指令面板, 閱讀與對話) and SHALL
name only bindings the client implements, including the ⌨ toggle and the dock's positional picks
1–9 (never a stale range). The help overlay's header subtitle SHALL describe its content (按鍵、指令列與閱讀操作),
never another surface's navigation.

A skill's `target_spec` SHALL be shown by the closed name set 無目標 / 自身 / 單一目標 / 範圍, and its
`element` by the element registry's own name followed by 屬性 (火屬性); an identifier outside either
set SHALL read 未知目標類型 or 未知屬性, never the raw key and never a guessed mechanic. The party
drawer's follow rules SHALL name affinity by the established term 羈絆.

#### Scenario: Help describes real keys
- **WHEN** the help overlay opens
- **THEN** it names only implemented bindings in localized prose, lists the ⌨ toggle and the 1–9
  positional picks, and preserves literal key and command syntax

#### Scenario: An unknown skill enum reads neutrally
- **WHEN** the combat detail pane shows a skill whose target type or element is outside the known sets
- **THEN** it reads 未知目標類型 or 未知屬性 and shows no raw identifier

## MODIFIED Requirements

### Requirement: Condition chips carry a severity glyph, a payload duration, and a bounded overflow
Each entry in `status.conditions` SHALL render as one chip pairing a per-severity shape glyph with the
condition's readable name — its label, or its code only when no label is supplied — shown whole or
ellipsised at the island width, never abbreviated to invented characters, and with an accessible name
carrying the condition's full label, its remaining duration when the payload supplies one, and every
derived modifier the payload provides. Each modifier SHALL be named in the game's stat vocabulary
(for example 攻擊, 敏捷, 防禦, 準度, 每回合行動, 魔力消耗) rather than by its raw adjustment key, with
its value verbatim — no sign, unit or digit added or dropped — and a key outside that vocabulary
SHALL be named by the neutral 其他修正 and keep its value. The five severities SHALL each map to a distinct
glyph shape, so two severities are never separated by colour alone, and the beneficial and harmful
directions SHALL be readable from the glyph itself. Because the chip may
ellipsise its name and carries no modifier text, the island SHALL also present the full label,
duration, and modifier text visibly when a chip is focused or hovered, so the information in its
accessible name stays reachable by pointer and by keyboard; the overflow surface names modifiers the
same way.

The duration SHALL render as a small secondary badge after the name, and only when the payload carries
`remaining_seconds` for that condition;
a condition without one SHALL render no badge and no substitute value. The badge SHALL show the
payload's integer verbatim and SHALL NOT be decremented, animated down, or otherwise advanced by the
client between committed revisions.

Visible chips SHALL be bounded, and the remainder SHALL be reachable in one action through an overflow
chip stating how many are hidden. The overflow surface SHALL be bounded and scrollable and SHALL close
on Escape, so no committed condition becomes unreachable at any condition count the payload permits.
An empty condition list SHALL render no condition island at all — no placeholder island, no
`無條件` text — consistent with the contextual-hiding rule that an absent surface is not a dimmed or
emptied surface.

#### Scenario: A chip carries its label, duration, and modifiers
- **WHEN** a condition with a label, a remaining duration, and a derived modifier is committed
- **THEN** its chip renders the severity glyph, the readable name, and a duration badge, and its accessible name states the label, the remaining duration, and the modifier's readable name with its verbatim value

#### Scenario: Two severities are distinguishable without colour
- **WHEN** a warning condition and a harmful condition are committed together
- **THEN** their chips carry different glyph shapes and remain distinguishable with colour removed

#### Scenario: A condition without a duration renders no badge
- **WHEN** a committed condition carries no `remaining_seconds`
- **THEN** its chip renders no duration badge and no substitute value in its place

#### Scenario: The duration does not tick between revisions
- **WHEN** a chip with a duration badge is displayed and no new revision commits
- **THEN** the badge continues to show the payload's value unchanged, and the client runs no countdown

#### Scenario: Overflowing conditions stay reachable
- **WHEN** more conditions are committed than the island shows as chips
- **THEN** an overflow chip states the hidden count and reveals every remaining condition in one action, within a bounded scrollable surface that closes on Escape

#### Scenario: No conditions renders no island
- **WHEN** the committed condition list is empty
- **THEN** no condition island is rendered anywhere in the HUD

#### Scenario: Long names stay bounded and complete
- **WHEN** six conditions with long labels and a seventh condition are committed
- **THEN** each of the six chips shows its own name, bounded by the island width without covering the
  vitals, its full label and localized modifiers remain in its accessible name and focus detail, and
  the overflow control reaches the seventh

#### Scenario: Unknown modifier keys keep their values
- **WHEN** a condition carries a known and an unknown modifier key
- **THEN** the known key is named in the stat vocabulary, the unknown key reads 其他修正, and both
  original values appear verbatim with their signs and units
