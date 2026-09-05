## Why

After `multichar-02` the browser holds a committed roster and after `multichar-03`/`multichar-04` it can act on
it, but nothing renders either. The account's other characters are reachable only by typing
`進入世界 <角色>` into the command line, which is precisely the Telnet affordance the graphical
client exists to replace.

## What Changes

- Add `web/webclient-app/components/CharacterSwitcher.vue`, mounted in `TopBar.vue`'s top-right
  cluster beside the existing meta pill, within the stage's top band and above the HUD island
  anchors.
- Collapsed state: the current character's portrait thumbnail and name, both read from the
  committed roster's current row so the pill and the dropdown can never disagree.
- Expanded state: one row per roster character in payload order — portrait thumbnail, name, a
  pending marker for a character still in creation — with the current row marked as selected and
  not activatable, and a trailing 「＋ 新增角色」 row.
- Lock presentation: when the committed roster reports switching as blocked, every non-current row
  renders disabled under **one** shared inline note carrying the panel's own reason string, never
  a per-row badge. When the account is at capacity, the create row renders disabled with its own
  stable reason.
- Creating a character is confirmation-gated: the create row opens an explicit two-step
  confirmation naming what will happen (you leave your current character), and only the confirm
  control dispatches `account.character.create`. Switching is a single activation — it is
  reversible and already combat-locked server-side.
- Keyboard and pointer parity, Escape closes exactly one level, and every control follows the
  existing connection-loss lock.
- Showcase lockstep: register `CharacterSwitcher` in the frozen component manifest and add a
  Storybook story with deterministic offline fixtures covering collapsed, expanded, combat-locked,
  capacity-reached, pending-sibling, and disconnected states.

## Capabilities

### New Capabilities

None. The surface extends `webclient-character-roster`, introduced by `multichar-02`.

### Modified Capabilities

- `webclient-character-roster`: gains the top-band switcher surface — what it renders from the
  committed panel, how the lock and capacity reasons are presented, and the confirmation gate on
  creation.
- `webclient-contextual-hud`: the stage's top band gains a third element, so the requirement that
  no anchor's rendered box intersects another's is restated to cover it at the minimum viewport.
- `webclient-component-showcase`: the frozen required-component manifest grows by the switcher.

## Impact

- New: `web/webclient-app/components/CharacterSwitcher.vue`,
  `web/webclient-app/stories/Core/CharacterSwitcher.stories.js`, and
  `web/webclient-app/tests/` coverage for it.
- Modified: `web/webclient-app/components/TopBar.vue`,
  `web/webclient-app/components/AppShell.vue`, `web/webclient-app/AppClient.vue`,
  `web/webclient-app/component-manifest.json`.
- Depends on `multichar-02-roster-read-model` (the store slice it binds to),
  `multichar-03-character-switch-action` (the switch it dispatches), and
  `multichar-04-character-create-action` (the creation it dispatches). It is the last change in the
  chain and is pure client work.
- No server change. No new panel, action, or protocol envelope.
