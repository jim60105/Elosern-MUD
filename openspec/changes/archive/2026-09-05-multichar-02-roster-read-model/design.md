## Context

Every committed panel today renders the session's one puppet. `PresentationContext` carries
`actor`, `protocol_version`, `options_state`, `options_fingerprint`, and `proposal` — no session
and no account. `build_presentation_context(session, actor)` is the single factory every
publication path goes through (`synchronize_session`, the dispatcher's completion / internal-error
/ stale paths, the art push, the trigger service), and presenters receive only the context.

The relevant existing machinery:

- `PresentationRegistry.register(PresenterSpec(name, schema_version, unavailable_reason,
  presenter))`; `render` converts every presenter failure into the registry-owned unavailable
  payload, and `PanelUnavailableError` selects the non-internal form.
- `objectives` is the precedent for a panel added late: registered with the shared
  `UNAVAILABLE_REASON`, rendered in every snapshot, with its own `PANEL_ALLOWLIST` entry in the
  preserved reducer `web/static/webclient/js/elosern/protocol.js`.
- `world/art/presenter.py::resolve_character(entity)` already resolves *any* entity's portrait:
  it calls `character_subject_for` (explicit `portrait_policy` only), applies the adult gate, and
  returns `{kind, label, status, url, aspect_ratio, alt, subject_key}` — falling back to the
  `無肖像` placeholder when the entity carries no policy. It does not require room presence.
- `world/rules/character_creation.py::finalize_player_portrait` writes
  `{"mode": "named", "stable_key": str(pk)}` **at activation**, so a still-pending shell has no
  portrait policy by construction.
- `world/rules/combat_session.py::is_in_active_session(actor)` is the same predicate
  `PlayerCharacter.at_pre_move` and `Coordinator.mode_for` use.
- Evennia's `create_character` defaults `key=self.key` (the account name), and
  `activate_player_character` renames the object to the chosen display name inside the activation
  transaction. Two pending shells on one account therefore share the account's name until
  activated.

## Goals / Non-Goals

**Goals:**

- One committed, read-only account-level panel that is available in **every** mode — creation
  included — so the switcher change never needs a bespoke availability gate.
- Truthful rows: identity, the object's current key, whether it is the live puppet, whether it is
  still pending, and its portrait resolution — nothing invented and nothing mutated.
- The account-level capacity and lock facts (`max_characters`, `can_create`, `switch_locked`,
  `lock_reason`) computed once per snapshot from canonical state.
- A store slice consumers can bind to, shipped with no consumer, so the switcher change is pure UI.

**Non-Goals:**

- No actions. `account.character.switch` / `account.character.create` are changes 03 and 04; this panel
  is display-only and its `switch_locked` field is advisory — change 03's adapters re-check the
  same predicates server-side.
- No per-character status badge (HP, location, last-played). The original design's D11 keeps the
  row to name + portrait, and nothing on the wire should exist that the UI does not render.
- No character deletion, renaming, or reordering.
- No change to `status`, `character`, or any other panel's schema version.

## Decisions

### D1 — A separate `roster` panel, not a field on `status`

The original design said "the roster travels with every status snapshot, the same way
location/time reach TopBar". That reading would put it *inside* the `status` panel, bumping
`STATUS_SCHEMA_VERSION` from 2 to 3 and forcing every `status` consumer, fixture, story, and the
reducer's allowlist version to move with it — for a field that has nothing to do with the actor's
resources or conditions.

A separate `roster` panel satisfies the same intent (it rides every snapshot, because
`full_snapshot` renders every registered panel) at a fraction of the blast radius, and it is the
`objectives` panel's precedent exactly. It also gets an independent availability discriminator, so
a broken account read degrades the switcher alone instead of the vitals.

### D2 — The presenter resolves the account from `context.actor.account`

`PresentationContext` has no session and no account, and widening it would touch every
publication path. `ObjectDB.db_account` is the account currently puppeting the object, so a
rendered actor always has one; the wrapper property `actor.account` is the read.

The actor itself must be read defensively, not only its `account`. `build_presentation_context` is
called with `getattr(session, "puppet", None)` on the dispatcher's stale path
(`web/webclient/actions/dispatcher.py:570-573`), so `context.actor` can legitimately be `None` on
an existing, reachable path. The read model therefore uses `getattr(actor, "account", None)`
rather than `actor.account`: a plain attribute read would raise `AttributeError`, which
`PresentationRegistry.render` catches and degrades into the **internal** unavailable form with a
correlation ID and an operational error log — misreporting a routine "no account to show" as a
presenter defect.

An actor that is `None`, an actor with no resolvable account, or an account whose `characters`
handler raises, all raise `PanelUnavailableError`, which yields the registry-owned non-internal
unavailable payload — the same degradation every other panel uses.

Alternative considered: add `account` to `PresentationContext`. Rejected for this change: it
changes the single factory's signature and every construction site for one panel's benefit. If a
second account-level panel ever appears, that is the moment to widen the context.

### D3 — The read model lives in `world/rules/account_roster.py`

Presenters serialize; they do not read canonical state directly (`status.py` calls
`build_status_read_model`, `art.py` calls `build_art_view`). The roster follows the same shape: a
frozen `AccountRosterView` of frozen `RosterCharacterView` rows plus the capacity/lock facts,
built read-only, never lazily constructing a handler and never writing.

### D4 — Portrait rows reuse `resolve_character`, unchanged

No generalization is needed: `world/art/presenter.py::resolve_character(entity)` already accepts
any entity, resolves only from an explicit named `portrait_policy`, applies the adult gate, and
returns the `無肖像` placeholder when no policy exists. The roster row serializes exactly the
fields the `art` panel's catalog entries carry (`subject_key`, `status`, `url`, `aspect_ratio`,
`alt`, `placeholder`), so the switcher change reuses `ArtPanel.vue`'s existing placeholder treatment
verbatim instead of inventing a second portrait vocabulary.

Consequence, stated rather than hidden: a still-pending character always resolves to the
placeholder, because `finalize_player_portrait` only runs at activation.

### D5 — `name` is the object key; `pending` is a separate flag; the client owns the marker

Because Evennia's `create_character` defaults the key to the account name, an account can hold two
pending shells that are both literally named after the account. The read model reports the truth
(`name` = the current object key, `pending` = the creation marker) and does **not** synthesize a
disambiguating label server-side — inventing a name on the wire would be a presentation decision
smuggled into the read model, and the object key is what `進入世界 <角色>` matches on.

The switcher change renders a stable 「建立中」 marker on pending rows, which disambiguates them for the
player without touching canonical identity.

### D6 — Rows are ordered by ascending character id and bounded

Deterministic ordering by numeric database id, mirroring `art_view._exploration_entities`, so the
row order never depends on handler iteration order and a snapshot diff is stable. The live puppet
is **not** hoisted to the front; it carries `current: true` and the client decides how to present
it.

The row list is bounded by a module constant equal to the knob's hard ceiling (10). The cap
already bounds it, but the presenter must not depend on a setting for its payload bound — a
misconfigured or future cap can never produce an envelope-busting panel.

### D7 — `switch_locked` is one snapshot-wide fact with one stable reason

Computed once from `is_in_active_session(context.actor)` — the same predicate that blocks
movement and resolves `combat` mode. When true, every non-current row is uniformly unswitchable
and the panel carries a single stable `lock_reason` string; there is no per-row status field
(the original design's D11).

The panel field is advisory only. Change 03's adapters re-evaluate the predicate at admission, so
a stale click cannot race the server into a switch.

### D8 — Availability is mode-independent, including creation

Unlike `party`, `objectives`, `character`, `services`, and `dialogue` — all of which return
unavailable for a `creation_pending` actor — the roster presenter deliberately does **not** gate
on `creation_pending`. A player who abandons a wizard mid-way must be able to switch back to a
finished character, which is only possible if the panel renders in creation mode. This is the
single reason the roster is its own panel rather than a slice of an existing one.

### D9 — `PANEL_ALLOWLIST` and the wire validator follow the `objectives` precedent

`roster: 1` is added to `PANEL_ALLOWLIST` in `web/static/webclient/js/elosern/protocol.js`, with
the panel's exact-field validator alongside the existing per-panel validators. The preserved
reducer is edited the same way `objectives`, `title_ballot`, and `title_codex` edited it; the
frozen façade surface (`window.Elosern.*`) is untouched.

## Risks / Trade-offs

- **Per-snapshot cost:** every full snapshot now resolves up to `MAX_NR_CHARACTERS` portrait
  records. → Mitigation: the bound is 10, each row is one attribute read plus the same art-record
  lookup the `art` panel already performs per catalog entry (`MAX_PORTRAIT_CATALOG` is 32), so the
  added work is strictly smaller than a panel that already ships. A regression test asserts the
  presenter performs no write and no lazy handler construction.
- **The panel exists with no consumer for one change.** → Accepted deliberately: it makes change
  04 a pure UI change and lets the read model be verified by unit tests and a snapshot assertion
  before any component depends on its shape.
- **`actor` or `actor.account` is `None`.** Not exotic: the dispatcher's stale path renders with
  `getattr(session, "puppet", None)`. → Mitigation: both reads are defensive and both degrade
  through `PanelUnavailableError` to the shared **non-internal** unavailable payload, so neither
  raises an `AttributeError` that would be logged as a presenter defect. The client renders no
  switcher, which is the correct behaviour for a session with no account.
- **The adult gate could hide a row's portrait** for a character whose age fields are somehow
  invalid. → Accepted: `resolve_character` already returns the `無法提供` placeholder in that case,
  and the row itself still appears, so the character stays reachable.
