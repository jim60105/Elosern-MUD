## Why

Two creation-finalization defects from audit run-1: (F02) the Web creation dock switches to the activation-confirmation screen before the `creation.custom` save result arrives, so a server-rejected save leaves the confirmation live and confirming activates an older stored draft — an irreversible wrong character; (F13) Web activation never assigns the named `portrait_policy` nor schedules the portrait ensure that Telnet activation performs, so Web-created characters permanently lack portraits (startup recovery cannot repair the missing policy).

## What Changes

- The activation-confirmation view is entered only after a successful `creation.custom` save, and stays out on rejection.
- Activation is bound to the exact draft that was last successfully saved (server-side fingerprint), so a stale confirmation can never activate an older draft.
- Web activation performs the same portrait finalization as Telnet activation: named `portrait_policy` + post-commit `schedule_portrait_ensure`, via a shared helper.

## Capabilities

### New Capabilities

- `creation-activation-gating`: save-then-confirm ordering and draft-fingerprint binding for Web creation activation.

### Modified Capabilities

- `webclient-character-creation-ui`: confirmation follows a confirmed successful save; rejected or pending saves stay on the form.
- `art-asset-lifecycle`: every player-activation path (Telnet and Web) runs the same portrait finalization.

## Impact

- `web/static/webclient/js/plugins/creation_dock.js` (confirm-view gating), `web/webclient/actions/creation_actions.py` (adapter + fingerprint), `world/rules/creation_wizard.py` (activation fingerprint check), `world/rules/character_creation.py` or a new shared finalization helper, `commands/character_creation.py` (dedupe to shared helper).
