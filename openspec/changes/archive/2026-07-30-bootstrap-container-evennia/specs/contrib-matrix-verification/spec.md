## ADDED Requirements

### Requirement: Contrib Reuse Matrix is verified against the installed Evennia version
Every module path and class/function name listed in design doc §4's Contrib Reuse Matrix SHALL
match an importable module and attribute in the Evennia version actually installed in the project
(pinned dependency), and design doc §4 SHALL be corrected in place wherever it does not.

#### Scenario: Matrix reflects the installed version
- **WHEN** design doc §4 is read after this change lands
- **THEN** every "Underlying contrib / core module" cell names a module path that exists in the
  pinned Evennia version, and every class/function named alongside it is importable from that
  module

#### Scenario: Corrections are recorded, not silently overwritten
- **WHEN** a row in the original matrix is found to be wrong
- **THEN** the correction is made in place in §4 and the nature of the correction (what was wrong,
  what is correct) is discoverable from the design doc's revision, not lost

### Requirement: Automated regression check against matrix drift
The project SHALL include an automated check that imports every module path named in the corrected
Contrib Reuse Matrix and resolves every named class or function, failing loudly if any path or
name stops resolving.

#### Scenario: Check passes against the pinned version
- **WHEN** the regression check runs against the pinned Evennia dependency
- **THEN** every import and attribute lookup listed in the matrix succeeds

#### Scenario: Check fails if a future upgrade breaks a path
- **WHEN** the pinned Evennia version is hypothetically bumped to one where a matrix-listed module
  has moved or a class has been renamed
- **THEN** the regression check fails with a message identifying which matrix row broke, rather
  than the breakage surfacing later as a confusing import error in an unrelated later change
