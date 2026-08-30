## ADDED Requirements

### Requirement: TitleCodexView is a pure bounded read model for the codex
`world/rules/title_view.py` SHALL expose
`build_title_codex_view(character, *, max_rows, max_display_chars,
max_basis_chars) -> TitleCodexView` reading only lore registry,
`db.title_collection`, and `db.title_equipped`: fixed rows in registry order
carrying `key`/`display`/`category`/`hint_zh` (hint only while locked)/
`flavor_zh` (only when unlocked)/`unlocked`, epithet rows newest-first carrying
`display`/`basis`/`equipped`/`can_remove`, an `equipped` dict, a live-composed
`full_title`, and unlocked/total counters. Every string SHALL respect the passed
maxima; the view SHALL compute without mutating and repeat byte-identically
while state is unchanged. OOB constants `TITLE_MAX_ROWS` /
`TITLE_MAX_DISPLAY_CHARS` / `TITLE_MAX_BASIS_CHARS` (and the title-category
enum) SHALL be mirrored across all four mirrors like every OOB surface.

#### Scenario: Locked rows show hints, unlocked rows show flavor
- **WHEN** a view is built for a character holding part of the registry
- **THEN** locked rows carry `hint_zh` and no flavor, unlocked rows carry flavor and no hint, and counters equal the unlocked/total split

#### Scenario: Overlong basis text is clipped to the cap
- **WHEN** an epithet's `origin_quote` exceeds `max_basis_chars`
- **THEN** the row's basis is clipped to the cap and remains a contiguous prefix of the quote

### Requirement: The codex OOB payload and WebClient window are server-authored
The `title` OOB schema v1 SHALL carry
`{schema_version, fixed_rows, epithet_rows, equipped, full_title, unlocked,
total, pending_ballot}` rendered by the WebClient as a big window: header with
the live full-title preview; 「稱號」block with category tabs (戰鬥／法術／探索／公會／
風流韻事), locked cards showing 🔒 + hint, clicking an unlocked fixed card
requesting that fixed equip; 「異名」block with click-to-equip, ★ marking the
equipped epithet, and the 「移除」 button rendered from the row's server-computed
`can_remove` flag with no client-side rules; a 「提名中」tab presenting G's pending
ballot with the accept/decline buttons; no 卸裝 control anywhere. The preview
SHALL update on every successful equip.

#### Scenario: Locked cards offer no affordance
- **WHEN** the window renders a row whose `unlocked` is false
- **THEN** the card shows the lock and hint, and clicking it causes no state change

#### Scenario: The remove button follows the flag
- **WHEN** an epithet row carries `can_remove = false`
- **THEN** no 移除 control renders for it, and the client evaluates no gate logic itself

### Requirement: Epithet removal is the only delete path and gates precede confirmation
`world/rules/titles.py::remove_epithet(entity, display)` SHALL be the system's
only collection-deleting API, validating in one pass before any review state
exists: unknown display or wrong kind ⇒ stable rejection; `display` equals the
equipped epithet ⇒ `TITLE_EQUIPPED_UNREMOVABLE`; it is the last remaining
epithet ⇒ `TITLE_LAST_EPITHET` — neither gate code ever enters the confirm flow.
Only an un-gated target echoes review info (display + basis) for the two-step
Telnet path (`title remove epithet <display>` then literal `confirm` suffix; any
other continuation cancels without state change), after which the executing call
re-validates both gates and, within one snapshot-registered transaction, removes
the entry and appends `title_epithet_removed` (entity, display, tick) to the
EventLog. Slots SHALL never be touched by removal. Fixed titles SHALL expose no
delete API, command, or code path — a structural test asserts absence. Removal is
irreversible; there is no recycle bin, and the removed name becomes nominatable
again through G's live-collection filter.

#### Scenario: Equipped epithet refuses at gate one
- **WHEN** `title remove epithet <equipped display>` is attempted
- **THEN** `TITLE_EQUIPPED_UNREMOVABLE` is returned and no review info is echoed

#### Scenario: The last epithet refuses
- **WHEN** a collection holding exactly one epithet attempts its removal
- **THEN** `TITLE_LAST_EPITHET` is returned and the collection is unchanged

#### Scenario: Confirm removes and records; any other continuation cancels
- **WHEN** an un-gated removal is confirmed with the literal `confirm` suffix, and separately answered with anything else
- **THEN** the confirmed call removes the entry, leaves both slots untouched, and appends `title_epithet_removed`; the other leaves state byte-identical

#### Scenario: Fixed titles have no delete surface
- **WHEN** the structural absence test scans titles modules and command surfaces
- **THEN** no fixed-title delete API, command, or code path exists

### Requirement: Codex surfaces remain consistent across sessions
Collection, equip record, and pending ballot are persistent attributes, so the
codex window — including the 「提名中」tab and every `can_remove` flag — SHALL
render identically after relogin or reload; a removal executed in one session
SHALL be reflected in the next session's view and EventLog.

#### Scenario: Post-relogin view matches the pre-logout view
- **WHEN** a player removes an epithet, logs out, and reopens the codex
- **THEN** the row is gone, counters updated, and the ballot tab state is unchanged by the logout
