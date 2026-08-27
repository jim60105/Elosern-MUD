## ADDED Requirements

### Requirement: A fixed-column-count dock pane sizes its columns to content, never stretching to fill the panel

When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count
SHALL govern only which cell each row occupies, never the rendered width of a column. A column's rendered
width SHALL fit the natural size of the tile or row content placed in it; a pane whose rows are fewer or
narrower than the panel's available width SHALL leave the remaining width empty rather than stretching
every column to consume it. When the pane's available width is narrower than the combined natural content
width of the fixed columns, the columns SHALL compress (each track can shrink toward zero) rather than
overflow the pane horizontally. This SHALL hold regardless of how many columns the keyboard geometry fixes,
and changing a column's rendered width SHALL NOT change which row occupies which cell.

#### Scenario: A short exit list renders content-sized tiles with a fixed keyboard column count
- **WHEN** the move frame renders four exits under its two-column keyboard geometry
- **THEN** each tile's rendered width fits its own glyph and text content, the pane's remaining width past the two tiles is left empty, and pressing the horizontal arrow key still moves focus between exactly the same two columns as before

#### Scenario: Column-count-driven layout never invents equal-width stretching
- **WHEN** a dock pane applies a fixed column count for its keyboard geometry
- **THEN** no column in that pane stretches a narrower row's content to an equal share of the panel's width

#### Scenario: A narrow pane compresses the fixed columns instead of overflowing
- **WHEN** the pane's available width (e.g. the minimum supported 1280x720 viewport) is narrower than the combined natural width of the fixed columns
- **THEN** the columns compress to fit the pane without horizontal overflow, and each tile or row wraps long content within its width cap
