## Purpose

Establishes the offline loading contract for the WebClient's Vue 3 single-page application: a locally built, self-contained Vite bundle served entirely from the project origin with no remote runtime UI dependencies, desktop-only bounded rendering at the 1451x790 reference viewport, and the retirement of the replaced stock and pre-Js text fallback on mount. It also carries the design system over from the 設計稿: the ink-night palette with a single seal-red accent, self-hosted display, serif, sans, and monospace typefaces, focus, selection, and motion tokens, status and health information never conveyed by color alone, and reduced-motion honor. It also preserves the client DOM contract hooks (action-dock target, item keys, `data-testid` hooks) and the stable public façades as browser-bridge shims. It also fixes the C4 flip contract: the view layer is fully reactive and store-bound, no legacy imperative view-plugin code remains in the load path, and every activation emits at most one request.

## Requirements

### Requirement: Chrome type is legible and numerals are stable
Every visible text in the client — chrome text, the drawn-map text, and the message/log prose — SHALL render at the reference scale at 16 CSS pixels or more using the shared local design faces; no shared type token, and no surface, SHALL carry a reference-scale type step below 16 CSS px.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces, the minimap island and the full-map overlay render at the 1451x790 reference viewport
- **THEN** every visible text — chrome text, drawn-map node labels and edge-marker names, and message/log prose — computes to at least 16 CSS px without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace

#### Scenario: Islands and overlays carry no sub-floor steps
- **WHEN** the minimap island's title, orientation marks and readout and the full-map overlay's guide, input hint, view controls, legend and remembered list render
- **THEN** each carries a reference-scale type step of at least 16 CSS px

#### Scenario: The drawn map meets the floor through the fitted label contract
- **WHEN** the node labels and edge-marker names inside the island's and the full map's SVG drawing render
- **THEN** they meet the 16 CSS px floor through the `webclient-local-map` fitted label contract (island node labels at a 16-unit step drawn at 16 × the drawing's scale at the reference scale, island marker names at the matching 16-unit marker step)

#### Scenario: Values use tabular lining numerals
- **WHEN** resource values, costs, counts and prices outside the drawn map render
- **THEN** they use proportional sans tabular lining numerals

#### Scenario: Monospace keeps its role surfaces
- **WHEN** command input, ASCII/box-drawing content, key names, the map's own coordinate and label type, the message window's page text and the full log's lines render
- **THEN** monospace remains their face, as `webclient-contextual-hud` and `webclient-input-narrative` define

#### Scenario: Prose keeps its reader sizing contract
- **WHEN** message and log prose renders
- **THEN** it retains its existing reader sizing contract, including its prose-scale preference

#### Scenario: Proportional em steps are re-stepped to the floor
- **WHEN** a treatment expresses its size relative to the surrounding prose (an `em` step such as a `sys` line's or the box-drawing art path's)
- **THEN** it is re-stepped so its computed size at the reference scale with the default prose scale is at least 16 CSS px

#### Scenario: Reader steps stay above the floor and hidden glyphs are exempt
- **WHEN** a reader-selectable size step is applied
- **THEN** no step drives visible text below the 16 CSS px floor, and `visibility: hidden` spacing glyphs are not visible text and are exempt

### Requirement: The WebClient loads a self-contained offline Vue SPA
The project WebClient SHALL load a locally built, self-contained Vue 3 single-page application produced by a Vite build and served entirely from the project origin. The page SHALL make no remote request for a runtime UI dependency (no CDN JavaScript, CSS, or font). (The live evennia-transport mount and the always-playable text path are established by later changes in this migration; this change establishes the offline build and render of the app.)

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the Vue application is loaded with all non-local network requests blocked
- **THEN** the Vite-built Vue bundle, its styles, and its self-hosted fonts load from the project origin without a CDN failure

#### Scenario: Desktop-only bounded render at each supported viewport
- **WHEN** the Vue application renders at the 1451x790 reference viewport
- **THEN** every required surface is visible and usable without overlapping the input path, and the application makes no mobile-behavior claim

#### Scenario: Mount retires the replaced text fallback
- **WHEN** the Vue application mounts into its container
- **THEN** the stock and pre-Js text fallback it replaces is hidden so it does not stack with the mounted application

#### Scenario: The application is desktop-only
- **WHEN** the application declares its supported viewports
- **THEN** it targets desktop only and claims no mobile acceptance

#### Scenario: The retired fallback cannot push surfaces offscreen
- **WHEN** the application mounts into its container and retires the stock and pre-Js text fallback
- **THEN** the fallback cannot stack in document flow and push required surfaces below the visible viewport

### Requirement: The design system carries over from the design draft and stays offline
The Vue application SHALL render with the approved design system derived from the 設計稿 (`docs/design/elosern-redesign/`), and that draft SHALL be the binding reference for **both** the visual system and the application's layout and information architecture. No design asset or font SHALL be fetched from a remote origin at render time.

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

#### Scenario: The rendered system carries the draft palette and tokens
- **WHEN** the application renders with the design system
- **THEN** it uses the ink-night palette, its seal-red accent retained for its semantic roles beside a muted-gold navigation, focus, and emphasis accent, the self-hosted display, serif, and sans typefaces, and the focus, selection, and motion tokens

#### Scenario: The draft binds layout and information architecture
- **WHEN** the draft is applied as the reference
- **THEN** it governs the palette, typefaces, and tokens, and equally the stage composition, surface anchoring, and mode-gated visibility model

#### Scenario: Color-vision legibility is preserved
- **WHEN** status and health information renders
- **THEN** it remains legible for common color-vision differences

#### Scenario: The draft governs silent details
- **WHEN** this capability and the draft are silent on a visual or navigational detail
- **THEN** the draft governs the choice

### Requirement: The Vue app binds the preserved strict DOM-independent logic to a reactive store
The Vue application SHALL use a single reactive store (Pinia) as the sole writer of client view state. The store SHALL consume the preserved DOM-independent logic through ES-module wrappers rather than reimplementing it, and SHALL publish committed state atomically so that no subscriber observes partially applied panel state. Components emit only user-intent dispatches; binding the live transport and the components to this store are established by later changes.

#### Scenario: Renderers observe only committed state
- **WHEN** a valid snapshot or update is accepted by the preserved protocol reducer through the store
- **THEN** the store publishes one commit of completely replaced panel state and no subscriber observes partially applied state

#### Scenario: Stale epochs and revisions are rejected
- **WHEN** an old-epoch snapshot or a stale active-epoch revision is presented to the store
- **THEN** the store discards it and preserves the last committed state

#### Scenario: The store holds only backed data
- **WHEN** the store receives panel data
- **THEN** it holds only data sourced from the OOB allowlist or the transport text stream and holds no invented data

#### Scenario: The consumed preserved logic is enumerated
- **WHEN** the store binds the preserved DOM-independent logic
- **THEN** it wraps the protocol reducer, the keyboard router, the narrative markup pipeline, the local-map model, and the choice-point and option-card logic

#### Scenario: The backing data allowlist is fixed
- **WHEN** the store accepts data
- **THEN** it holds only data derived from the OOB panel allowlist (art, status, context_actions, local_map, services, creation, exploration, character) and the transport text stream; it holds no invented data

#### Scenario: Tests drive the store with raw reducer inputs
- **WHEN** the store is exercised in tests
- **THEN** it is driven by raw reducer inputs

### Requirement: The app preserves the client DOM contract hooks and exposes stable test hooks
The Vue application SHALL preserve the DOM contract identifiers that the OOB and browser contract depend on: the focusable action-dock target that the keyboard router dispatches into, the `action-` and `target-` item keys selected by pointer or keyboard, and the identity of the required panel surfaces. The application SHALL expose a stable `data-testid` hook on every remaining interactive surface so behavioral browser acceptance targets deterministic hooks rather than styling selectors.

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

#### Scenario: Public façades persist as browser-bridge shims
- **WHEN** existing OOB and browser contracts reference the stable public façades — the narrative input/append path (`window.Elosern.narrativeInput`), the action submission entry point (`window.Elosern.actions.submit`), and the keyboard-router consumption contract
- **THEN** they are implemented as browser-bridge shims over the store and the imported logic

#### Scenario: Entry points stay single and non-duplicated under Vue
- **WHEN** the DOM is implemented in Vue
- **THEN** existing behavioral tests and the choice-point/narrative append path keep their single, non-duplicated entry points

### Requirement: Degraded text remains playable alongside the Vue shell
The application SHALL remain fully playable by ordinary text commands when the Vue graphical surfaces are unavailable, when the Vite bundle fails to load, or when the OOB channel is incompatible. An incompatible or failed OOB presentation SHALL lock the graphical controls while leaving the text path functional.

#### Scenario: Bundle blocked keeps text playable
- **WHEN** the Vue bundle cannot load
- **THEN** ordinary text commands can still be sent and rendered and no required input path is lost

#### Scenario: Incompatible OOB locks graphical, keeps text
- **WHEN** the application receives an unsupported protocol version
- **THEN** graphical actions are disabled and locked while a text command round-trips and renders normally

#### Scenario: Unparseable message degrades to literal text
- **WHEN** a message cannot be fully tokenized by the markup pipeline
- **THEN** the narrative shows readable literal text rather than being suppressed

#### Scenario: Text output stays the authoritative surface
- **WHEN** the Vue shell presents narrative and command output
- **THEN** narrative and command output remain the authoritative text surface, and a message that cannot be fully tokenized degrades to readable literal text rather than suppressing the log

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
breakdown elements rendered.

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

#### Scenario: Equipment adjustment strings print verbatim

- **WHEN** the doll and inventory surfaces render equipment rows
- **THEN** they print the server-generated adjustment string verbatim, the
  inventory sourcing it by joining the server's character equipment rows on
  `item_key`; a bag-only item renders none; empty renders nothing

#### Scenario: The intimate view shows the effective exposure value

- **WHEN** the intimate view renders
- **THEN** it shows the payload's effective exposure value

#### Scenario: Only schema version 5 is accepted on the wire

- **WHEN** a character payload reaches any wire validator
- **THEN** only schema version 5 is accepted, an unknown layer
  `source`/`kind` is still rejected on the wire, and neutral-chip fallback
  exists only as direct-render defense in the component

### Requirement: Desktop chrome scales once from the reference viewport
At the 1451x790 reference viewport the client SHALL use its reference chrome dimensions. Above the reference, comparable chrome text, controls, spacing and bounded islands SHALL render at one desktop chrome factor, `S = clamp(1, min(viewportHeight / 790, viewportWidth / 1451), 1.4)`, times their reference dimensions within rounding tolerance.

#### Scenario: Large desktop is proportional
- **WHEN** the same scene renders at 1451x790 and at 2560x1440 with the same reader preference
- **THEN** top navigation, control targets, map island and drawer header dimensions have the cap's 1.4 ratio within 2 CSS pixels while art and prose scale exactly once

#### Scenario: An uncapped large viewport is proportional
- **WHEN** the same scene renders at 1451x790 and at 1741x948 (a viewport whose height and width ratios are both 1.2, below the cap)
- **THEN** the same comparable dimensions have a 1.2 ratio within 2 CSS pixels

#### Scenario: Reader preference is independent
- **WHEN** the player changes only prose scale at fixed viewport size
- **THEN** message/log prose changes but chrome geometry does not

#### Scenario: Resize preserves hit testing
- **WHEN** a user resizes between acceptance dimensions and then selects a map node or command
- **THEN** the visible target receives the intended existing action and no stale geometry or duplicate dispatch occurs

#### Scenario: The capped viewport renders at 1.4 times reference
- **WHEN** the client renders at 2560x1440, where both raw ratios exceed the cap
- **THEN** comparable chrome renders at 1.4 times its reference dimensions

#### Scenario: Small or narrow viewports hold the readability floor
- **WHEN** the viewport is below the reference, or narrower than its height would imply at the reference's own aspect ratio
- **THEN** chrome does not shrink below its reference readability floor and does not grow beyond the width's own ratio to the 1451px reference

#### Scenario: Prose, art and bands scale once
- **WHEN** chrome multiplies by the desktop chrome factor
- **THEN** viewport-responsive prose, stage art and band geometry are not multiplied a second time

### Requirement: The monospace type role is a self-hosted, sliced Jim Mono TC face
The Vue application SHALL render its monospace type role with the Jim Mono TC typeface served from the
project origin, so Latin, digits, box drawing, and CJK in a monospace surface come from one bundled
family in which every East Asian Wide or Fullwidth character is exactly two Latin cells wide, in both
the regular and the bold weight. The monospace stack SHALL NOT name any machine-installed font family
ahead of the bundled faces.

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
- **WHEN** the local-map island and the full map overlay render a dense neighbourhood with CJK labels at 1451x790 and 2560x1440
- **THEN** every drawn node label and edge-marker name stays inside its reserved box, no two labels overlap, and the island keeps its anchored size

#### Scenario: The monospace role surfaces are enumerated
- **WHEN** the monospace type role renders
- **THEN** it covers the command line, keycaps, option and badge numerals, local-map labels, box-drawing map art, the message window's page text and the full log's lines

#### Scenario: Noto Sans TC may follow only as the coverage fallback
- **WHEN** the monospace font stack is declared
- **THEN** the already self-hosted Noto Sans TC MAY follow the bundled faces only as the fallback for CJK outside the shipped coverage

#### Scenario: The face ships as small unicode-range slices
- **WHEN** Jim Mono TC is delivered
- **THEN** it ships as unicode-range woff2 slices, each no larger than 64 KB, so a page downloads only the slices whose characters it draws

#### Scenario: Each weight covers the bundled Noto Sans TC CJK
- **WHEN** the shipped coverage of each weight is checked
- **THEN** it ships every East Asian Wide or Fullwidth code point of the bundled Noto Sans TC coverage that the font provides

#### Scenario: Box-drawing strokes join across cells
- **WHEN** a drawn grid renders with box-drawing glyphs
- **THEN** the glyphs join across cells so the grid shows continuous strokes

#### Scenario: Programming ligatures stay enabled and keep their cells
- **WHEN** monospace text draws a contextual programming ligature
- **THEN** ligatures stay enabled and a ligature occupies exactly the cells of the characters it replaces

#### Scenario: The licence ships beside the font files
- **WHEN** the Jim Mono TC assets are committed
- **THEN** the licence (SIL Open Font License 1.1), its notice, and the upstream licence texts are shipped next to the font files
