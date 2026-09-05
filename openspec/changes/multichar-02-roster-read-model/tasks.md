# Tasks: multichar-02-roster-read-model

## 1. Deterministic read model

- [ ] 1.1 `world/rules/account_roster.py`: frozen `RosterCharacterView`
  (`identity: int`, `name: str`, `current: bool`, `pending: bool`) and frozen `AccountRosterView`
  (`characters: tuple[...]`, `max_characters: int`, `can_create: bool`, `switch_locked: bool`,
  `lock_reason: str | None`), plus `AccountRosterError` for an unreadable account. Module constant
  `MAX_ROSTER_ROWS = 10` (presenter-owned, independent of the configured cap).
- [ ] 1.2 `build_account_roster(actor)`: resolve the owning account from `actor.account`, raise
  `AccountRosterError` when it is absent or its character list cannot be read; build rows from
  `account.characters` sorted by ascending `pk`, truncated to `MAX_ROSTER_ROWS`; bound each name
  by the shared display-name code-point bound; mark `current` by identity comparison with the
  actor; read `pending` from `creation_pending`.
- [ ] 1.3 Capacity/lock facts: `max_characters` from `django.conf.settings.MAX_NR_CHARACTERS`
  read at call time (never snapshotted at import); `can_create` from the character count against
  it; `switch_locked` from `world.rules.combat_session.is_in_active_session(actor)`; the single
  stable `lock_reason` 「戰鬥中無法切換角色」 only when locked. No writes, no lazy handler
  construction, no persona or disguised-stats read.

## 2. Presenter and registration

- [ ] 2.1 `web/webclient/presentation/roster.py`: `ROSTER_SCHEMA_VERSION = 1` and
  `roster_presenter(context)` serializing `build_account_roster(context.actor)`, converting
  `AccountRosterError` into `PanelUnavailableError`. Deliberately no `creation_pending` gate —
  add the comment naming that as the reason the panel exists separately.
- [ ] 2.2 Each row's `portrait` object serialized from `world.art.presenter.resolve_character`,
  carrying `subject_key`, `status`, `url`, `aspect_ratio`, `alt`, and `placeholder` in exactly the
  shape `web/webclient/presentation/art.py::_serialize_catalog_entry` produces (reuse its
  `_placeholder_for` treatment so the two never drift).
- [ ] 2.3 `web/webclient/presentation/registry.py`: register the `roster` panel with the shared
  `UNAVAILABLE_REASON` (the roster has no bespoke failure vocabulary) and
  `ROSTER_SCHEMA_VERSION`.

## 3. Client protocol reducer

- [ ] 3.1 `web/static/webclient/js/elosern/protocol.js`: add `roster: 1` to `PANEL_ALLOWLIST` and
  the exact-field roster validator beside the existing per-panel validators, following the
  `objectives` panel's pattern (available-form field allowlist, bounded row list, bounded strings,
  nullable URL restricted to the `/art/` same-origin prefix).
- [ ] 3.2 Confirm the panel-version parity contract test picks the new panel up; add the roster to
  whichever fixture enumerates registered panels if it is a literal list.

## 4. Store slice

- [ ] 4.1 `web/webclient-app/stores/elosern.js`: derive `rosterAvailable`, `rosterCharacters`,
  `rosterCanCreate`, `rosterMaxCharacters`, `rosterSwitchLocked`, and `rosterLockReason` from
  `rs.panels.roster` in the reducer view, and expose the matching computeds — mirroring the
  `objectivesAvailable` / `objectivesRows` pattern. No component consumes them in this change.

## 5. Tests

- [ ] 5.1 `world/rules/tests/test_account_roster.py` (`EvenniaTest`): ordering by identity; the
  `current` flag; the `pending` flag; a foreign account's characters never appear; the row bound
  holds when the account somehow exceeds it; `max_characters` / `can_create` at and below the cap;
  `switch_locked` and its reason in and out of an active combat session; `AccountRosterError` when
  `actor.account` is `None`.
- [ ] 5.2 `web/webclient/presentation/tests/test_roster.py`: available-form field set; the panel
  is available for a `creation_pending` actor and for an actor in combat; a raised
  `AccountRosterError` yields the common non-internal unavailable form carrying
  `schema_version: 1`; the portrait object matches the art catalog entry shape for an activated
  character, a pending character (no-portrait placeholder, null URL, null subject key), and a
  not-yet-generated asset.
- [ ] 5.3 Read-only assertion: rendering a full snapshot for an account owning several characters
  leaves every listed character's traits, attributes, and handlers untouched and does not advance
  the world clock.
- [ ] 5.4 Vitest: the reducer accepts a valid `roster` panel and rejects a payload with an unknown
  field, an out-of-prefix URL, or a wrong schema version; the store slice exposes the committed
  rows and degrades to empty/unavailable.
- [ ] 5.5 `covers_requirement` annotations for the five new `webclient-character-roster`
  requirements and the modified `webclient-oob-protocol` requirement.

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world web.webclient server` and `npm test`.
- [ ] 6.2 `uv run --locked python -m tools.spec_traceability check` and
  `uv run --locked python -m tools.observability_lint check`.
- [ ] 6.3 Live container check with two characters on one account: `ui_sync` delivers a `roster`
  panel with both rows, correct `current` marking, and correct `can_create`; entering combat flips
  `switch_locked` on the next snapshot and leaving it clears the flag.
