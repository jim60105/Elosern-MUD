## Context

The main OpenSpec store currently contains dozens of capabilities and hundreds
of normative requirements. Tests are distributed beside their owning packages
and use both `unittest.TestCase` and Evennia's integration-test base. Nothing
currently records which requirement a test covers, so neither OpenSpec
validation nor line coverage can identify a behavioral contract with no test.

This is repository quality infrastructure. It must work offline, avoid importing
the game merely to inspect metadata, preserve the existing `uv --locked`
workflow, and treat `openspec/specs/` as the current contract. Active and
archived change specs are intentionally excluded because they are proposed or
historical rather than current requirements.

## Goals / Non-Goals

**Goals:**

- Give every current OpenSpec requirement a deterministic, human-readable ID.
- Let an existing unit or integration test declare coverage of one or more IDs
  and emit evidence only after that test executes successfully in CI.
- Fail with actionable diagnostics for uncovered requirements and stale,
  malformed, or ambiguous declarations.
- Enforce strict OpenSpec validation, full-suite success, complete requirement
  traceability, and at least 90% aggregate project-code coverage in GitHub
  Actions.
- Keep all Python commands reproducible through the locked `uv` environment.

**Non-Goals:**

- Adding, weakening, or fabricating product-behavior tests to make the gate
  green.
- Proving that a test's assertions semantically establish a requirement. The
  annotation is a reviewable traceability claim; the verifier proves identity,
  placement, and completeness.
- Requiring every test to have an annotation. Infrastructure and regression
  tests may support several contracts indirectly.
- Tracking scenarios independently. Requirement-level completeness is the
  requested gate; scenario granularity can be added by a later change.
- Measuring dependency code or treating line coverage as a substitute for
  requirement traceability.

## Decisions

### Requirement IDs are derived from the main spec

The verifier will identify a requirement as
`<capability>::<normalized-requirement-name>`. The capability is the directory
name directly under `openspec/specs/`. The normalized name uses Unicode NFKC,
case folding, and runs of non-alphanumeric characters converted to `-`.

The script will provide a listing mode so contributors copy IDs instead of
reimplementing normalization. It will reject empty slugs and collisions. A
requirement rename deliberately invalidates its old annotation, forcing the
traceability claim to be reviewed with the contract change.

Alternatives considered were ordinal IDs, hashes, and editing every spec to add
an explicit ID. Ordinals silently change when requirements are reordered;
hashes are hard to review; adding IDs to every current contract creates a large
unrelated spec rewrite. Derived IDs retain readable diffs with no main-spec
churn.

### Tests carry transparent decorator annotations with execution evidence

A small repository module will expose
`@covers_requirement("capability::requirement")`. The decorator accepts one or
more literal IDs and preserves the wrapped callable's identity and return or
exception behavior. When a CI-only evidence-file environment variable is set,
the wrapper appends a JSON record only after the test returns successfully. A
skipped, expected-failing, failing, or uncollected test therefore emits no
successful-execution evidence. The decorator performs no game-state work and
does no file I/O during ordinary local test runs.

The verifier will parse test source with Python's AST instead of importing test
modules. An annotation is valid only in a discoverable `test_*.py` module and on
a `test_*` function or method in an eligible test class, all arguments must be
string literals, and the imported decorator must resolve to the repository
helper. Multiple real tests may cover the same requirement. After CI runs, the
verifier correlates static associations with exact module and qualified-test
identities in the evidence file and counts only successful executions.

A central manifest was considered but rejected because it separates the claim
from the assertions reviewers must assess. Docstring tags avoid an import but
are easier to mistype and harder for editors to discover than a typed Python
symbol.

### Completeness and code coverage are separate gates

The traceability command will parse all main `spec.md` files, scan repository
test modules, and produce a sorted report. A static mode catches authoring errors
before test execution. Its CI mode additionally requires successful runtime
evidence for at least one associated test per requirement. It exits nonzero for
parse or evidence errors, unknown annotations, invalid annotation placement,
identity collisions, or any requirement with zero successful associations. It
does not waive missing coverage through a baseline or allowlist.

The two required commands run unconditionally under Coverage.py with branch
measurement enabled:

```sh
COVERAGE_FILE=.coverage.evennia uv run --locked coverage run -m evennia test --settings settings.py .
COVERAGE_FILE=.coverage.top-level uv run --locked coverage run -m unittest discover tests
uv run --locked coverage combine .coverage.evennia .coverage.top-level
uv run --locked coverage report --fail-under=90
```

Both test commands receive the same CI-only execution-evidence path. Coverage
source roots are exactly `commands`, `server`, `typeclasses`, `web`, and `world`.
Only `*/tests/*` is omitted from the percentage; dependencies, OpenSpec
artifacts, and repository tools are outside those source roots rather than
hidden with broad omission globs. Any future omission or source-root change is a
reviewed configuration change. Combined data is mandatory before the one
threshold report.

Combining the gates prevents a high line percentage from hiding a missing
contract and prevents annotations from hiding broadly unexecuted production
code. Mutation testing and assertion-strength analysis remain outside scope.

### CI uses one reproducible quality-gate job

GitHub Actions will check out the repository, install a pinned compatible `uv`,
sync from `uv.lock`, validate OpenSpec strictly, run the traceability verifier,
execute all project test entry points under Coverage.py, combine their data, and
enforce the configured report threshold. The job will run on pushes and pull
requests and will not contact LLM or image-generation services.

A job matrix was considered but rejected because independently generated
coverage files make aggregate threshold handling more complex and this project
has one pinned Python version. One sequential job gives a single authoritative
result.

## Risks / Trade-offs

- **A reviewer can attach an unrelated test to a requirement** → Keep the
  annotation beside the actual test and make its diff part of normal review;
  the tool validates traceability structure, not semantic truth.
- **Requirement renames create many stale IDs** → Listing and diagnostics show
  both the source requirement and invalid annotation location; intentional
  contract changes update annotations in the same change.
- **The initial audit can expose real uncovered requirements** → Treat zero gaps
  as a prerequisite for workflow enablement. Pause this change and hand the
  deterministic gap report to the owning behavior change; do not commit a known-
  failing required workflow or add placeholder tests here.
- **Coverage behavior differs between local and CI execution** → Put source,
  branch, omit, and threshold rules in `pyproject.toml`, and use the same locked
  commands in both environments.
- **A full suite may be expensive** → Correctness takes priority for this
  single-version project; optimization can split jobs later while preserving
  combined coverage semantics.

## Migration Plan

1. Add the decorator and verifier, then inventory IDs with its listing mode.
2. Annotate only existing tests whose assertions substantively cover a current
   requirement, and run both test entry points to collect execution evidence.
3. Treat a zero-gap audit as a prerequisite for continuing. If a genuine gap is
   found, emit the verifier's deterministic JSON report containing the ID, spec
   location, and association status; pause this change before adding the
   enforcing workflow, and hand the report to the behavior change that owns the
   missing test.
4. After the prerequisite passes, add Coverage.py through `uv add --dev`,
   configure the exact aggregate measurement scope, and require 90% locally.
5. Add and enable the CI workflow only after strict traceability, both test
   commands, and aggregate coverage all pass with their final configuration.

Rollback consists of reverting the workflow, tool, annotations, and development
dependency together. There is no runtime data or migration to reverse.

## Open Questions

None. Requirement-level annotations and a 90% aggregate threshold are fixed by
this change; any uncovered behavior discovered during the audit is reported and
owned by a separate product-behavior change.
