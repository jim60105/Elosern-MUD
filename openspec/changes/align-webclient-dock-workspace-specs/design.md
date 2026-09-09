# Design: align-webclient-dock-workspace-specs

## D1 — The band is one property; the delta pins the coupling, not the pixels

The whole geometry repair reduces to one fact: the stage carries a single
`--dock-h` custom property that both the dock's height and the narrative
feed's bottom anchor read, and CSS `:has()` selectors on the stage retarget
that property per rendered frame (interaction workspace, waiting frame,
combat, empty combat pane). Pinning the exact clamp constants in the spec
would freeze design tuning forever; pinning only "surfaces are visible" let
the overlap class of bugs ship silently. The delta therefore pins the
observable coupling — one band, per-frame adaptation in a named size order,
feed never overlapping dock, pane contents scrolling inside the band while
the tab bar and breadcrumb stay fixed — and names the shipped constants as
the implementation's current choice.

## D2 — The workspace clause extends the existing interact sentence, not a new requirement

The synced dock requirement already owns the interact composition ("first
select a present target and then show only that target's server-authored
affordances"). The workspace is that composition's rendered form, so it joins
that requirement's paragraph as one clause plus one scenario rather than a
sibling requirement — the same place a future re-layout would have to amend.
The anchor widening (waiting/interaction frames extending the dock band to
the left HUD column edge) is observable non-overlap behavior for the same
two frames and rides the same clause.

## D3 — Dialogue-mode boundedness belongs to the shell, not the dialogue capability

The bounded dialogue feed is a stage-anchor geometry fact (`[data-anchor="feed"]`
height clamp in dialogue mode), owned by `webclient-desktop-shell`'s
required-surfaces requirement. `webclient-dialogue-session` owns session
state, the panel contract, and the leave action — not layout. No delta is
filed there.

## D4 — Evidence is the shipped layout assertions

The repair round's verification (three viewports, no horizontal document
overflow, tab/content and feed/dock non-overlap, last option scroll-reachable)
was live-browser evidence; the durable regression net is the Vitest layout
suite (`tests/action/action_dock.test.js`, `tests/components/dock_panes.test.js`)
plus the managed browser acceptance rows this capability class already owns.
This change ships no code, so it adds no new test obligations; the delta
scenarios are written so the existing managed browser geometry checks map to
them without re-derivation.
