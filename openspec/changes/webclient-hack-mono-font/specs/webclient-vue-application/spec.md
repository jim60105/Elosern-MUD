## ADDED Requirements

### Requirement: The monospace type role is a self-hosted, sliced Hack face
The Vue application SHALL render its monospace type role (the command line, keycaps, option and badge
numerals, local-map labels, and box-drawing map art) with the Hack typeface served from the project
origin, with Noto Sans TC (already self-hosted) drawing the CJK characters that Hack does not cover.
The monospace stack SHALL NOT name any machine-installed font family ahead of the bundled faces, so the
rendered monospace glyphs of the UI's own vocabulary do not depend on the player's installed fonts.
Hack SHALL be delivered as regular and bold unicode-range woff2 slices, each no larger than 40 KB, so
a page downloads only the slices whose characters it draws. The Hack license text SHALL be shipped
next to the font files. The switch SHALL NOT change the map layout contract: local-map node labels
and edge-marker names SHALL stay inside their reserved boxes and SHALL NOT overlap one another at the
supported desktop viewports.

#### Scenario: Monospace text renders the bundled Hack face offline
- **WHEN** the application loads with remote requests blocked and the command line is opened
- **THEN** the command input's Latin characters are drawn with the Hack web font served from the project origin, not with a machine-installed font

#### Scenario: CJK text in a monospace surface uses the bundled sans face
- **WHEN** a monospace surface such as a local-map node label or a box-drawing heading contains CJK characters
- **THEN** those characters are drawn with the self-hosted Noto Sans TC face and the surrounding Latin, digit, and box-drawing characters with Hack

#### Scenario: Only the needed slices are downloaded
- **WHEN** the populated shell renders monospace text that contains no Greek, Cyrillic, or extended-Latin characters and its fonts have finished loading
- **THEN** the Hack Latin slice has been fetched and neither the Greek-Cyrillic nor the extended-Latin Hack slice has been fetched

#### Scenario: Every Hack slice is small
- **WHEN** the built bundle's Hack woff2 slices are inspected
- **THEN** each slice is at most 40 KB, the declared unicode ranges of one weight do not overlap and together cover every character the Hack face provides, and the Hack license text is present beside the source font files

#### Scenario: Map labels keep their layout under Hack
- **WHEN** the local-map island and the full map overlay render a dense neighbourhood at 1440x900 and 1280x720
- **THEN** every drawn node label and edge-marker name stays inside its reserved box, no two labels overlap, and the island keeps its anchored size
