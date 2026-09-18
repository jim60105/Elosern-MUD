## Context

Two repository-wide contracts constrain every extraction here:

1. **Traceability literals.** `tools.spec_traceability` requires `@covers_requirement` with
   literal ID arguments on discoverable `test_*` functions/methods. Shared *implementations*
   are fine; shared *decorated methods* are not. So the mixin holds `assert_*` bodies and the
   files keep decorated shells.
2. **Shard ownership.** `.github/evennia-shards.json` + `tests.test_evennia_test_optimization_contract`
   require every non-browser test module under the five packages to be owned by exactly one
   shard, matched by module path prefix. Non-test helper modules are NOT test modules and the
   contract tolerates them (`_showcase_build.py`, `world/lore/tests/...` helpers,
   `_dialogue_helpers.py` predate this change). New helpers therefore stay underscore-prefixed
   or plainly-named non-`test_*` modules; no `test_*.py` is renamed, so the manifest never
   changes.

## Decisions

### D1 — Data-independence base: mixin + manifest-parameterized asserts

```python
# tests/_data_independence_base.py
class DataIndependenceContractMixin:
    """unittest mixin; subclasses define MIGRATED_FILES/BEHAVIOR_FILES module constants
    and the mixin reads them via type(self)."""
    def assert_no_ledger_exemption(self): ...       # body of the ×12 copy
    def assert_zero_findings(self): ...             # body of the ×16 copy (subTest preserved)
    def assert_no_violation_naming_manifest(self): ...
    def assert_freeze_seed_untouched(self): ...
    def assert_gate_green_for_manifest(self): ...   # the ×4 copy
```

Each `tests/test_data_independence_*.py` keeps its class (base `unittest.TestCase` + mixin),
its manifest constants, its module docstring, and its decorated shells:

```python
@covers_requirement("test-data-independence::guild-shop-and-service-...")
def test_migrated_files_hold_no_ledger_exemption(self):
    self.assert_no_ledger_exemption()
```

The ×16/×17 "two hash-groups" the audit notes are only that: some files assert against the
debt-ledger group, some against the seed group — both variants get a mixin method (or a
parameter), discovered at implementation by diffing the 17 bodies (`git grep` + one read).

### D2 — Showcase evidence: `run_npm` into `_showcase_build.py`

`_showcase_build.py` already owns `showcase_build_lock`, `ensure_app_dist`,
`ensure_storybook_out`, and a private `_run_npm`; the public `run_npm(args, timeout)` moves
there verbatim (the seven copies' union), with `run_node(args, timeout)` beside it if any
file defines it separately (check at implementation). Evidence modules replace their local
def with `from ._showcase_build import run_npm`. The `setUpClass` build-lock boilerplate
collapses via a module-level helper `build_for(cls, what="dist")` or a mixin
`ShowcaseEvidenceMixin.setUpClass` — pick whichever the 6 copies fit without changing any
`@covers_requirement`-decorated method body's assertions.

### D3 — Browser harness: preserve the two tearDown orderings

Two variants exist: (a) `server = getattr(self, "server", None); super().tearDown(); if server:`
(2 files) and (b) `super().tearDown(); if getattr(self, "server", None): try: server.stop()`.
The mixin implements (b) as `ManagedServerTearDownMixin.tearDown`; files needing (a) keep a
two-line override. `_wait_command_field_released` moves to `harness.py` (or
`browser_helpers.py` — its natural home is `harness.py` per the audit) as
`wait_command_field_released`, the two copies import-delete. Browser journeys run locally only
one class at a time (AGENTS.md budget) — verification runs a chosen cheap class per file
group, not the full browser suite.

### D4 — `_raw_attribute` → `world/tests/raw_attributes.py`

The six copies differ only in docstring; the union SQL body moves to
`raw_attribute_value(obj, key)`. Each test class keeps its `_raw_attribute` method as a
one-line delegate (call sites inside those classes are dense; a rename churns dozens of
assertions for nothing). `world/tests/` is inside the `world` shard prefix — but the new
module is not named `test_*`, so the ownership contract's test-module scan (which discovers
via unittest loading of manifest labels, i.e. `world.rules.tests`-style labels) never sees it
as an owned test module; `world.tests` is not a manifest label and stays that way (verify by
running the optimization contract test).

## Risks / Trade-offs

- A mixin can hide which file checks what; the shells keep the literal IDs and the per-file
  manifests, so `git grep test_migrated_files_carry_zero_findings` still lands on the
  decorated shell, and the base carries one docstring naming all five contract checks.
- Browser `tearDown` variants: folding (a) into (b) silently changes stop-vs-teardown order;
  the plan keeps (a)'s override instead of unifying — a byte-order choice, not a cleanup.
