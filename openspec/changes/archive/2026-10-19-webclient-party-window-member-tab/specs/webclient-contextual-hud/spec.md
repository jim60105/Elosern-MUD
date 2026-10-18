# Spec Delta

## REMOVED Requirements

### Requirement: The party drawer presents compbig rows and the fixed follow rules
**Reason**: `PartyDrawer` is deleted and design §3.4 bans rule prose from windows; the follow rules move to the help overlay (`party-management-acceptance`).
**Migration**: See `webclient-party-window` (rail and 成員 tab) and the help-overlay party rules requirement.

## MODIFIED Requirements

### Requirement: Client help and finite display vocabularies are localized

The client-owned help reference (including its party guidance), the combat detail's skill target type and element, and the party window's labels SHALL read in Traditional Chinese rather than English prose or raw identifiers.

#### Scenario: Literal keys and syntax stay verbatim
- **WHEN** localized content renders literal key names or command syntax
- **THEN** key names (Enter, Esc, Tab, Space, Shift, PageUp, PageDown, Home, End, arrows, digits) and command syntax (`help`) stay verbatim, rendered as key caps and code, and protocol identifiers, payloads and user-authored content do not change

#### Scenario: The help reference groups real bindings under a truthful subtitle
- **WHEN** the help reference renders
- **THEN** its rows are grouped by where the keys act (指令列, 指令面板, 閱讀與對話), it names only bindings the client implements — including the ⌨ toggle and the dock's positional picks 1–9 (never a stale range) — and the overlay's header subtitle describes its content (按鍵、指令列與閱讀操作), never another surface's navigation

#### Scenario: Closed sets name skills; unknowns read neutrally
- **WHEN** a skill's `target_spec` or `element` renders, or an identifier falls outside either set
- **THEN** `target_spec` shows by the closed name set 無目標 / 自身 / 單一目標 / 範圍, `element` by the element registry's own name followed by 屬性 (火屬性), and an outside identifier reads 未知目標類型 or 未知屬性, never the raw key and never a guessed mechanic

#### Scenario: The party drawer uses the established term
- **WHEN** party guidance or the party window names affinity
- **THEN** it uses the established term 羈絆

#### Scenario: Help describes real keys
- **WHEN** the help overlay opens
- **THEN** it names only implemented bindings in localized prose, lists the ⌨ toggle and the 1–9
  positional picks, and preserves literal key and command syntax

#### Scenario: An unknown skill enum reads neutrally
- **WHEN** the combat detail pane shows a skill whose target type or element is outside the known sets
- **THEN** it reads 未知目標類型 or 未知屬性 and shows no raw identifier
