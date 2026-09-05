# Tasks: multichar-04-topbar-switcher-ui

## 1. The component

- [ ] 1.1 `web/webclient-app/components/CharacterSwitcher.vue`: props for the committed slice
  (`characters`, `canCreate`, `switchLocked`, `lockReason`, `locked` for the connection gate) and
  emits for the two dispatch intents. Renders nothing when the roster is unavailable.
- [ ] 1.2 Collapsed pill: the current row's portrait thumbnail and name, width-bounded with
  ellipsis truncation, styled to sit beside `.topbar-meta` in the `top:16px` band and never extend
  past `top:64px`.
- [ ] 1.3 Portrait thumbnail rendering reusing `ArtPanel.vue`'s existing treatment of the
  `{status, url, alt, placeholder}` shape — asset when a URL is present, the committed placeholder
  otherwise. Do not add a second portrait vocabulary.
- [ ] 1.4 Expanded list: one row per committed character in payload order; a stable 「建立中」
  marker on pending rows; the current row marked selected and non-activatable; bounded max-height
  with internal scrolling; absolutely positioned popover above the island z-index so the band's own
  box is unchanged; closes on Escape, on outside pointer activation, and on a committed epoch
  change.
- [ ] 1.5 Lock presentation: when `switchLocked`, disable every non-current row and render exactly
  one shared inline note carrying `lockReason` verbatim from the panel. No per-row badge, no
  client-composed reason string.
- [ ] 1.6 Create control: trailing 「＋ 新增角色」 row; disabled with the stable
  「角色數量已達上限」 reason when `!canCreate`; otherwise opens an inline two-step confirmation
  (an explicit line stating the current character will be left, a cancel control, a confirm
  control) following the Forfeit confirmation pattern. Only confirm emits; Escape and cancel emit
  nothing.
- [ ] 1.7 Keyboard parity: rows and controls are natively focusable and activate identically from
  keyboard and pointer; the connection/mutation lock disables every control.

## 2. Wiring

- [ ] 2.1 `TopBar.vue`: mount `CharacterSwitcher` in the top-right cluster, accept the roster props
  and re-emit the two intents; update the header comment's band inventory.
- [ ] 2.2 `AppShell.vue`: thread the roster props and the two events through to `TopBar`, alongside
  the existing `locationLabel` / `timeLabel` / `connected` props (both `TopBar` mount sites).
- [ ] 2.3 `AppClient.vue`: bind the store's roster computeds and route the two intents to
  `store.dispatchAction('account.character.switch', { character_id })` and
  `store.dispatchAction('account.character.create', {})`. No optimistic state, no local
  debouncing, no close-on-dispatch.

## 3. Showcase lockstep

- [ ] 3.1 `component-manifest.json`: add `Core/CharacterSwitcher` to `required` (44 → 45).
- [ ] 3.2 `stories/Core/CharacterSwitcher.stories.js`: deterministic offline stories for collapsed,
  expanded, combat-locked, capacity-reached, pending-sibling, long-name truncation, and
  disconnected.
- [ ] 3.3 `tests/overlays/deferred_surfaces_absent.test.js`: bump the required-manifest length to
  45 with the growth comment. Do **not** add the switcher to the deferred list — it is fully backed
  by the committed `roster` panel.

## 4. Tests

- [ ] 4.1 Vitest `tests/core/character_switcher.test.js`: nothing renders when the roster is
  unavailable; the collapsed pill reads the current row; rows render in payload order with the
  current one selected and non-activatable; the pending marker; the single shared lock note with
  no per-row badge; exactly one switch dispatch carrying the row's identity; no optimistic
  selection move before a commit; the create control opens a confirmation without dispatching and
  only confirm dispatches once; the capacity-disabled create control opens nothing; every control
  disabled when locked or disconnected; Escape closes one level and dispatches nothing.
- [ ] 4.2 Extend the existing top-band layout assertions to cover the three band elements at
  1440x900 and 1280x720 with a maximum-length committed name, and assert the band's rendered box is
  unchanged while the popover is open.
- [ ] 4.3 If a managed browser slice under `web/tests/browser/` is added that targets any new
  `data-testid`, add those hooks to §2.3 of
  `docs/development/webclient-vue-frozen-contract-audit.md` in the same change, because
  `tests/test_webclient_frozen_contract.py` requires every managed browser target to appear there.
  If no browser slice targets them, leave the audit untouched.
- [ ] 4.4 `covers_requirement` annotations for the four new `webclient-character-roster` UI
  requirements and the two modified requirements.

## 5. Verification

- [ ] 5.1 `npm test`, `npm run build-storybook`, and `npm run showcase-coverage`.
- [ ] 5.2 `uv run --locked python -m tools.spec_traceability check` and
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests`
  (the frozen-contract and command-docs repository checks).
- [ ] 5.3 Live container check with two characters on one account: the pill names the live
  character; the dropdown lists both; switching lands on the other character with a complete stage
  and no uncertain-result notice; entering combat greys the other rows with one note; filling the
  account greys the create row; creating from the confirmation lands in the creation wizard;
  abandoning that wizard and switching back to the finished character works, and switching to the
  abandoned shell resumes the wizard.
