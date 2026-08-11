## Context

`_submitCustom` (`web/static/webclient/js/plugins/creation_dock.js:647-685`) sends `creation.custom` and immediately, before any server result, flips `_view` to the activation confirmation. A rejected save (`_rejected` without `affected_panels`, `web/webclient/actions/creation_actions.py:175-177`) publishes a snapshot with an unchanged draft, so the confirmation stays live and `creation.activate` later activates whatever older draft is stored (`creation_wizard.py:613-673`). Separately, Telnet activation writes `portrait_policy` and calls `schedule_portrait_ensure` (`commands/character_creation.py:106-112`) while the Web path (`creation_actions.py:307-330`) does neither; `_recover_named_portraits` (`world/art/service.py:193-219`) cannot repair a missing policy.

## Goals / Non-Goals

**Goals:**
- Confirmation screen reachable only for a server-confirmed save of the draft the player just submitted.
- A stale/live confirmation cannot activate any draft other than the last successfully saved one.
- Identical portrait finalization across Telnet and Web activation.

**Non-Goals:**
- Changing the deterministic `activate_player_character` semantics.
- Retry/backoff UX for failed saves (server already returns stable rejection codes).

## Decisions

**D1 — Move the confirm-view switch into the save success path (client).** `_submitCustom` transitions to the confirmation view only inside the `creation.custom` success callback; on rejection/error it stays on the form and surfaces the rejection code.

**D2 — Server-side draft fingerprint binding (defense in depth).** `save_custom_draft` returns the fingerprint of the stored draft; the adapter records it as `session.ndb`-local state (or in the returned payload) and `creation.activate` requires the activation payload's fingerprint to match the draft it is about to activate. A mismatch is rejected with a stable code, so even a crafted/stale confirmation cannot activate an older draft.

**D3 — Shared post-activation finalization helper inside the activation transaction.** Extract `finalize_player_portrait(character)` (named policy `{"mode": "named", "stable_key": str(pk)}` + `transaction.on_commit(schedule_portrait_ensure)`) into `world/rules/character_creation.py`; call it from both `commands/character_creation.py` and `_creation_activate_adapter` INSIDE `activate_player_character`'s outer transaction, so a rollback removes both the policy attribute and any queued job (fault-injection test pins this).

## Risks / Trade-offs

- **Fingerprint format drift**: draft fingerprint must be stable between save and activate; reuse the existing serialization/fingerprint function already used for draft staleness (`creation_wizard.py:455-468`).
- **Failed portrait enqueue after activation**: art failures must not roll back the character; finalization stays post-commit, mirroring Telnet today.
- **Web preset/concept paths**: activation gating applies to custom saves; preset/concept paths already finalize the same stored draft and go through the same activate adapter, so fingerprint binding covers them uniformly.
