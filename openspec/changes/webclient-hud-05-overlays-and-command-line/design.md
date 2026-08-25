## Context

H1 is landed and archived, so the container exists. `HudFrame.vue:182-188` already reserves the
command line's anchor — `left:0; right:0; bottom:0; height:46px; z-index:6`, the draft's geometry
exactly — and H1's task 2.7 parked the *existing* `CommandDrawer` inside it unchanged, explicitly
deferring the chrome to this wave. `HudFrame.vue:195-199` already hides that anchor in creation mode
with `display:none`. H5 therefore changes what lives in the anchor, not the anchor.

What lives there today is a `<button class="drawer-entry" aria-expanded="false">指令輸入（/）</button>`
and, only while `open` is true, the prompt line, `#inputfield` and the send button
(`CommandDrawer.vue:140-196`). The field is genuinely absent from the DOM in the closed state. Every
entrance path — `/`, the button, and a dock borrowing the drawer for free-form dialogue — is really an
*open* operation followed by a focus operation, and `AppShell.vue:155-162` implements `/` as
`toggleDrawer()`. The draft has no such state: `index.html:866-880` is one always-present bar holding
`.verbs`, `.cmdfield` (chevron + input + hint) and `.hist`.

The overlays are a different kind of gap. `MapOverlay.vue`, `SettingsOverlay.vue` and `HelpOverlay.vue`
are finished components with tests, stories and manifest entries, and nothing imports them. Each
carries its own ad-hoc modal chrome: `MapOverlay` is `position:absolute; inset:0; z-index:50` with a
close button and no focus trap; `SettingsOverlay` is `z-index:40`, same; `HelpOverlay` declares
`aria-modal="true"` with no trap behind it. Meanwhile H1 shipped a *fourth* full-screen overlay,
`FullLogOverlay.vue`, with a real (if two-element) trap at `:46-70`, and H4 extracts that into
`components/focus-trap.js` and re-points `FullLogOverlay` at it. Wiring three more overlays with three
more chromes is exactly the divergence H4's D5 says it is buying H5 out of.

Three verified facts shape the rest of the work.

`options.dismiss` is the only allowlisted `options.*` action (`web/webclient/actions/registry.py:350`;
the docstring at :88 enumerates the whole allowlist). `SettingsOverlay.vue:74` emits
`options.type_scale`. That dispatch is rejected by the allowlist; it has never fired because the
component has never been mounted. Roadmap §3 forbids a wave from touching the allowlist.

`--prose-scale` does not exist. `grep -n "prose-scale" web/webclient-app/styles/tokens.css` is empty
after H1. In the draft it is a `:root` variable multiplied into exactly four declarations —
`.feed .log`, `.feed .log .sys`, `.dlg .say` and nothing else — i.e. narrative and dialogue prose, not
UI text.

The persistence lane is already built and unused. `layout_store.js:50-53` allowlists exactly two
harmless display preferences, `text2html` and `fontScale` (bounded 0.5–2.0 at :36-37), inside a
2048-byte versioned wrapper. Nothing in the Vue client has ever written either.

Constraints inherited from the roadmap: no server, protocol or read-model change; preserve the DOM
contract identifiers and re-map everything else to `data-testid`; each wave re-maps the browser
assertions it breaks in its own change; both 1440×900 and 1280×720; the client stays shippable at every
landing; a surface with no backing read model is absent, never mocked.

## Goals / Non-Goals

**Goals**

- Replace the collapsed drawer with the draft's always-visible command line, at parity of every
  keyboard behaviour, with `#inputfield` unmoved.
- Decide `/` deliberately and state its keyboard-contract consequence, rather than leaving a toggle
  that now has nothing to toggle.
- Give the three built overlays real triggers and **one** modal contract, generalised from what H1 and
  H4 already built rather than invented a third time.
- Make the settings surface honest: nothing it offers may be inert, and nothing it offers may claim a
  server round-trip it cannot make.
- Ship `--prose-scale` as a real, persisted, narrative-scoped preference.
- Advertise no affordance this change does not implement, even where the draft draws one.

**Non-Goals**

- The dock's frames, tabs, badges, breadcrumb or keyboard geometry (H3). The quick-word chips live on
  the command line and are not router rows.
- The reference drawers, their scrim, and `focus-trap.js`'s trap semantics (H4). H5 consumes the trap.
- The HUD island stack, the vitals and the condition chips (H2). H5's one cross-wave edit is the
  minimap island's full-map control, which H2 deferred here by name.
- Any new read model. No companion strip, no toast queue, no objective tracker, no game-help browser.
- Any change to the narrative markup allowlist grammar. The text-to-HTML preference chooses whether the
  pipeline runs, never what it permits.
- Tab completion, in any form.

## Decisions

### D1 — The field is permanently present; the entry button and the open state are removed

`CommandDrawer.vue` becomes `CommandLine.vue`: one bar rendering the chip cluster, `›`, `#inputfield`
inside its preserved `.inputfieldwrapper`, the hint cluster, the history controls and the utility
controls, with no conditional branch. The `open` prop, the `toggle` emit, the `drawer-entry` button and
its `aria-expanded` state all go. `AppShell`'s `openDrawer` / `closeDrawer` / `toggleDrawer` collapse
into `focusCommandField()` and `releaseCommandField()`, and `defineExpose` publishes those instead, so
the dock's free-form borrow still has one call to make.

*Rationale:* the entry button exists in the current spec for one stated reason — *"so the drawer stays
discoverable and a stale localStorage layout never removes the entry point."* A field that is never
removed satisfies that requirement more strongly than a button that guards a removable one, and the
`aria-expanded` state is a lie once nothing collapses.

*Alternative rejected:* keeping the button as a redundant focus affordance beside the visible field.
It would leave `aria-expanded` describing a state that no longer varies, and it puts two tab stops on
the same action.

### D2 — `/` focuses the field; it never toggles and never types a slash

Outside an editable, `/` moves focus into `#inputfield` and calls `preventDefault()` so no literal `/`
is inserted. Inside **any** editable — the command field included — `/` is ordinary text and is never
claimed by the router, so `whisper /ooc` and `cast 火矢=e1` stay typeable and a second `/` while the
field is focused simply types a slash.

The keyboard-contract consequence, stated so it is not rediscovered later: **`/` loses its return
path.** Today `/` is the way in *and* the way out. After H5 the only key that leaves the field is
Escape, which returns focus to `#action-dock` — the behaviour the current spec already requires and
which is therefore load-bearing for the first time. The `MODIFIED` requirement says so explicitly, and
a browser assertion covers "`/` then Escape returns to the dock" as a round trip.

*Rationale:* a toggle needs two states. Making `/` close-and-blur when pressed a second time outside
the field would be a phantom of the removed state, and making it insert a slash when the field is
already focused is what the unchanged editable rule already produces.

*Alternative rejected:* `/` clears the field and focuses it. It destroys a half-typed command with a
key a player may press by reflex, and it makes `/` a mutation rather than a navigation.

### D3 — Escape is one precedence ladder, evaluated topmost-first

`topmost open full overlay → open drawer (H4) → focused command field → dock menu level`. Each rung
consumes the key and stops. The overlay and the drawer already own Escape while they hold trapped
focus (H4 D4), so the ladder is a statement of what *is*, not a new dispatcher — but stating it is what
keeps H5 from adding a fourth Escape owner. The command field's rung is the existing
`emit("focus-parent")` path; the dock's rung is `focusEscape()`, untouched.

*Rationale:* three waves now install an Escape handler. Without a written order, "Escape pops exactly
one menu level" and "Escape closes the overlay" both look correct in isolation and race in practice.

*Alternative rejected:* a central key dispatcher owning Escape for every surface. It would move the
key out of the trapped surfaces that already own it and require H4's landed contract to be reopened.

### D4 — A chip's label is the command it inserts, drawn from the installed command set

Each chip writes its verb plus a trailing space into the field and focuses it. It never submits: a
prepared command still travels through Enter and the single send implementation, so there is exactly
one send path. The v1 sets are:

| mode | chips |
|---|---|
| exploration | `看` `拿` `說` `交談` `等待` |
| combat | `說` `施法` |

These are the localized command keys the server actually installs (`commands/localized/general.py:170,
199,260`, `commands/talk.py:78`, `commands/skip.py:70`, `commands/action.py:28`). **The draft's `走`
and `問` chips are dropped**: `grep -rn '^    key = ' commands/` shows no `go`/`goto` command and no
`ask` command in this game. Movement is by exit name through the dock's 移動 frame, and NPC keyword
conversation is `交談`. A chip that types a verb the parser rejects is worse than no chip.

The draft's icon plus mnemonic key badge (`.verb b`) is **not** rendered. The draft's own script never
binds those letters, and binding six bare letters globally would claim keys that today fall through to
the text and command-history path — a keyboard-contract change H5 has no mandate for. Because the label
*is* the verb, the mnemonic has nothing left to teach.

*Alternative rejected:* keeping the draft's five exploration chips verbatim and letting `走`/`問` submit
into the parser's error path. It is the draft's literal pixels and it teaches the player two commands
that do not exist.

### D5 — The hint cluster advertises only what ships; the history buttons are the pointer path to the keys

The hint renders `↑↓ 歷史` and nothing else. The draft's `Tab 補全` is dropped: the draft never
implements completion, this change does not implement completion, and there is no completion source
(the action allowlist is server-side and the dock is the completion surface this client actually has).
The up/down controls are real `<button>`s carrying 上一筆 / 下一筆 accessible names that drive the same
history-walk state ArrowUp/ArrowDown drive — one walk, two input paths, exactly the pointer-parity model
`webclient-pointer-activation` requires — and they never submit.

When horizontal space runs short (1280×720 with the full chip set) the **hint cluster** is the first
element dropped, then the chip cluster scrolls; the field keeps a floor width and the history and
utility controls are never dropped, because they are the only pointer path to their behaviour.

*Alternative rejected:* rendering `Tab 補全` as aspirational chrome. It is the exact failure the roadmap's
truthful-data rule exists to prevent, applied to affordances instead of data.

### D6 — The borrowed free-form dialogue keeps its contract minus the close

This answers H3's deferred question. A dock free-form affordance still borrows the field: it focuses it,
marks the borrow, and on a successful send clears the field and returns focus to `#action-dock` —
because that interaction has completed. What it no longer does is *close* anything. When the action
client is locked the send does not dispatch, the typed speech stays in the field and focus stays in the
field, so nothing is lost. The borrow is released whenever focus leaves the field for any reason other
than that dock's own successful send, and whenever a send is routed as ordinary text.

*Rationale:* "the drawer closes" was only ever the visible signal that the borrow ended. Focus return is
the part that mattered, and it survives verbatim.

*Alternative rejected:* keeping the borrow alive until the player explicitly cancels. A persistent field
has no "cancel" gesture, so an abandoned dialogue would capture the next unrelated command — the exact
case `webclient-desktop-shell`'s "A cancelled dialogue cannot capture a later command" scenario forbids.

### D7 — One overlay host, one open overlay, registered into H1's existing recession set

`OverlayHost.vue` owns the full-screen surface: `position:fixed; inset:0` above the stage, the draft's
`.full` header row (icon, title, subtitle, labelled close control), a scrolling body slot, focus trapped
through H4's `components/focus-trap.js`, Escape and the close control both closing and restoring focus to
the trigger. `MapOverlay`, `SettingsOverlay` and `HelpOverlay` keep their bodies and lose their own
chrome, `z-index` and close buttons.

**At most one overlay is open**; opening a second closes the first, mirroring H4's single-drawer rule.
An open overlay pushes its name into the open-surface array `AppClient.vue:97-106` already computes, so
H1's `menu-open` recession applies with no second mechanism.

`CreationOverlay` stays outside this stack. It is mounted on `panelAvailable('creation')`, not opened by
a player, and it is the mode's whole surface; making it one of "at most one" would let a settings click
dismiss a character-creation wizard.

*Alternative rejected:* leaving each overlay's own chrome and adding only a trap. Three close buttons,
three z-indices and three Escape handlers would then have to agree, which is the divergence H4's D5
already paid to avoid — and H5 would be the wave that reintroduced it.

### D8 — The store owns the overlay slice, beside H4's drawer slice

`store.openOverlay(name)` / `store.closeOverlay()` over the closed set `map | settings | help`, published
as `view.hudOverlay`, exactly parallel to H4's `openHudDrawer` / `view.hudDrawer`. Opening an overlay
closes any open drawer and vice versa: they are both "the surface laid over the stage", and two of them
at once would nest two focus traps. A mode change into creation, an epoch reset and a transport loss each
force the overlay closed, through the same teardown H4 already routes the drawers through.

*Alternative rejected:* local `ref`s in `AppClient`. Three subtrees need to open an overlay (the minimap
island, the command line, and a future dock row), and exactly one place must be able to force everything
closed on an epoch reset.

### D9 — The map trigger goes on the minimap island, and H5 serializes behind H2

H2's `webclient-local-map` delta says the island *"SHALL present no control for a surface the application
does not mount: a full-map affordance SHALL exist only once the full-map surface it opens is reachable."*
H5 makes it reachable, so H5 adds the control — a labelled `<button>` on the island's header row,
`展開全地圖`, opening the map overlay. It is a **sibling** of the lattice, not a wrapper around it: the
island already contains actionable move nodes, and wrapping interactive content in an interactive
element is the nested-control anti-pattern the composite-widget contract exists to prevent.

`LocalMap.vue` belongs to H2 (roadmap §7), so this is a forced serialize: H5's "Depends on" cell becomes
`H1, H2, H3`, amended in the roadmap per §9 rather than worked around.

*Alternative rejected:* putting the map trigger only in the command line's utility strip and leaving the
island silent. It keeps the file boundary clean and it strands the affordance the draft puts on the
island (`.mini[data-full="map"]`) and that H2 wrote a requirement to enable.

### D10 — Settings and help are reached from the command line's utility strip

Two icon buttons with accessible names 設定 and 說明 sit at the right end of the bar, after the history
controls. They are ordinary tab stops reachable from the field.

Consequence, accepted deliberately: the command line is hidden in creation mode by H1's matrix, so
settings and help are unreachable during character creation. They are unreachable *today* in every mode,
creation is a bounded flow with its own exit, and the matrix is the roadmap's central thesis — a surface
that punches through a mode gate to stay visible is the dimming-instead-of-hiding pattern H1 removed.

*Alternative rejected:* a fourth absolutely-positioned cluster in the 64px top band. The band already
carries the brand (`top:16px; left:16px`) and the meta pill (`top:16px; right:16px`), and the `hud-right`
anchor starts at `top:64px` with H2's minimap in it; a third element there competes for the same strip and
edits H1's `TopBar.vue` for a control that has a natural home in H5's own anchor.

### D11 — The map overlay ships no zoom or pan, and the hint is dropped

The draft's map legend advertises `滾輪縮放 · 拖曳平移` and the draft implements neither. H5 renders neither
the behaviour nor the hint. The `local_map` payload is a single bounded layer whose in-view node span H2's
render model already caps at 64×64 with rank-compression fallback, so a full-screen overlay has room for
the whole lattice without a viewport transform; and a pointer-only pan/zoom would need a keyboard
equivalent to keep parity, which is a real interaction surface for no payload gain.

The overlay must also not reintroduce what H2 removed: no bearing, no compass angle, no distance figure.
Node `x`/`y` are renderer-local presentation geometry. The overlay is the same `LocalMap` component at a
larger size, so it inherits H2's orientation-legend rule rather than restating it.

*Alternative rejected:* shipping wheel-zoom and drag-pan because the draft draws the words. It adds an
interaction the read model does not need and an accessibility obligation the wave has no budget for.

### D12 — Settings are client-local presentation state; nothing dispatches

No settings control emits a `ui_action`. Each is applied to the document's presentation tokens
immediately and persisted through `layout_store.js`'s harmless-display-preference lane. `fontScale`
(bounded 0.5–2.0) carries the prose scale and `text2html` carries the narrative-pipeline toggle — both
keys exist today and have never been written. `reducedMotion` and `colorblind` are **added to
`PREFERENCE_TYPES`**, which is purely additive: `normalizePreferences` drops unknown keys and copies
known ones, so an existing version-1 wrapper without them normalizes cleanly and **no layout-version bump
and no migration are required**. Two booleans are far inside the 2048-byte cap.

The reduced-motion control is an *override* over the OS `prefers-reduced-motion` media query, which keeps
working when no override is stored. This is the honest reading of `webclient-desktop-shell`'s persistence
rule — "harmless display preferences" — and it is why `options.type_scale` was never the right envelope:
there is no server state for any of these to change.

*Alternative rejected:* adding `options.type_scale`, `options.fonts`, `options.reduced_motion`,
`options.text_to_html` and `options.colorblind` to the action allowlist. It is a server change; roadmap §3
forbids every wave from making one, and specifically forbids widening the dispatch surface so a component
compiles.

### D13 — `--prose-scale` is a new token at the draft's three steps, scoped to prose only

`styles/tokens.css` gains `--prose-scale: 1` on `:root`, multiplied into the narrative and dialogue font
sizes only — the caption card's lines, the full-log overlay's lines and the prompt line — never into
`--text-sm` / `--text-body` or any HUD, dock, drawer or overlay chrome. The A−/A/A+ control sets
`[0.92, 1, 1.12]`, the draft's `fsScale` array, replacing `SettingsOverlay`'s inert 90/100/110/125% select.

*Rationale for keeping the scope narrow:* the HUD's geometry is fixed and measured. The command line is
exactly 46px, `--dock-h` is `clamp(150px, 22vh, 184px)`, the left island stack clears the dock by 41px at
1280×720 (roadmap §8), and every wave must re-assert that no stage anchor's box intersects another's at
both viewports. A global UI scale would break that assertion on the first step, for a need — narrative
readability — that the prose scope already meets. Dropping the 125% step follows from the same measurement:
the caption card is height-bounded at 30vh and 1.25 overflows it into internal scrolling on the first line
of a long room description.

*Alternative rejected:* a general `--ui-scale` applied to the root font size. It is what a player asking
for "bigger text" often means, and it invalidates the non-overlap acceptance every wave runs.

### D14 — The `data-testid` retires; the persisted layout component id does not

`data-testid="command-drawer"` and its `-entry` / `-input` / `-prompt` / `-send` children become
`command-line` / `command-line-input` / `command-line-prompt` / `command-line-send`, and this change
re-maps every assertion that uses them (H1's preserved list carried `data-testid="command-drawer"`; H5 is
the wave that retires it, per roadmap §5's "each wave owns the assertions it breaks"). `#inputfield` and
its `.inputfieldwrapper` do **not** move — the key path's drawer-ownership gate identifies the field by
exactly that pair.

`layout_store.js:46`'s `REQUIRED_COMPONENTS` entry `"command-drawer"` also does not move. It is a
persistence identifier inside a versioned wrapper, not a DOM hook; renaming it would invalidate every
stored wrapper for no observable gain and would edit preserved `js/elosern/*` logic beyond the additive
`PREFERENCE_TYPES` entries of D12. `webclient-desktop-shell`'s required-surface list therefore stays
literally true: the surface is still provided, and its self-identifying content is still the prompt line.

*Alternative rejected:* renaming the persisted id in lockstep for tidiness, with a layout-version bump and
a migration. It is churn with a migration test attached and zero user-visible effect.

### D15 — The help overlay renders the client's own control reference, not invented game help

`HelpOverlay.vue`'s `guide` prop is backed by nothing. The eight allowlisted panels are `art`, `status`,
`context_actions`, `local_map`, `services`, `creation`, `exploration`, `character`
(`web/webclient/presentation/registry.py:191-253`); none carries an onboarding guide, and
`stories/fixtures.js:1009`'s `ONBOARDING_GUIDE_SAMPLE` is a Storybook fixture. Mounting the overlay with an
empty `guide` renders a frame and a close button.

H5 therefore gives the overlay a section it can tell the truth about: the **client's own control
reference** — the keys this client implements (arrow keys, Enter, Escape, `/`, ArrowUp/ArrowDown history),
the dock's navigation model, the quick-word chips and the drawer/overlay close paths — generated from one
client-local constant module, `lib/controls-reference.js`. That is client-authoritative knowledge, not game
data, so it is not a mock. The `guide` sections keep rendering only when a payload supplies them (never
today), and the game's own `help` output stays reachable by typing `help` into the field, which the overlay
says in one line.

The draft's 分類 → 條目 → 子主題 game-help browser is named in the deferred-surface assertion with what it
waits on: an OOB panel carrying `help` content.

*Alternative rejected:* shipping `ONBOARDING_GUIDE_SAMPLE` as live copy. It is the fixture the showcase
uses, it would present authored South-Gate guidance to a player standing anywhere in the world, and it is
precisely "a component faked to look real".

## Risks / Trade-offs

- **Risk: a permanently focusable field swallows keys the router needs.** A player who clicks the field
  and then presses ArrowDown expecting the dock gets a history walk instead. → **Mitigation:** the field
  is a normal tab stop and never auto-focuses; focus lands on `#action-dock` after synchronization and
  after every action, unchanged. Escape from the field is the single documented return path (D2), it is
  covered by a browser round-trip assertion, and the dock's guidance line already names it.
- **Risk: H5 breaks the largest concentration of browser assertions in the suite.** Nine files, ~90
  matches. → **Mitigation:** `#inputfield` does not move, which is where most of the matches actually
  are; only the `data-testid` family and the entry-button/`aria-expanded` cases change; all of it is
  re-mapped in this change, and `tests/preserved_contract.test.js` fails at the unit gate rather than in
  Playwright if a preserved identifier moves.
- **Risk: editing `LocalMap.vue` collides with H2.** → **Mitigation:** it is a forced serialize, declared
  in the proposal and amended into the roadmap's dependency cell (D9). The edit is one control on the
  island's header row and touches neither the render model nor the lattice.
- **Risk: two focus traps could nest (a drawer open behind an overlay).** → **Mitigation:** D8 makes the
  overlay slice and the drawer slice mutually exclusive in the store, and a Vitest asserts that opening
  one closes the other; the Escape ladder (D3) is then unambiguous because at most one trapped surface
  exists.
- **Risk: the settings surface silently loses behaviour players could see in Storybook.** The font-family
  select and the 90/100/110/125% steps disappear. → **Mitigation:** both were inert; the change is
  recorded in the `webclient-component-showcase` `MODIFIED` delta and in the overlay's own Vitest, so no
  window exists where the spec promises a control the surface does not have.
- **Risk: `--prose-scale` at 1.12 overflows the 30vh caption card.** → **Mitigation:** the card already
  scrolls internally within its bounded height (H1's landed requirement) and the full log is one action
  away; the browser acceptance asserts the caption stays bounded and non-overlapping at both viewports at
  **each** of the three scale steps.
- **Risk: settings that persist through the layout store are lost on a version reset.** → **Mitigation:**
  that is the landed contract ("unknown versions SHALL reset to the version-1 default"), it is stated in
  the requirement, and every preference re-applies its default at load rather than leaving the document in
  a half-applied state.
- **Risk: the utility strip's mode gating hides settings and help in creation.** → **Mitigation:**
  accepted and stated (D10); creation is bounded, the controls are unreachable in every mode today, and
  H6 owns the final audit of what each mode must reach.

## Migration Plan

No data migration and no layout-version bump: 0 released users, and D12's two new `PREFERENCE_TYPES` keys
are additive over a version-1 wrapper that simply lacks them. A wrapper carrying an unknown version still
resets to the version-1 default, unchanged.

Landing order inside the change is the tasks order: the preserved-identifier freeze first, then the
command line (the client is fully operable the moment it lands, because the field it replaces was optional
chrome around the same `#inputfield`), then the overlay host and the three wirings, then settings and the
prose scale, then the browser re-map. Rollback is `git revert` of the change: `#inputfield`, the store's
dispatch path, the transport, the bridge and the KeyboardRouter are untouched, and the persisted wrapper
written by a reverted build normalizes cleanly against the older allowlist because unknown keys are
dropped.

## Open Questions

None blocking. Four deferred:

1. Whether the dock's guidance line should be generated from `lib/controls-reference.js` so it cannot
   drift from the help overlay's control section — **H6**, which owns the final contract audit; H3's dock
   hint is left byte-identical here.
2. Whether the drawer width becomes a user preference alongside `--prose-scale` (H4's open question 3) —
   **answered: no.** The draft fixes the drawer at `min(560px, 94vw)`, a second stored preference buys a
   third `PREFERENCE_TYPES` key and a bounds test for a dimension the design reference does not vary, and
   nothing in the read models depends on it.
3. Whether the full-log overlay should adopt `OverlayHost`'s chrome as well — deferred to **H6**, which
   re-freezes the component set; H5 re-points nothing H1 shipped beyond what H4 already re-pointed.
4. Whether a game-help browser becomes buildable — it waits on an OOB panel carrying `help` content, which
   is a server-side delivery unit, not a view wave.
