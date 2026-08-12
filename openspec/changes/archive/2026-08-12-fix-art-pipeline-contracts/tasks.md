## 1. Shared stable-key contract

- [x] 1.1 Tighten `world/art/subjects.py::_validate_subject_key`: reject `|`, `/`, `:`, `{`, `}`, control characters, length > 64 (shared constant)
- [x] 1.2 Enforce the same rules in `world/imports/validate.py` (schema pattern/maxLength on `key`) and `world/quests/characterization.py` (mirrors the `fix-import-key-validity` change; keep the rule set identical)
- [x] 1.3 Keep the wire `MAX_SUBJECT_KEY` at 128 (full key = prefix + key); add a boundary round-trip test for every `ArtSubjectKind`
- [x] 1.4 Update any test fixtures/example imports that use slash, pipe, or over-long keys

## 2. In-flight status normalization

- [x] 2.1 In `world/art/presenter.py`, normalize `in_progress` to `pending` for wire output (persistent status untouched)
- [x] 2.2 Confirm Python and JS wire allowlists already accept the normalized output (no change needed beyond tests)

## 3. Tests and verification

- [x] 3.1 Tests: slash/over-long import keys rejected; quest characterization keys validated; wire length constants agree
- [x] 3.2 Test: snapshot taken while a record is claimed renders the panel as available with a pending placeholder
- [x] 3.3 Run art queue/presenter, imports, and webclient art panel tests
