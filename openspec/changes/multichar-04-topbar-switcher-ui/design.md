## Context

`TopBar.vue` is 114 lines and holds exactly two absolutely positioned elements inside the stage's
top band: `.topbar-brand` at `top:16px; left:16px` and `.topbar-meta` at `top:16px; right:16px`,
both at `z-index: 4`. Its header comment records the constraint that the HUD island anchors start
at `top:64px`, so the band must stay bounded above them. `AppShell.vue` passes
`locationLabel` / `timeLabel` / `connected`; `AppClient.vue` sources them from
`store.view.statusSlice`.

`multichar-02` adds the store slice this surface binds to (`rosterAvailable`,
`rosterCharacters`, `rosterCanCreate`, `rosterMaxCharacters`, `rosterSwitchLocked`,
`rosterLockReason`), with each row carrying identity, name, current/pending flags, and an art-panel
shaped `portrait` object. `multichar-03` adds `account.character.switch` and
`account.character.create`.

Existing conventions this surface must obey rather than reinvent:

- `store.dispatchAction(actionId, payload, display)` is the single dispatch entry; it already gates
  on `connected`, `mutationsLocked`, `phase !== "active"`, and one-in-flight.
- The two-step confirmation pattern is established by the combat Forfeit frame: open a panel with
  an explicit cancel row and confirm row, submit only from confirm, and leave safely on Escape.
- `ArtPanel.vue` already renders the exact `{subject_key, status, url, aspect_ratio, alt,
  placeholder}` portrait shape the roster rows carry.
- The component manifest is `frozen: true`; adding a component requires the manifest entry, a
  Storybook story, and `npm run showcase-coverage`.
- `tests/test_webclient_frozen_contract.py` only requires a hook to be in the audit's frozen list
  when `web/tests/browser/*.py` actually targets it.

## Goals / Non-Goals

**Goals:**

- One top-band surface that renders in every mode, including creation — the roster panel is
  mode-independent precisely so a player who abandoned a wizard can get back out.
- Render strictly from the committed panel. No client-mined character data, no optimistic
  selection, no locally invented ordering.
- One shared lock note, one shared capacity note; no per-row badges.
- A confirmation gate on creation and only on creation.
- Full keyboard parity and correct behaviour when disconnected.

**Non-Goals:**

- No per-character status in the rows (HP, location, last played). The panel does not carry it and
  the surface must not invent it.
- No character deletion, renaming, or reordering controls.
- No drag-to-reorder, no favourites, no "last played" sort.
- No switcher in the Telnet surface.

## Decisions

### D1 — The switcher lives in `TopBar.vue`, not in a HUD island

The top band is where account-level identity belongs and it is the one region already reserved
above the island anchors. Putting it in `hud-right` would place account-scope state inside a
per-character island stack that is mode-gated and scrollable, and it would compete with the
minimap and objective tracker for vertical room.

Consequence to verify rather than assume: the band now holds brand + meta pill + switcher. The
requirement that no stage anchor's rendered box intersects another's is asserted at 1440x900 and
1280x720; at 1280x720 the collapsed pill must fit beside the meta pill. The collapsed form is
therefore bounded — a thumbnail plus a name truncated with ellipsis at a fixed max width — rather
than sized by the character's name.

### D2 — The dropdown is a popover above the islands, not a band-expanding element

Expanding downward from `top:16px` crosses `top:64px`, where `hud-right` begins. The dropdown is
absolutely positioned relative to the switcher at a higher `z-index` than the islands, so it
overlays them transiently instead of pushing the band's height into the anchor region. The band's
own box does not change when the dropdown opens, so the anchor-overlap assertion stays about
static layout.

It closes on Escape, on outside pointer activation, and on any committed epoch change (a completed
switch closes it, because the whole roster re-commits under a new epoch).

### D3 — Both the collapsed label and the rows read from the roster panel

The collapsed pill's name and portrait come from the roster row whose `current` flag is set, not
from `status.actor.name` or the `character` panel. One source means the pill and the highlighted
row can never disagree, including in creation mode where the character panel is unavailable but
the roster is not.

When the roster panel is unavailable, the entire switcher renders nothing — not an empty pill and
not a placeholder. An unreadable account is a state in which offering character controls would be
a lie.

### D4 — The lock is one note, sourced from the panel

When `rosterSwitchLocked` is true every non-current row is disabled and one shared inline note
renders the panel's own `rosterLockReason` string. The client does not compose the reason text and
does not derive the lock from the combat mode itself — it renders the committed field. If a future
lock reason appears server-side, this surface needs no change.

Similarly, the create row's disabled reason 「角色數量已達上限」 renders from `!rosterCanCreate`;
the surface does not compute capacity from `rosterCharacters.length` against
`rosterMaxCharacters`, so the two can never disagree with the server's own answer.

### D5 — Creation is confirmation-gated; switching is not

Creating leaves the current character to enter a wizard — an accidental click on a row adjacent to
the character list has a disproportionate effect, and the original design fixed this as D5. The
confirmation follows the established Forfeit pattern: an explicit panel naming what happens, a
cancel row, a confirm row, and dispatch only from confirm. Escape leaves it without dispatching.

Switching is a single activation. It is reversible, it is already refused during combat by the
server, and requiring two clicks for the surface's primary action would be friction without a
corresponding risk.

### D6 — Pending rows carry a stable marker, not a synthesized name

`multichar-02`'s D5 leaves name disambiguation to the client, because a shell that has not been
activated still carries the account's name as its object key. The row renders the committed `name`
plus a stable 「建立中」 marker when `pending` is set. Activating such a row switches to it and
lands in the creation wizard through the ordinary creation-mode snapshot — the abandoned-wizard
resume path falls out of the existing machinery with no bespoke code, which is the original
design's D12.

### D7 — Dispatch goes through the store's single entry, with no local optimism

Row activation calls `store.dispatchAction('account.character.switch', { character_id })`; the
confirm control calls `store.dispatchAction('account.character.create', {})`. Neither pre-selects
a row, pre-marks a pending state, or hides the dropdown on dispatch alone — the surface changes
only when a commit lands. The store's existing gates (disconnected, locked, one in flight) are the
only debouncing; the component adds none.

### D8 — Showcase and browser-hook lockstep

`Core/CharacterSwitcher` joins the frozen manifest (44 → 45 required components) with a story
carrying deterministic offline fixtures for collapsed, expanded, combat-locked, capacity-reached,
pending-sibling, and disconnected states. The surface is not on the deferred list and must not be
added to it — it is fully backed by the committed `roster` panel.

If a managed browser slice under `web/tests/browser/` targets any of the new `data-testid` hooks,
the frozen contract audit's §2.3 list must gain them in the same change, because
`tests/test_webclient_frozen_contract.py` enforces that every managed browser target appears
there. If no browser slice targets them, the audit is untouched.

## Risks / Trade-offs

- **Top-band crowding at 1280x720.** → Mitigation: the collapsed form is width-bounded with
  ellipsis truncation, and the anchor-overlap assertion is extended to the top band's three
  elements at both asserted viewports (D1).
- **A popover overlaying the HUD islands can hide the minimap or the tracker while open.** →
  Accepted: it is transient, closes on Escape and on outside activation, and the islands it covers
  are display-only. The alternative — reserving permanent vertical space — would cost the islands
  room at every moment instead of only while the menu is open.
- **A switch takes a visible moment** (result, then detach, then a fresh snapshot). During the
  detached window the store locks mutations and clears panels, so the stage briefly empties. →
  Mitigation: this is the same visible sequence Telnet `離開角色` / `進入世界` already produces and
  the connection-loss lock already covers; the switcher's controls are disabled throughout it by
  the existing gate, so no second switch can be started mid-transition.
- **The dropdown's row count is bounded by the server cap (≤10).** → No virtualization is needed
  and none is built; a fixed max-height with internal scrolling covers the ceiling.
