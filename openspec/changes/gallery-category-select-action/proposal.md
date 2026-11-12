# Proposal: register the gallery category selection action

## Batch:

Gallery window programme, stage 1 (design D6 "Switching category is a server
round trip").

- depends-on: gallery-v4-presenter
- conflict: `web/webclient/actions/gallery_actions.py` and
  `web/webclient/actions/registry.py` are edited later by `gallery-v4-cutover`,
  `gallery-mutation-admission` and `gallery-people-category`. The
  `webclient-action-dispatch` registry requirement is modified again by
  `gallery-people-category` (adds `gallery.group.select`); land this first.

## Why

The window switches category through one server round trip,
`gallery.category.select {category}`. Registering the action before the wire
cutover keeps the cutover change inside one working day. Until the cutover the
action only writes the v4 selection store, which the registered v3 panel does
not read, so it has no visible effect and no risk.

## What Changes

- New adapter `gallery.category.select` in
  `web/webclient/actions/gallery_actions.py` over
  `gallery_selection.select_gallery_category`, with an exact payload validator
  (`{category}` from the five keys), the uniform three-panel publication and
  one `gallery_action` event.
- Registered in `web/webclient/actions/registry.py`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-management-actions`: adds the category selection action.
- `webclient-action-dispatch`: the production registry enumeration includes
  `gallery.category.select`.

## Impact

- Code: `web/webclient/actions/gallery_actions.py`,
  `web/webclient/actions/registry.py`, and the silent entry in
  `web/static/webclient/js/elosern/command_echo.js`.
- Tests: the gallery action test module and the registry enumeration test
  (`rg -ln "party.view_member" web/webclient/actions/tests`), plus the
  command-echo coverage manifest and its Node and Vitest tables.
- Estimate: 3 hours (adapter and validator 1 h, tests 1.5 h, spec and gates
  0.5 h).
