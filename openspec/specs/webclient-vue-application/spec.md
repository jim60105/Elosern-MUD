## Purpose

Establishes the offline loading contract for the WebClient's Vue 3 single-page application: a locally built, self-contained Vite bundle served entirely from the project origin with no remote runtime UI dependencies, desktop-only bounded rendering at 1440x900 and 1280x720, and the retirement of the replaced stock and pre-Js text fallback on mount. It also carries the design system over from the 設計稿: the ink-night palette with a single seal-red accent, self-hosted display, serif, sans, and monospace typefaces, focus, selection, and motion tokens, status and health information never conveyed by color alone, and reduced-motion honor. It also preserves the client DOM contract hooks (action-dock target, item keys, `data-testid` hooks) and the stable public façades as browser-bridge shims. It also fixes the C4 flip contract: the view layer is fully reactive and store-bound, no legacy imperative view-plugin code remains in the load path, and every activation emits at most one request.

## Requirements

### Requirement: Chrome type is legible and numerals are stable
At the reference scale chrome text SHALL render at least 12 CSS pixels using the shared local design faces, including the minimap island's title, orientation marks and readout and the full-map overlay's guide, input hint, view controls, legend and remembered list. The only text outside that floor is the drawn map itself — the node labels and edge-marker names inside the island's and the full map's SVG drawing — whose sizes follow the `webclient-local-map` fitted label contract (island node labels at a 12-unit step drawn at 12 × the drawing's scale, island marker names at a 10-unit step). Resource values, costs, counts and prices outside the drawn map SHALL use proportional sans tabular lining numerals. Monospace SHALL remain reserved for command input, ASCII/box-drawing content, key names and the map's own coordinate and label type; prose SHALL retain its existing reader sizing contract, including viewport-relative sizing and prose-scale preferences.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces, the minimap island and the full-map overlay render at 1920x1080
- **THEN** chrome text outside the drawn map meets the 12px floor without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace

### Requirement: The WebClient loads a self-contained offline Vue SPA
The project WebClient SHALL load a locally built, self-contained Vue 3 single-page application produced
by a Vite build and served entirely from the project origin. The page SHALL make no remote request for
a runtime UI dependency (no CDN JavaScript, CSS, or font). The application SHALL target desktop only and
SHALL NOT claim mobile acceptance; every required surface SHALL be visible and usable at 1440x900 and
at 1280x720. When the application mounts into its container, the stock and pre-Js text fallback it
replaces SHALL be retired so it cannot stack in document flow and push required surfaces below the
visible viewport. (The live evennia-transport mount and the always-playable text path are established by
later changes in this migration; this change establishes the offline build and render of the app.)

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the Vue application is loaded with all non-local network requests blocked
- **THEN** the Vite-built Vue bundle, its styles, and its self-hosted fonts load from the project origin without a CDN failure

#### Scenario: Desktop-only bounded render at each supported viewport
- **WHEN** the Vue application renders at 1440x900 and at 1280x720
- **THEN** every required surface is visible and usable without overlapping the input path, and the application makes no mobile-behavior claim

#### Scenario: Mount retires the replaced text fallback
- **WHEN** the Vue application mounts into its container
- **THEN** the stock and pre-Js text fallback it replaces is hidden so it does not stack with the mounted application

### Requirement: The design system carries over from the design draft and stays offline
The Vue application SHALL render with the approved design system derived from the 設計稿
(`docs/design/elosern-redesign/`), and that draft SHALL be the binding reference for **both** the visual
system and the application's layout and information architecture — its palette, typefaces, and tokens,
and equally its stage composition, surface anchoring, and mode-gated visibility model. The application
SHALL render with the ink-night palette, its seal-red accent retained for its semantic roles beside a
muted-gold navigation, focus, and emphasis accent, the self-hosted display, serif,
and sans typefaces, and the focus, selection, and motion tokens. Status and health information SHALL
never be conveyed by color alone (an icon or symbol plus a numeric value or an explicit text label is
required), SHALL honor `prefers-reduced-motion`, and SHALL remain legible for common color-vision
differences. No design asset or font SHALL be fetched from a remote origin at render time. Where this
capability and the draft are silent on a visual or navigational detail, the draft governs; a surface in
the draft that has no backing OOB read model SHALL NOT be built and SHALL NOT be mocked.

#### Scenario: Self-hosted fonts load offline
- **WHEN** the application loads with remote requests blocked
- **THEN** the display, serif, and body fonts render from the project origin

#### Scenario: Status is not color-only
- **WHEN** a gauge, condition, or health state is displayed
- **THEN** it pairs an icon or symbol with a numeric value or an explicit text label instead of relying on color alone

#### Scenario: Reduced motion is honored
- **WHEN** `prefers-reduced-motion` is set
- **THEN** non-essential animation transitions are disabled

#### Scenario: The draft is the binding layout reference
- **WHEN** the application composes its surfaces
- **THEN** it renders the draft's stage composition and mode-gated visibility model, not a fixed multi-column dashboard

#### Scenario: An unbacked draft surface is absent rather than mocked
- **WHEN** the draft shows a surface with no backing OOB read model
- **THEN** the application renders no such surface and presents no placeholder standing in for its data

### Requirement: The Vue app binds the preserved strict DOM-independent logic to a reactive store
The Vue application SHALL use a single reactive store (Pinia) as the sole writer of client view state.
The store SHALL consume the preserved DOM-independent logic — the protocol reducer, the keyboard router,
the narrative markup pipeline, the local-map model, and the choice-point and option-card logic — through
ES-module wrappers rather than reimplementing it. The store SHALL publish committed state atomically so
that no subscriber observes partially applied panel state, and it SHALL hold only data derived from the
OOB panel allowlist (art, status, context_actions, local_map, services, creation, exploration,
character) and the transport text stream; it SHALL NOT invent data. Components emit only user-intent
dispatches, and the store is driven in tests by raw reducer inputs; binding the live transport and the
components to this store are established by later changes.

#### Scenario: Renderers observe only committed state
- **WHEN** a valid snapshot or update is accepted by the preserved protocol reducer through the store
- **THEN** the store publishes one commit of completely replaced panel state and no subscriber observes partially applied state

#### Scenario: Stale epochs and revisions are rejected
- **WHEN** an old-epoch snapshot or a stale active-epoch revision is presented to the store
- **THEN** the store discards it and preserves the last committed state

#### Scenario: The store holds only backed data
- **WHEN** the store receives panel data
- **THEN** it holds only data sourced from the OOB allowlist or the transport text stream and holds no invented data

### Requirement: The app preserves the client DOM contract hooks and exposes stable test hooks
The Vue application SHALL preserve the DOM contract identifiers that the OOB and browser contract depend
on: the focusable action-dock target that the keyboard router dispatches into, the `action-` and `target-`
item keys selected by pointer or keyboard, and the identity of the required panel surfaces. The application
SHALL expose a stable `data-testid` hook on every remaining interactive surface so behavioral browser
acceptance targets deterministic hooks rather than styling selectors. The application SHALL also preserve
the stable public façades that existing OOB and browser contracts reference — the narrative input/append
path (`window.Elosern.narrativeInput`), the action submission entry point (`window.Elosern.actions.submit`),
and the keyboard-router consumption contract — implemented as browser-bridge shims over the store and the
imported logic, so existing behavioral tests and the choice-point/narrative append path keep their single,
non-duplicated entry points while the DOM is implemented in Vue.

#### Scenario: Keyboard router reaches the same dock
- **WHEN** the application renders the active menu frame and the player focuses the preserved action-dock target
- **THEN** a key press dispatches through the keyboard router to the focused item

#### Scenario: Pointer chooses by the stored key with keyboard parity
- **WHEN** the player clicks an action or target row
- **THEN** the `action-` or `target-` item key is used and the chosen item equals the item a keyboard journey would reach

#### Scenario: Interactive surfaces carry stable hooks
- **WHEN** any required interactive surface renders
- **THEN** it exposes a stable, unique `data-testid` identifier usable by automation

#### Scenario: Existing façade contracts hold
- **WHEN** an existing browser test or spec references the `window.Elosern.narrativeInput` narrative append path or the `window.Elosern.actions.submit` action entry point
- **THEN** those contracts resolve and route through the store and the single bridge dispatch path (the live transport round-trip is proven by a later change) with no duplicated append or action path

### Requirement: Degraded text remains playable alongside the Vue shell
The application SHALL remain fully playable by ordinary text commands when the Vue graphical surfaces are
unavailable, when the Vite bundle fails to load, or when the OOB channel is incompatible. An incompatible
or failed OOB presentation SHALL lock the graphical controls while leaving the text path functional.
Narrative and command output SHALL remain the authoritative text surface and SHALL degrade a message that
cannot be fully tokenized to readable literal text rather than suppressing the log.

#### Scenario: Bundle blocked keeps text playable
- **WHEN** the Vue bundle cannot load
- **THEN** ordinary text commands can still be sent and rendered and no required input path is lost

#### Scenario: Incompatible OOB locks graphical, keeps text
- **WHEN** the application receives an unsupported protocol version
- **THEN** graphical actions are disabled and locked while a text command round-trips and renders normally

#### Scenario: Unparseable message degrades to literal text
- **WHEN** a message cannot be fully tokenized by the markup pipeline
- **THEN** the narrative shows readable literal text rather than being suppressed

### Requirement: The view layer is fully reactive and store-bound with no legacy imperative view plugin
Every player-facing Vue surface SHALL be a reactive component that renders committed state from the Pinia
store and dispatches only through the allowlisted action path; no component SHALL mutate store or server
state directly, and no legacy imperative view-plugin code (the retired GoldenLayout/jQuery dock and
`elosern_ui` view files) SHALL remain in the client load path. The keyboard router SHALL keep focusing the
preserved action-dock target, and every activation SHALL emit at most one request.

#### Scenario: A control emits one dispatch only
- **WHEN** the player activates a dock item, verb, skill, or target control
- **THEN** exactly one allowlisted OOB action envelope is dispatched and no local model mutation occurs

#### Scenario: No legacy view code is loaded
- **WHEN** the production client load path is inspected
- **THEN** the retired GoldenLayout/jQuery dock and `elosern_ui` view files are not loaded and every
  interactive surface is a store-bound Vue component

#### Scenario: Single request per deliberate activation
- **WHEN** a mutation control is activated rapidly or a held key repeats while a submission is in flight
- **THEN** at most one request is emitted until the action's declared presentation revision is accepted

### Requirement: The character UI renders server breakdown without recomputation

The Vue application SHALL render character stat rows from the version-5
payload's `layers` in payload order with verbatim registry names and
kind-formatted signed amounts, SHALL render ALL layers without
truncation, SHALL NOT sort, recompute, regroup, or re-total layer data,
and layer-free rows SHALL keep their existing value text with no
breakdown elements rendered. Equipment rows in the doll and inventory
surfaces SHALL print the server-generated adjustment string verbatim (the
inventory sources it by joining the server's character equipment rows on
`item_key`; a bag-only item renders none; empty renders nothing), and the
intimate view SHALL show the payload's effective exposure value. Only
schema version 5 SHALL be accepted at every wire validator; an unknown
layer `source`/`kind` SHALL still be rejected on the wire, and neutral-
chip fallback exists only as direct-render defense in the component.

#### Scenario: Layer chips mirror the payload exactly

- **WHEN** the drawer renders a defense row whose payload layers are a
  skill mult, a condition flat, and an equipment flat in that order
- **THEN** three chips appear in that order with the payload names and
  kind-formatted amounts, and the value line keeps the existing gauge or
  static text

#### Scenario: No layers, no breakdown elements

- **WHEN** a stat row carries an empty layers list
- **THEN** the value line is unchanged from today and no chip container or
  wrapper element renders

#### Scenario: Adjustment text is verbatim and joined

- **WHEN** an equipped item's character row carries 「攻擊 −2｜防禦 +8｜
  敏捷 −10%｜生命上限 +15」 and the same item appears in the inventory
  equipment list
- **THEN** doll and inventory both print exactly that string, and a
  bag-only item prints nothing

#### Scenario: Effective exposure is proven, not vacuous

- **WHEN** the fixture carries a worn bias-bearing item whose stored-base
  exposure differs from the effective ordinal
- **THEN** the intimate view renders the effective ordinal and the stored-
  base ordinal is asserted absent

#### Scenario: Version 4 payloads are rejected at every wire

- **WHEN** a character payload at schema version 4 reaches the Vue store
  path or the legacy client, or a v5 payload carries a layer with a source
  outside the closed set
- **THEN** every wire validator rejects it; only a direct component render
  with hand-built props exercises the neutral 其他 chip fallback while the
  value line stays correct

### Requirement: Desktop chrome scales once from the reference viewport
At 1920x1080 the client SHALL use its reference chrome dimensions; at 2560x1440 comparable chrome text, controls, spacing and bounded islands SHALL render at four thirds of their reference dimensions within rounding tolerance. Below the reference height, or on a viewport narrower than its height would imply at 16:9, chrome SHALL not shrink below its reference readability floor nor grow beyond the width's own ratio to the 1920px reference. Viewport-responsive prose, stage art and band geometry SHALL NOT be multiplied a second time.

#### Scenario: Large desktop is proportional
- **WHEN** the same scene renders at 1920x1080 and 2560x1440 with the same reader preference
- **THEN** top navigation, control targets, map island and drawer header dimensions have a 4/3 ratio within 2 CSS pixels while art and prose scale exactly once

#### Scenario: Reader preference is independent
- **WHEN** the player changes only prose scale at fixed viewport size
- **THEN** message/log prose changes but chrome geometry does not

#### Scenario: Resize preserves hit testing
- **WHEN** a user resizes between acceptance dimensions and then selects a map node or command
- **THEN** the visible target receives the intended existing action and no stale geometry or duplicate dispatch occurs

### Requirement: The monospace type role is a self-hosted, sliced Jim Mono TC face
The Vue application SHALL render its monospace type role (the command line, keycaps, option and badge
numerals, local-map labels, and box-drawing map art) with the Jim Mono TC typeface served from the
project origin, so Latin, digits, box drawing, and CJK in a monospace surface come from one bundled
family in which every East Asian Wide or Fullwidth character is exactly two Latin cells wide, in both
the regular and the bold weight. The monospace stack SHALL NOT name any machine-installed font family
ahead of the bundled faces; the already self-hosted Noto Sans TC MAY follow it only as the fallback for
CJK outside the shipped coverage. Jim Mono TC SHALL be delivered as unicode-range woff2 slices, each no
larger than 64 KB, so a page downloads only the slices whose characters it draws, and each weight SHALL
ship every East Asian Wide or Fullwidth code point of the bundled Noto Sans TC coverage that the font
provides. Box-drawing glyphs SHALL join across cells so a drawn grid shows continuous strokes. The
face's contextual programming ligatures SHALL stay enabled, and a ligature SHALL occupy exactly the
cells of the characters it replaces. The Jim Mono TC licence (SIL Open Font License 1.1), its notice,
and the upstream licence texts SHALL be shipped next to the font files.

#### Scenario: Monospace text renders the bundled Jim Mono TC face offline
- **WHEN** the application loads with remote requests blocked and the command line is opened
- **THEN** the command input's Latin characters are drawn with the Jim Mono TC web font served from the project origin, not with a machine-installed font

#### Scenario: CJK in a monospace surface is the same bundled face at two cells
- **WHEN** a monospace surface such as the command input or a box-drawing map line contains CJK characters within the shipped coverage, in the regular or the bold weight
- **THEN** those characters are drawn with the bundled Jim Mono TC face, each CJK character advances exactly two Latin characters' width, and `…` and `─` advance exactly one

#### Scenario: A box-drawing grid with CJK stays aligned and joined
- **WHEN** a message page draws a box-drawing grid whose rows hold equal cell counts and whose cells hold CJK text, such as `│北門│` between `┌────┐` and `└────┘` (each row six cells)
- **THEN** the grid's vertical strokes line up column for column across every row and its horizontal and vertical strokes meet without gaps

#### Scenario: A ligature keeps its cells
- **WHEN** monospace text contains a ligature sequence such as `->`
- **THEN** it may draw as one ligature glyph, and the run's advance equals the advance of the same number of Latin characters

#### Scenario: Only the needed slices are downloaded
- **WHEN** the populated shell renders monospace text that contains no Greek, Cyrillic, or extended-Latin characters and its fonts have finished loading
- **THEN** the Jim Mono TC regular Latin slice has been fetched and neither the Greek-Cyrillic nor the extended-Latin Jim Mono TC slice has been fetched

#### Scenario: Every Jim Mono TC slice is small and both weights cover the same CJK
- **WHEN** the committed Jim Mono TC woff2 slices and their stylesheet are inspected
- **THEN** each slice is at most 64 KB, the declared unicode ranges of one weight do not overlap, both weights declare the same CJK code points, the CJK code points equal the bundled Noto Sans TC coverage's East Asian Wide and Fullwidth code points minus the recorded ones the font lacks, and the licence files are present beside the font files

#### Scenario: Map labels keep their layout under Jim Mono TC
- **WHEN** the local-map island and the full map overlay render a dense neighbourhood with CJK labels at 1440x900 and 1280x720
- **THEN** every drawn node label and edge-marker name stays inside its reserved box, no two labels overlap, and the island keeps its anchored size
