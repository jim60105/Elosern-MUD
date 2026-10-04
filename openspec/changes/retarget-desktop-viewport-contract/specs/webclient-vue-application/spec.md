## MODIFIED Requirements

### Requirement: Chrome type is legible and numerals are stable
Every visible text in the client — chrome text, the drawn-map text, and the message/log prose — SHALL render at the reference scale at 16 CSS pixels or more using the shared local design faces; no shared type token, and no surface, SHALL carry a reference-scale type step below 16 CSS px, including the minimap island's title, orientation marks and readout and the full-map overlay's guide, input hint, view controls, legend and remembered list. The drawn map itself — the node labels and edge-marker names inside the island's and the full map's SVG drawing — meets the same floor through the `webclient-local-map` fitted label contract (island node labels at a 16-unit step drawn at 16 × the drawing's scale at the reference scale, island marker names at the matching 16-unit marker step). Resource values, costs, counts and prices outside the drawn map SHALL use proportional sans tabular lining numerals. Monospace SHALL remain the face of command input, ASCII/box-drawing content, key names and the map's own coordinate and label type, and SHALL additionally be the face of the message window's page text and the full log's lines as `webclient-contextual-hud` and `webclient-input-narrative` define; prose SHALL retain its existing reader sizing contract, including its prose-scale preference. The floor is on every rendered size: a treatment that expresses its size relative to the surrounding prose (an `em` step such as a `sys` line's or the box-drawing art path's) SHALL be re-stepped so its computed size at the reference scale with the default prose scale is at least 16 CSS px, and no reader-selectable step may drive visible text below it; `visibility: hidden` spacing glyphs are not visible text and are exempt.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces, the minimap island and the full-map overlay render at the 1451x790 reference viewport
- **THEN** every visible text — chrome text, drawn-map node labels and edge-marker names, and message/log prose — computes to at least 16 CSS px without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace

### Requirement: The WebClient loads a self-contained offline Vue SPA
The project WebClient SHALL load a locally built, self-contained Vue 3 single-page application produced
by a Vite build and served entirely from the project origin. The page SHALL make no remote request for
a runtime UI dependency (no CDN JavaScript, CSS, or font). The application SHALL target desktop only and
SHALL NOT claim mobile acceptance; every required surface SHALL be visible and usable at the
1451x790 reference viewport. When the application mounts into its container, the stock and pre-Js text fallback it
replaces SHALL be retired so it cannot stack in document flow and push required surfaces below the
visible viewport. (The live evennia-transport mount and the always-playable text path are established by
later changes in this migration; this change establishes the offline build and render of the app.)

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the Vue application is loaded with all non-local network requests blocked
- **THEN** the Vite-built Vue bundle, its styles, and its self-hosted fonts load from the project origin without a CDN failure

#### Scenario: Desktop-only bounded render at each supported viewport
- **WHEN** the Vue application renders at the 1451x790 reference viewport
- **THEN** every required surface is visible and usable without overlapping the input path, and the application makes no mobile-behavior claim

#### Scenario: Mount retires the replaced text fallback
- **WHEN** the Vue application mounts into its container
- **THEN** the stock and pre-Js text fallback it replaces is hidden so it does not stack with the mounted application

### Requirement: Desktop chrome scales once from the reference viewport
At the 1451x790 reference viewport the client SHALL use its reference chrome dimensions. Above the reference, comparable chrome text, controls, spacing and bounded islands SHALL render at one desktop chrome factor, `S = clamp(1, min(viewportHeight / 790, viewportWidth / 1451), 1.4)`, times their reference dimensions within rounding tolerance; at 2560x1440, where both raw ratios exceed the cap, they SHALL render at 1.4 times their reference dimensions. Below the reference, or on a viewport narrower than its height would imply at the reference's own aspect ratio, chrome SHALL not shrink below its reference readability floor nor grow beyond the width's own ratio to the 1451px reference. Viewport-responsive prose, stage art and band geometry SHALL NOT be multiplied a second time.

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

### Requirement: The monospace type role is a self-hosted, sliced Jim Mono TC face
The Vue application SHALL render its monospace type role (the command line, keycaps, option and badge
numerals, local-map labels, box-drawing map art, and the message window's page text and the full
log's lines) with the Jim Mono TC typeface served from the
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
- **WHEN** the local-map island and the full map overlay render a dense neighbourhood with CJK labels at 1451x790 and 2560x1440
- **THEN** every drawn node label and edge-marker name stays inside its reserved box, no two labels overlap, and the island keeps its anchored size
