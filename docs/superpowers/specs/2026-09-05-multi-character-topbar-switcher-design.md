# Multi-Character Support and TopBar Character Switcher — Design

**Date:** 2026-09-05
**Status:** Approved
**Scope:** Enabling one account to own and play multiple characters end to end — backend
capacity, a new-character creation entry point, account-level WebClient protocol/actions, and a
TopBar dropdown for switching or creating characters.

---

## 1. Product Context

Evennia's `CmdIC`/`CmdOOC` (localized as `進入世界`/`離開角色` in
`commands/localized/account.py`) already implement generic puppet switching among
`account.characters`. However, the project currently ships with Evennia's default
`MAX_NR_CHARACTERS = 1` (never overridden in `server/conf/settings.py`), and there is no
in-game path to create a second character — exactly one character shell is auto-created per
account at account creation (`Account.at_post_create_character`). The whole WebClient stack
(`protocol.py`, `PresentationContext`, `AppClient.vue`) is built around "one session, one live
puppet" and carries no account-level concept of "my other characters."

This change raises the character cap, adds an explicit "create another character" flow reusing
the existing creation wizard, and exposes an account-level roster + switch/create actions through
the WebClient protocol, surfaced as a dropdown in `TopBar.vue`.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Full-stack scope.** This change covers backend capacity, the new-character flow, the account-level protocol, and the TopBar UI as one feature. | The four layers are tightly coupled (UI needs the protocol, which needs backend capacity); none is independently useful. |
| D2 | **Character cap is an env-overridable knob**, `MAX_NR_CHARACTERS = _env_int("ELOSERN_MAX_CHARACTERS", 5)` in `server/conf/settings.py`, following the file's existing `_env_int` pattern. | Matches the deployment-knob convention already used throughout the file; avoids a hardcoded redeploy-to-change value. |
| D3 | **`MULTISESSION_MODE` and `AUTO_PUPPET_ON_LOGIN` stay unchanged.** | They already express "one live puppet per session" and "reconnect resumes the last puppet," both of which this feature preserves. |
| D4 | **A new character is created by unpuppeting the current one, calling `account.create_character(...)`, puppeting the fresh shell, and letting it fall into the existing creation wizard** (the shell's `creation_pending=True` already routes it through `CharacterCreationCmdSet`/`CreationOverlay`). | Reuses the entire existing creation UI and rules pipeline; no second wizard is built. |
| D5 | **Creating a character requires client-side confirmation before dispatch** (no new protocol step; the client simply gates when it sends `account.character.create`). | Prevents an accidental click from leaving the current character (agreed during brainstorming). |
| D6 | **`WORLD_INTRODUCTION` is never resent for a second/third character.** Only the reusable creation-start presentation applies. | The introduction is account-level lore shown once; it is not per-character content. |
| D7 | **Switching or leaving a character is blocked while the current puppet is in an active combat session** (`world.rules.combat_session.is_in_active_session`), mirroring the existing movement block in `PlayerCharacter.at_pre_move`. | Prevents using character-switch as a combat-escape hatch or leaving combat state inconsistent. |
| D8 | **The roster (character list) travels with every status snapshot**, the same way location/time reach `TopBar` today, rather than being a separately requested panel. | The switcher must render in every mode (creation/exploration/combat/dialogue); tying it to snapshot delivery avoids a bespoke availability/mode gate. |
| D9 | **Switch and create are dispatched as ordinary account-scoped actions** (`account.character.switch`, `account.character.create`) through the existing action registry/dispatcher, not a new transport concept. | Reuses validation, in-flight/epoch guarding, and error-envelope conventions already built for every other action. |
| D10 | **Portrait thumbnails reuse the existing named-portrait subject mechanism** (`portrait_policy = {"mode": "named", "stable_key": str(pk)}`, the same one `world/rules/art_view.py` uses for present-entity portraits), generalized to resolve by character id regardless of room presence. | Every activated player character already gets this policy at creation (`finalize_player_portrait`); no new asset pipeline is needed. |
| D11 | **The dropdown shows only name + portrait per character**, not a general per-character status badge; a disabled reason (combat lock, slot cap) is shown once, contextually, not per row. | Matches the reviewed content scope; keeps the row visually simple. |
| D12 | **An orphaned pending character (creation abandoned mid-wizard) needs no special handling.** It simply appears in the roster; selecting it resumes the creation wizard through the same puppet-switch action, because a `creation_pending` puppet already renders `CreationOverlay` on sync. | Falls out of D4 + D8 for free; avoids a distinct "resume" code path. |

---

## 3. Backend Capacity

- `server/conf/settings.py`: add
  ```python
  MAX_NR_CHARACTERS = _env_int("ELOSERN_MAX_CHARACTERS", 5)
  ```
  placed near the other deployment knobs, using the file's existing bounded-int helper.
- No change to `MULTISESSION_MODE` (stays at Evennia's default, one live session per account) or
  `AUTO_PUPPET_ON_LOGIN` (stays `True`).
- `commands/localized/account.py`'s `_MAX_NR_CHARACTERS == 1` branches in `CmdOOCLook`/`CmdOOC`
  become dead once the cap is raised (they gate on the value being exactly 1); no code change is
  required there, but this is a known, accepted side effect — Telnet OOC will fall through to
  Evennia's default multi-character OOC menu once more than one character exists.

## 4. New-Character Creation Flow

New account-scoped action `account.character.create` (empty payload), added to a new
`web/webclient/actions/account_actions.py` alongside `character_actions.py`'s existing pattern.

Adapter behavior:

1. Reject with `{"outcome": "rejected", "code": "character_slots_full", "message": "角色數量已達上限。"}`
   when `len(account.characters) >= settings.MAX_NR_CHARACTERS`.
2. Otherwise, mirroring `CmdOOC.func`:
   - `account.unpuppet_object(session)`
   - `send_unpuppet_transition(session)`
   - `retire_sequence(session)`
   - `reset_client_sequence(session)`
3. `account.create_character(...)` to create a fresh shell (`creation_pending=True` is already
   set by `Account.at_post_create_character`).
4. `account.puppet_object(session, new_shell)`; set `account.db._last_puppet = new_shell`.
5. `synchronize_session(session, new_shell)` to push a full snapshot. Because the new shell is
   `creation_pending`, the snapshot's mode resolves to `creation` the same way the account's very
   first character does, and the browser renders `CreationOverlay` unmodified.
6. `WORLD_INTRODUCTION` is not sent (D6); only the existing creation-start presentation applies.

Client side: `CharacterSwitcher`'s "＋ 新增角色" row opens a confirmation modal; only on
confirmation does it dispatch `account.character.create`.

## 5. Account-Level Protocol: Roster, List, and Switch

### 5.1 Roster delivery

Every status/snapshot push (the same path that currently carries location/time for `TopBar`)
gains a `roster` slice:

```jsonc
{
  "characters": [
    { "id": 42, "name": "艾莉亞", "portrait_url": "…" /* or null */, "current": true, "switchable": false },
    { "id": 57, "name": "凱恩", "portrait_url": null, "current": false, "switchable": true }
  ],
  "can_create": true,
  "max_characters": 5
}
```

- `switchable` is computed once per snapshot from whether the **current** puppet is in an active
  combat session (D7); when `false`, every non-current row is uniformly locked and the client
  shows one shared reason string rather than a per-row status.
- `portrait_url` resolves through the same named-portrait subject lookup used by
  `world/rules/art_view.py` (`character_subject_for` / `portrait_policy`), generalized to accept
  an arbitrary owned character id instead of only "present in the current room." `null` means no
  portrait asset yet (placeholder rendered client-side, consistent with `ArtPanel.vue`'s existing
  placeholder handling).
- `can_create` is `len(account.characters) < settings.MAX_NR_CHARACTERS`.

### 5.2 `account.character.switch`

Payload: `{"character_id": <int>}`.

Adapter behavior:

1. Reject (`invalid_character`) if `character_id` does not resolve to a member of
   `account.characters`.
2. Reject (`in_combat`) if the current puppet `is_in_active_session`.
3. No-op success if `character_id` is already the current puppet.
4. Otherwise perform the same unpuppet → puppet → `synchronize_session` sequence as §4 steps 2, 4,
   5 (targeting the requested character instead of a freshly created one), and update
   `account.db._last_puppet`.

Both actions are registered in `web/webclient/presentation/registry.py` alongside the existing
action families, and follow the existing `{"outcome": "success"|"rejected", "code", "message"}`
envelope shape and the dispatcher's existing in-flight/epoch guarding — no new concurrency
mechanism is introduced.

## 6. Frontend: TopBar Character Switcher

- New component `web/webclient-app/components/CharacterSwitcher.vue`, mounted inside
  `TopBar.vue`'s existing top-right cluster (alongside the meta pill, without colliding with the
  HUD island anchors that start at `top:64px`, per D5/D10 of the original TopBar design).
- **Collapsed state:** current character's portrait thumbnail + name.
- **Expanded (dropdown) state:**
  - One row per roster character: portrait thumbnail + name. The current character's row is
    marked selected and is not clickable.
  - When `switchable` is `false` for the roster, every non-current row renders disabled/greyed
    with one shared inline note (e.g. "戰鬥中無法切換角色"), instead of per-row badges (D11).
  - A trailing "＋ 新增角色" row; disabled/greyed with "角色數量已達上限" when `can_create` is
    `false`; otherwise opens a confirmation modal, and only on confirmation dispatches
    `account.character.create`.
  - Clicking an enabled, non-current row dispatches `account.character.switch` with that
    character's id.

## 7. Error Handling and Edge Cases

- **Combat lock:** covered by D7/§5.1 — both the switch and create actions reject with
  `in_combat` while the current puppet is in an active session; the dropdown reflects this
  uniformly rather than letting a stale click race the server.
- **Slot cap reached:** `character_slots_full` / `can_create: false` — covered above.
- **Invalid or foreign character id:** `account.character.switch` rejects any id not in
  `account.characters`; no cross-account puppeting is possible through this surface.
- **Concurrent/rapid clicks:** handled by the dispatcher's existing per-session in-flight
  epoch/marker guard; no new debouncing logic is required.
- **Abandoned pending character:** no special handling needed (D12) — it is just another roster
  entry that resumes the creation wizard when selected.
- **Portrait not yet generated:** `portrait_url: null` renders the existing placeholder treatment,
  consistent with how `ArtPanel.vue` already handles missing portraits.

## 8. Testing Plan

- **Backend unit tests:** `web/webclient/actions/tests/test_account_actions.py` covering
  `account.character.create` (slot-cap gate) and `account.character.switch` (membership gate,
  combat-lock gate, no-op-on-self, successful puppet transition + `_last_puppet` update).
- **Settings test:** assert `ELOSERN_MAX_CHARACTERS` overrides `MAX_NR_CHARACTERS` and the
  default is 5, following the existing environment-override test conventions in
  `server/conf/tests/`.
- **Frontend:** Storybook stories for `CharacterSwitcher` covering collapsed, expanded, disabled
  (combat-locked), and slot-cap-reached states; a component test asserting the correct actions are
  dispatched on row/confirm clicks.
- **Integration:** extend `server/conf/tests/test_ui_action_integration.py` with an end-to-end
  WebSocket scenario that creates a second character, switches back and forth, and asserts a full
  snapshot (including the new puppet's own panels) is delivered after each transition.

---

## 9. Out of Scope

- Any Telnet-side UI for browsing/switching characters beyond Evennia's stock OOC menu (already
  functional once the cap is raised; no localization or styling work is planned here).
- Per-character-slot monetization, deletion, or renaming flows.
- Concurrent multi-window puppeting of two characters from the same account at once (unaffected by
  and unrelated to `MULTISESSION_MODE`, which this change does not touch).
