# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Admission

- [x] 1.1 Thread `actor` into `_mutate` and `_mutate_official` and add the admission check and message per design. Verify `rg -n "_mutate\(\"" web/webclient/actions/gallery_actions.py` returns nothing (every call passes actor).
- [x] 1.2 Add tests for the four ADDED scenarios to the gallery action test module (`rg -ln "gallery.default.set" web/webclient/actions/tests`), decorated with the requirement ID, and fix existing tests that mutated a subject outside every category. Verify the module and `web.webclient.presentation.tests.test_art_push` pass under the prefix.

## 2. Gates

- [x] 2.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.observability_lint check` and `uv run --locked python -m tools.contract_gate --change gallery-mutation-admission`; all pass.
- [x] 2.2 Run `openspec validate gallery-mutation-admission --strict`; it passes.
