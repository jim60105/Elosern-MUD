# Tasks: webclient-gallery-actions

## 1. Adapter module

- [x] 1.0 Shared resolution helper: `resolve_gallery_subject_by_key`
  (`gallery-card-update-api` ships it; adapters call it for character-kind
  keys, typed producer for registry kinds) mapped to the stable rejection
  codes; no re-implementation inside `gallery_actions.py`.
- [x] 1.1 New `web/webclient/actions/gallery_actions.py`: shared subject-key
  payload validation (rail grammar), `image_id` uuid-form bound, and the
  typed-error → stable-code table (`unknown_field`, `prompt_too_long`,
  `binding_unsupported`, `unknown_card`, `unknown_subject`, plus the
  capability-naming refusals) with bounded zh-TW messages following the
  `character_actions` exemplar. Every completed result targets only gallery.
  Schema failures remain `malformed_payload`; D7 defines defensive domain codes.
- [x] 1.2 `gallery.subject.select`: exact `{subject_key}` validator; adapter
  writes the panel change's session selection store only;
  `affected_panels=("gallery",)`; `unknown_subject` rejection.
- [x] 1.3 `gallery.generate`: exact `{subject_key, fields, custom_prompt}`
  kind-neutral validator (distinct catalog ids; prompt ≤512 code points,
  printable with ASCII spaces only);
  adapter calls `request_gallery_image` once and returns `data:
  {"image_id": …}`; no connectivity import.
- [x] 1.4 `gallery.default.set` / `gallery.card.delete`: exact
  `{subject_key, image_id}`; call `set_default` / `remove_card`; re-resolve the
  card through `cards_for` first; `unknown_card` on a miss.
- [x] 1.5 `gallery.face_rect.update`: exact `{subject_key, image_id,
  face_rect}`; persist verbatim through
  `world/art/gallery.py::update_card_face_rect` (its validator owns the rect
  bounds; no crop, no second image, no file write).
- [x] 1.6 `gallery.binding.save`: exact `{subject_key, image_id, slots}`
  (non-empty distinct slot ids); build `{mask (backend SLOT_ORDER), snapshot =
  current normalized snapshot over the masked slots}` via the no-create
  stored-state reader; persist through
  `world/art/gallery.py::update_card_binding`; `binding_unsupported` for kinds
  declaring no binding support.

## 2. Registration and mirrors

- [x] 2.1 Register the six specs in `web/webclient/actions/registry.py`; extend
  the pinned production action-set test to the new exact set.
- [x] 2.2 `web/static/webclient/js/elosern/protocol.js`: mirrored exact
  payload validators for the six ids (bounds identical to Python).

## 3. Tests (deterministic; fake queue settles; no live SD/LLM)

- [x] 3.1 New `web/webclient/actions/tests/test_gallery_actions.py`: happy path
  per action against a real gallery record + faked queue; every stable rejection
  code; monster replace shape; binding captures what is worn now (empty slot →
  null, accessories sorted); item-key smuggling rejected pre-adapter; request
  dedupe via completed-request cache; companion-subject generate/binding
  through the public resolver; the panel delta's dispatch-a-selection scenario
  is exercised HERE (its stated executable home).
- [x] 3.2 Verify the module is owned by the existing recursive
  `web.webclient.actions` label in `.github/evennia-shards.json` (adding an
  explicit module label would duplicate ownership). Annotate substantively
  covered existing main requirements; defer new requirement IDs until archive
  sync creates them. Keep main specs unchanged during apply.

## 4. Observability

- [x] 4.1 One `gallery_action` facade event per completed mutation (info
  success / warn rejection) with `subject`, `action_id`, `image_id`, `kind` in
  context; observability lint clean; no Evennia logger imports.

## Verification evidence

The focused Evennia run passed 89 tests across the new action module (15),
dispatcher, action catalog, options, persona, existing gallery panel, and shard
ownership labels. The dependency-free Node gate passed 453 tests; focused
Vitest transport/store/command-echo coverage passed 69 tests in three files.
Observability, synthetic test-data, current-spec traceability, and strict
OpenSpec validation passed.

A removed standalone smoke script bootstrapped an isolated SQLite database,
created real puppet/companion records, and exercised all six production
dispatcher actions with an offline queue settlement. The Node reducer accepted
14 actual server envelopes: one initial snapshot, six gallery updates, and
seven results (including a duplicate generation replay with no second update).
It observed companion selection, one pending row, the verbatim rectangle,
current-equipment binding, and an empty gallery after default deletion.
Unpuppet retired the selection; no live SD/LLM service was used.

Both synchronous Rubber Duck critiques found no blocking issues. The plan
review clarified kind-neutral schemas, binding-refusal precedence, strict
rectangle/Unicode mirrors, rejection publication, and recursive shard ownership.
The final review's maintenance suggestions were adopted as an explicit monster
resolution branch and source-site documentation for typed-error translation;
the existing monster test also verifies default/delete actions. Selection keeps
the store's returned prose verbatim rather than introducing a reverse dependency
merely to align punctuation. No archive or main-spec sync was performed.
