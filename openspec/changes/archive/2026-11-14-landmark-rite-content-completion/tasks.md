# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
This change edits authored content only. Do not add or change any test or code.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-content` is merged: `grep -c "provisional: reassigned by landmark-rite-content-completion" world/lore/rites/content/landmark_rites.yaml` prints at least 1. If the file is missing, stop and report.

## 2. Archetypes and assignment

- [x] 2.1 Author `grave`, `mine` and `gate` per design D1 and reassign their districts per design D2. Verify: the test prefix with `world.lore.tests.test_rite_content_document` passes.
- [x] 2.2 Author `cliff` and `plaza` and reassign their districts the same way. Verify: the same test label passes, and `grep -c "provisional" world/lore/rites/content/landmark_rites.yaml` prints 0.

## 3. Review and gates

- [x] 3.1 Update `docs/lore/landmark-rites-review.md` per design D3, correcting the document where a rule fails. Verify: the document has one section per archetype of the YAML document and every option row is marked pass; the test of 2.1 still passes.
- [x] 3.2 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-content-completion` and `openspec validate landmark-rite-content-completion --strict`. Verify: all exit 0.
