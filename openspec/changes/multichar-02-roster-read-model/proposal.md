## Why

Once an account can hold several characters (`multichar-01-account-capacity`), the WebClient has
no way to know it. The whole presentation stack is built around "one session, one live puppet":
`PresentationContext` carries only the actor, and every registered panel renders that one
character. There is no account-level read model anywhere on the wire, so the TopBar switcher has
nothing to render and the switch/create actions have nothing to gate their controls on.

This change adds exactly that read model — a committed `roster` presentation panel — and stops
there. It ships no action and no UI, so it can land and be verified independently of the write
path.

## What Changes

- Add a new host-independent `roster` presentation panel (schema version 1), registered in
  `web/webclient/presentation/registry.py` and rendered in every snapshot, so the switcher can
  render in creation, exploration, combat, and dialogue mode alike without a bespoke availability
  gate.
- Add the deterministic read model behind it in `world/rules/` — the account's owned characters,
  each with its stable identity, display label, pending flag, and portrait subject resolution —
  built read-only from canonical state, exactly like the existing status/art read models.
- Resolve each row's portrait through the existing named-portrait subject mechanism
  (`world.art.subjects.character_subject_for` plus the art presenter's resolver), generalized from
  "an entity present in the current room" to "any character the account owns". A character that
  has not been activated yet carries no portrait policy and resolves to the shared placeholder.
- Carry the account-level capacity facts on the same panel: how many characters the account may
  hold, whether another may be created, and whether switching is currently blocked (with one
  shared, stable reason) because the live puppet is in an active combat session.
- Expose the panel as a client store slice (`rosterSlice`) with no component consuming it yet, so
  change 04 has a committed read model to bind to.
- Add the `roster` entry to the client protocol reducer's `PANEL_ALLOWLIST` and its wire
  validator, following the `objectives` panel precedent.

## Capabilities

### New Capabilities

- `webclient-character-roster`: the committed account-level roster read model — which characters
  an account owns, which one is live, each row's portrait resolution, the capacity facts, and the
  switch-lock state. (The switch/create actions and the TopBar UI extend this same capability in
  changes 03 and 04.)

### Modified Capabilities

- `webclient-oob-protocol`: the panel allowlist gains `roster`, and the roster is the first panel
  whose subject is the account rather than the puppet — the read-only, no-mutation presenter
  contract is restated for it explicitly.

## Impact

- New: `world/rules/account_roster.py` (deterministic read model),
  `web/webclient/presentation/roster.py` (presenter), plus their tests.
- Modified: `web/webclient/presentation/registry.py` (panel registration),
  `web/static/webclient/js/elosern/protocol.js` (`PANEL_ALLOWLIST` + roster validator),
  `web/webclient-app/stores/elosern.js` (`rosterSlice`).
- Depends on `multichar-01-account-capacity` (an account that can actually hold more than one
  character; without it every roster is a single row and the capacity facts are untestable).
- Unblocks `multichar-03-switch-create-actions` (shares the lock/capacity semantics) and
  `multichar-04-topbar-switcher-ui` (consumes the slice).
- No player-facing behaviour changes: nothing renders the panel until change 04.
