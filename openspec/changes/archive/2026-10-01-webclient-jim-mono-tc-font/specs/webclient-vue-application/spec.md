## ADDED Requirements

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

## REMOVED Requirements

### Requirement: The monospace type role is a self-hosted, sliced Hack face
**Reason**: Replaced by "The monospace type role is a self-hosted, sliced Jim Mono TC face". Jim Mono TC carries Hack's Latin glyphs and adds two-cell CJK in the same family.
**Migration**: None needed (no released users). The Hack slices, their generator, and their tests are removed in the same change.
