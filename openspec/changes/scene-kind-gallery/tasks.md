# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Declaration

- [ ] 1.1 Apply design D1 in `world/art/gallery_kinds.py`, `world/art/gallery.py`, `world/art/queue.py`; rewrite the kind-contract test that read the scene kind as gallery-less to use a patched synthetic declaration and add tests for the ADDED scene-declaration scenarios. Verify the kind-capability and gallery model test modules (`rg -ln "has_gallery|capabilities_for" world/art/tests`) pass under the prefix.
- [ ] 1.2 Add a seed-sync test that a seed folder `scene/<unregistered>/` is refused while `scene/<registered synthetic archetype>/` synchronizes one card. Verify the seed test module passes.

## 2. Scene chain

- [ ] 2.1 Implement design D2 in `world/art/presenter.py`. Verify new presenter tests (gallery card wins over a classic output; no card falls back to classic; pending gallery job reports pending; recorded gallery error reports failed; retention token uses the card identity) pass in the presenter scene test module (`rg -ln "describe_scene" world/art/tests web/webclient/presentation/tests`), decorated with the modified `scene-artwork-presentation` requirement ID.

## 3. Staff commands and generation seam

- [ ] 3.1 Update the staff-command tests for scene requeue/retry (design D3) and add a seam test that a scene subject request queues one gallery job. Verify `<prefix>` on the `commands` art test module and the gallery generation test module passes.

## 4. Gates

- [ ] 4.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change scene-kind-gallery`; all pass.
- [ ] 4.2 Run `openspec validate scene-kind-gallery --strict`; it passes.
