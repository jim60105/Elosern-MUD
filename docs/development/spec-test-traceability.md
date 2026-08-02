# OpenSpec Test Traceability

Every current OpenSpec requirement must be associated with at least one real
unit or integration test. Requirement traceability and Python code coverage are
separate quality gates: an annotation establishes which behavior a test claims
to verify, while Coverage.py measures which first-party code executed.

The current contract is read only from direct capability specs at
`openspec/specs/<capability>/spec.md`. Proposed specs under
`openspec/changes/` and historical specs under
`openspec/changes/archive/` are excluded.

## Requirement identifiers

The verifier derives identifiers in this form:

```text
<capability>::<normalized-requirement-name>
```

Normalization applies Unicode NFKC, case folding, and replaces runs of
non-alphanumeric characters with `-`. Do not construct identifiers by hand.
List the canonical identifiers and their source locations with:

```sh
uv run --locked python -m tools.spec_traceability list
```

A renamed requirement receives a new identifier. Update its test annotations
as part of reviewing the contract change. Empty identifiers and normalization
collisions are verification errors.

## Annotating a test

Import the repository helper and apply it directly to a discoverable `test_*`
function or method:

```python
from tools.spec_traceability import covers_requirement


class DamageTests(unittest.TestCase):
    @covers_requirement("combat-resolution::damage-is-defense-reduced-with-a-floor-of-one")
    def test_defense_reduces_damage_but_never_below_one(self):
        result = calculate_damage(attack=10, defense=100)
        self.assertEqual(result, 1)
```

One test may cover several requirements when its assertions substantively
verify all of them:

```python
@covers_requirement(
    "world-clock::world-clock-advances-deterministically",
    "settlement-stage-order::due-events-settle-in-a-fixed-order",
)
def test_clock_advances_and_settles_stages_in_order(self):
    ...
```

Arguments must be one or more string literals. The decorator must be imported
from `tools.spec_traceability`; aliases for that import are supported. The
verifier rejects dynamic arguments, unknown identifiers, invalid imports, and
decorators placed on non-test callables.

The annotation is a reviewable claim, not proof of assertion strength. Add it
only when the test inputs, action, and assertions establish the requirement.
Never attach an unrelated test, weaken assertions, add a placeholder test, or
use a skipped test to close a traceability gap. The verifier intentionally has
no baseline, waiver, or allowlist.

## Static verification

Run static verification while editing specs or tests:

```sh
uv run --locked python -m tools.spec_traceability check
```

This command parses specs and test source without importing game modules. It
fails for annotation errors and for every current requirement with no valid
association. Add `--json-output <path>` to write a deterministic report for
handoff or automated processing.

## Successful-execution evidence

Static presence is insufficient for the CI gate. The decorator writes a JSON
Lines record only after an annotated test returns successfully and only when
`OPENSPEC_TEST_EVIDENCE` is configured. Failing, skipped, expected-failing, and
uncollected tests therefore do not satisfy a requirement.

Collect evidence from both required test entry points and verify it with:

```sh
traceability_evidence=$(mktemp)
OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked evennia test --settings settings.py commands server typeclasses web world
OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked -m unittest discover -s tests -t .
uv run --locked python -m tools.spec_traceability verify \
  --evidence "$traceability_evidence"
```

Both test commands are mandatory. The top-level regression suite is not a
substitute for the full Evennia suite.

## Final local quality gate

Run strict OpenSpec validation, evidence-aware traceability verification, and
`git diff --check` before handoff. After the repository reaches zero genuine
requirement gaps and the coverage dependency and configuration are enabled, run
the exact aggregate coverage sequence:

```sh
COVERAGE_FILE=.coverage.evennia \
  OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
  uv run --locked coverage run -m evennia test --settings settings.py commands server typeclasses web world
COVERAGE_FILE=.coverage.top-level \
  OPENSPEC_TEST_EVIDENCE="$traceability_evidence" \
uv run --locked coverage run -m unittest discover -s tests -t .
uv run --locked coverage combine .coverage.evennia .coverage.top-level
uv run --locked coverage json --fail-under=0 -o coverage.json
uv run --locked python -m tools.verify_coverage_roots coverage.json
uv run --locked coverage report --fail-under=90
uv run --locked coverage xml -o coverage.xml
```

The Evennia runner owns package-local tests under exactly these first-party
roots: `commands`, `server`, `typeclasses`, `web`, and `world`; top-level
repository contracts remain owned by `unittest discover -s tests -t .`. Only modules
under `*/tests/*` may be omitted from those roots. Dependency code, OpenSpec
artifacts, and repository tools are outside the configured source roots. Both
coverage data files must be combined before applying the aggregate 90% gate or
generating `coverage.xml` for Codecov.

## Handling a genuine gap

If no existing test substantively verifies a requirement, leave it uncovered
and generate a deterministic JSON report. The behavior change that owns the
requirement must add the missing unit or integration test. Add the annotation
beside that test after its assertions cover the contract, then rerun both test
entry points with execution evidence.

Do not enable or weaken the required CI workflow while any genuine gap remains.
An active change requirement enters this index after its delta is synced into
the main specs; its owning change must already carry the corresponding behavior
test so the annotation can be added when the main identifier exists.
