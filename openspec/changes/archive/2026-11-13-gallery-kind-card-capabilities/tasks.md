# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb` (env file holds `MUD_TEST_SETTINGS=1`).

## 1. Declaration

- [x] 1.1 Add `supports_face_rect`, `supports_stage`, `supports_card_delete` to `GalleryKindCapabilities` (slots, constructor, freeze, `as_dict`, `__repr__`) and declare character (true, true, true), monster (true, true, false), scene (false, false, false); extend `validate_declaration_contract` per design D3. Verify the existing kind-capability contract tests (`rg -ln "validate_declaration_contract" world/art/tests`) pass under the prefix and a new test asserts a gallery-less entry declaring `supports_stage` is a violation.

## 2. Writer guards and adapter codes

- [x] 2.1 Add the four writer guards of design D4 in `world/art/gallery.py` and `world/art/service.py`. Verify new tests in `world/art/tests/test_gallery.py` (or the module that already tests `set_stage`; find with `rg -ln "def test.*stage" world/art/tests`) patch a declaration through the existing test patch seam of `_CAPABILITIES_BY_KIND_VALUE` and assert each refusal leaves the record unchanged; annotate with the two ADDED `art-gallery-kind-capabilities` IDs.
- [x] 2.2 Map the three refusals in `web/webclient/actions/gallery_actions.py::_error_code` with zh-TW messages. Verify tests in `web/webclient/actions/tests/` (find the gallery action test module with `rg -ln "gallery.card.delete" web/webclient/actions/tests`) assert `delete_unsupported` for a monster card and `stage_unsupported` under a patched declaration, each with the three-panel refresh; annotate with the ADDED management-actions ID. Update any existing test that deleted a monster card successfully to expect the refusal.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`; both pass.
- [x] 3.2 Run `openspec validate gallery-kind-card-capabilities --strict`; it passes.

## Implementation notes

- Tests for the ADDED requirements stay unannotated: the delta requirement IDs
  exist only after archive sync, which adds the annotations. This supersedes
  the "annotate with the ADDED IDs" wording in 2.1 and 2.2.
- The record has no `as_dict`; the three fields were added to `with_values`,
  the field-enumerating copy seam, instead (design D3).
- The writer guards skip a kind declared without a gallery, so the scene
  kind keeps its established no-gallery refusal text (design D4).
