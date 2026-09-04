# Delta spec: webclient-contextual-hud (webclient-align-05-party-hud)

## ADDED Requirements

### Requirement: The party quickbar island presents the committed party only
The left HUD SHALL carry a party island while the committed `party` panel is available in
exploration or combat mode, and SHALL render no party island when the panel is unavailable or the
committed mode is creation. The island's header SHALL read `同伴` with the slot count as
`N / 4`, where `N` equals the committed slot count. Each row of `party.slots` SHALL render one
cell carrying: the companion's display name; an avatar showing the bound portrait only when the
row's `portrait_ref` resolves through the client's art catalog, otherwise the display name's
initial letter in the reference's gold display face; an HP hairline bar whose fill ratio is
`hp_current / hp_maximum`; and a state row carrying the HP numerals and the row's bond stage
name. When the committed combat panel's participant rows carry a row with the same `identity`,
the state row SHALL additionally prefix the joined participant's session token (e.g. `a2`); a
companion not fighting SHALL show no token. The slot row SHALL be padded with dashed
`+ 邀請` cells — one per missing companion up to four — and an empty party SHALL render a row
of four dashed invite cells. Activating the island or any cell SHALL open the 同伴 · 隊伍
drawer and SHALL NOT dispatch any action. The island SHALL present no affinity numeral, no
companion trait the panel does not carry, and no estimate.

#### Scenario: The quickbar mirrors the committed party
- **WHEN** a snapshot commits two party slots with HP 180/220 and 144/160 and bond stages 親睦
  and 信賴
- **THEN** the island reads `同伴 2 / 4` and renders both cells with their HP bars, numerals, and
  stage names, plus two dashed invite cells, and no numeric affinity appears

#### Scenario: The combat token is joined by identity
- **WHEN** the committed combat panel carries a participant row whose `identity` equals a party
  slot's `identity` with token `a2`
- **THEN** that companion's state row shows the `a2` prefix, and a party row with no matching
  participant shows no token

#### Scenario: No portrait falls back to the initial letter
- **WHEN** a party row carries `portrait_ref: null` for display name `蕾娜`
- **THEN** the avatar renders the gold initial `蕾`, not an invented image

#### Scenario: An unavailable party panel hides the island
- **WHEN** the committed `party` panel switches to the unavailable form
- **THEN** no party island is rendered anywhere in the HUD (not an emptied or dimmed island)

#### Scenario: The quickbar opens the drawer without mutating
- **WHEN** the player activates a party cell
- **THEN** the 同伴 · 隊伍 drawer opens and no `ui_action` or text command is sent

### Requirement: The party drawer presents compbig rows and the fixed follow rules
The 同伴 · 隊伍 drawer SHALL render on the shared right-anchored drawer contract with the sub-count
`N / 4`, one compbig row per committed party slot (initial-letter/gold avatar with the same
portrait fallback, display name, bond stage line, HP bar with numerals, the joined 參戰 token
when the companion fights, and a 請其離隊 control), and one 空位 row stating the invite rule in
stage-name words — the raw affinity threshold number SHALL NOT be shown. The 空位 row's
`邀請當前 NPC…` control SHALL dispatch `explore.party_invite` with the exact existing payload
`{npc_id: <the committed invite-capable interact target's identity>, message: ""}` — the fixed
empty message, since the drawer invents no freeform invitation input — under the existing
dispatch and confirmation contract, enabled only when the committed exploration context names
an invite-capable interact target, and SHALL be disabled with its rule line as the reason
otherwise — it SHALL never fabricate a target. Activating 請其離隊 SHALL dispatch `explore.party_leave` for that identity
under the same contract. The drawer SHALL close the party section with three fixed follow-rule
statements matching the reference draft verbatim, and SHALL render no companion detail control
that has no backing read model.

#### Scenario: Rows follow the committed party
- **WHEN** the drawer is open and a party mutation commits a third companion
- **THEN** a third compbig row appears with its committed fields and the sub-count reads `3 / 4`

#### Scenario: Leaving dispatches through the confirmation contract
- **WHEN** the player activates 請其離隊 on a companion row
- **THEN** the existing confirmation flow submits `explore.party_leave` for that identity and the
  row disappears only when the corresponding commit lands

#### Scenario: The invite control is honest about its preconditions
- **WHEN** the exploration context carries no invite-capable interact target
- **THEN** 邀請當前 NPC… is disabled with the stated rule as its reason and dispatches nothing,
  and the raw invite threshold number is never shown

#### Scenario: The follow rules are the reference's three lines
- **WHEN** the drawer body is enumerated
- **THEN** the 跟隨規則 card carries the reference draft's three fixed statements and no invented
  rules
