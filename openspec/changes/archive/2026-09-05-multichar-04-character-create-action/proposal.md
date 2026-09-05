## Why

`multichar-03-character-switch-action` built the account-scoped write path and the verified,
recoverable puppet-transition helper, but it can only move between characters that already exist.
An account below its capacity still has no way to make a second character from the graphical
client — the only entry points are the Developer-locked `charcreate` and the account's one
auto-created shell at registration.

This change adds the second caller to the machinery change 03 built.

## What Changes

- Add `account.character.create` (empty payload) to `web/webclient/actions/account_actions.py` and
  the production action registry, following change 03's decide-synchronously /
  transition-later contract exactly.
- **Create the new shell before leaving the current character.** Evennia's `create_character`
  performs its own slot check and returns `(None, [error])` rather than raising, so attempting it
  first means a capacity failure costs nothing: the session never detaches and never needs the
  recovery ladder. Only once a shell exists does the transition attach it through change 03's
  verified `_attach_puppet`.
- Reject `character_slots_full` and `in_combat` synchronously at admission — creating a character
  leaves the current one, so the combat lock applies exactly as it does to switching.
- Deliver the reusable creation start presentation for the new shell. The world introduction is
  never resent: after `multichar-01` it is bound to the login hook, which a mid-session puppet
  change does not run, so this is structurally guaranteed rather than merely avoided.
- Extend the WebSocket integration test with the full end-to-end scenario: create a second
  character, complete its wizard, switch back, switch forward — asserting a complete snapshot for
  the correct puppet after each transition and that no request is left without a result.

## Capabilities

### New Capabilities

None. The action extends `webclient-character-roster`, introduced by `multichar-02`.

### Modified Capabilities

- `webclient-character-roster`: gains `account.character.create`, its rejection codes, its
  create-before-detach ordering, and the guarantee that the world introduction is never resent for
  a second or later character.

## Impact

- Modified: `web/webclient/actions/account_actions.py` (one validator, one adapter, one transition
  function reusing change 03's `_attach_puppet` / `_recover_transition`),
  `web/webclient/actions/registry.py` (one registration plus the docstring inventory),
  `web/webclient/actions/tests/test_account_actions.py`,
  `server/conf/tests/test_ui_action_integration.py`.
- Reuses unchanged: `Account.create_character`, `at_post_create_character`,
  `creation_start_screen`, `synchronize_session`, and the whole existing creation wizard.
- Depends on `multichar-03-character-switch-action` (the clock seam, `_attach_puppet`, and the
  recovery ladder) and, through it, on `multichar-01-account-capacity`. Its integration test also
  asserts on the `roster` panel, so it is fully verifiable only once
  `multichar-02-roster-read-model` has landed.
- Unblocks `multichar-05-topbar-switcher-ui`'s create control.
- No client-side change.
