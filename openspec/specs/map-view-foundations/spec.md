# map-view-foundations Specification

## Purpose
Extract neutral frontend projection, geometry and glyph primitives and migrate existing game maps in the same cutover. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Shared map geometry is host neutral
Shared map drawing primitives SHALL preserve coordinate geometry and viewport transforms without depending on game state, editor commands or host application styles.

#### Scenario: Uniform projection
- **WHEN** a synthetic metre graph is projected, panned and pointer-zoomed
- **THEN** unequal physical gaps remain proportional, inverse projection returns the original point and the zoom anchor is preserved

#### Scenario: Two host consumers
- **WHEN** game and editor hosts supply their own selection/theme policies
- **THEN** shared shapes render through the same primitives while player knowledge/actions remain game-owned
