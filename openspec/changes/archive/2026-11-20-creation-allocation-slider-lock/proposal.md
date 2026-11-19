# Proposal

## Batch: single change

- depends-on: none (no other active change exists at proposal time)
- conflicts: none known; touches only the WebClient custom-creation allocation step

## Why

The custom-creation allocation step only offers a number box with steppers, shows point ranges with a dash (`0–8`), and keeps the custom elf's zero-cap axes (point range `0~0`) looking editable, so players cannot tell which stats accept points.

## What Changes

- Render every allocation point range in the custom form (axis help line, budget briefing, out-of-cap error) through one formatter that joins the bounds with `~`.
- Add a range slider to each allocation axis next to the existing number box. Both bind the same form value, so they stay in sync. The slider is bounded by `0` and the server `point_cap`; like the number box, it does not clamp to the remaining budget.
- Disable the number box, slider and both steppers of an axis whose `point_cap` is `0` while its value is `0`, and mute the row with the existing ink/paper theme tokens. A user-driven race or subrace change zeroes the allocations of the new profile's zero-cap axes so they lock at once. A stale non-zero value on a zero-cap axis keeps the controls enabled so the player can clear it.
- Non-goals: the keyboard dock menu (`web/static/webclient/js/elosern/creation_menu.js`), the text creation wizard, the server policy, the protocol, and the budget rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: the requirement "Creation controls preserve native entry and existing authority" adds a slider kept in sync with each axis, tilde point ranges, and locked zero-cap axes.

## Impact

- `web/webclient-app/components/CreationCustomSteps.vue`, `web/webclient-app/components/creation-custom-steps.css`, `web/webclient-app/composables/use-creation-custom.js`.
- Vitest: `web/webclient-app/tests/overlays/creation_overlay.test.js`, `web/webclient-app/tests/overlays/creation_steps.test.js`.
- Browser: `web/tests/browser/test_browser_creation_viewport_pointer.py`.
- No server, protocol, data or dependency change.
- Human-reviewed: the design's "Human review: allocation slider and locked-axis styling" section covers how the slider and the muted locked rows look. No test checks that.
