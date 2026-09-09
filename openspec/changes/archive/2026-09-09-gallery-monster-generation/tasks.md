## 1. Extend the capability declaration

- [x] 1.1 Add three fields to each record in `world/art/gallery_kinds.py`: requires-age-precondition, supports-field-selection, and supports-free-text. Keep the module import-free.
- [x] 1.2 Declare the character kind with the age precondition, field selection, free text, and binding support; declare the monster kind with none of those four. The card maximum stays as `gallery-kind-capabilities` set it — `None` for character, `1` for monster.
- [x] 1.3 Extend the exhaustiveness contract test to cover the new fields, and add the test asserting the monster kind declares strictly fewer capabilities than the character kind.

## 2. Make the request seam kind-driven

- [x] 2.1 Rename the first parameter of `world/art/service.py::request_gallery_image` to `entity_or_subject` (the signature the design declared) and accept either an entity carrying a portrait subject or an already-derived `ArtSubject`. Derive the subject through the existing typed producers — do not add a monster branch to a character-shaped function.
- [x] 2.2 Refuse a subject whose kind declares no gallery with a typed error before any other work.
- [x] 2.3 Gate each precondition on the declaration: run the canonical-age re-check only where the age precondition is declared; validate a field selection only where field selection is declared; accept free text only where free text is declared; validate a binding only where binding support is declared.
- [x] 2.4 Reject — never silently drop — a non-empty selection, non-empty free text, or non-`None` binding supplied for a kind that does not declare it, with a typed error naming the undeclared capability. Keep every rejection ahead of any render or write.
- [x] 2.5 Assemble the description through the existing `description_for`, which already returns the registry-driven monster description and ignores selection and free text for that kind — pass no selection for a kind that declares none rather than passing an empty one through the character path.

## 3. Scope the prompt catalog

- [x] 3.1 In `world/art/gallery_prompt.py`, make the catalog validation kind-aware: a kind that declares no field selection has no selectable field and any selection is a typed rejection.
- [x] 3.2 Keep `gallery_prompt.py` free of an import cycle — it may consult the import-free capability module, never `world/art/subjects.py`.

## 4. Generalize the staff seams

- [x] 4.1 Generalize `requeue_character_portrait` to the shared seam and rename it kind-neutrally; it is the force path and keeps bypassing the automatic idempotency guard.
- [x] 4.2 Generalize the retry seam's internals to accept any gallery-bearing subject. Do NOT rename it — `gallery-failure-visibility` already did, and `CmdArtRetry` calls it by that name. The command's one call site now hands the seam the erroring subject's TYPED subject instead of its key text: key-only resolution is ambiguous when a character stable key equals a monster tier key, and the gallery arm already holds the typed subject (rubber-duck finding, design: collision safety).
- [x] 4.3 In `commands/art.py::CmdArtRequeue`, route a subject whose kind declares a gallery — character and monster alike — to the gallery request seam, and keep the classic reset only for kinds declaring no gallery.
- [x] 4.4 Verify a monster requeue never resets a pre-existing classic monster record.
- [x] 4.5 Cover `@art retry` reaching an erroring monster subject through the existing gallery arm. The gallery arm iterates gallery records rather than kinds, so no branch is needed; the command's typed-subject handoff (see 4.2) is the only edit.

## 5. Tests

- [x] 5.1 Cover the seam: a monster subject queues exactly one job with no age attribute read and the registry-driven description; a scene subject is refused.
- [x] 5.2 Cover the rejections: a field selection, a custom prompt, and a binding each raise a typed error for a monster subject, with no record and no render.
- [x] 5.3 Cover the settled monster card: exactly one card, unbound, the shared default rectangle, empty `requested_fields`, and it is the default.
- [x] 5.4 Cover `@art requeue portrait:monster:<tier>`: one gallery request, the declared cap honoured on settle, and any pre-existing classic record untouched.
- [x] 5.5 Cover `@art retry` reaching an erroring monster subject through the existing gallery arm, plus the moot-error clear and the in-flight keep-error on a carded monster.
- [x] 5.6 Confirm character requests are unaffected: the existing character seam tests pass unchanged.
- [x] 5.7 Annotate every new test with `@covers_requirement`, and register any new test module in `.github/evennia-shards.json` in this change. No new test module was added — the existing `world.art`/`commands` shard prefixes already own the edited modules.

## 6. Verification

- [x] 6.1 `openspec validate gallery-monster-generation --strict` passes.
- [x] 6.2 `uv run --locked python -m tools.spec_traceability check` reports zero uncovered requirements.
- [x] 6.3 `uv run --locked python -m tools.observability_lint check` passes with no new waiver.
- [x] 6.4 The `world.art` and `commands` Evennia shards pass.
- [x] 6.5 Confirm the automatic monster paths are still on the classic pipeline — routing them is `gallery-monster-autogen`'s job, and this change must not start doing it halfway.
