# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
This change edits authored content only. Do not add or change any test or code.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-watch-perspectives` is merged: `grep -c "watch:$" world/lore/rites/content/landmark_rites.yaml` prints at least 1 (at least one option has a watch scene). If not, stop and report.

## 2. Third options

- [ ] 2.1 For `spring`, `statue`, `megalith`, `tower` and `tree`, decide per design D1 and author the third option per design D2 where it qualifies. Verify: the test prefix with `world.lore.tests.test_rite_content_document` passes.
- [ ] 2.2 Do the same for `grave`, `mine`, `gate`, `cliff` and `plaza`. Verify: the same test label passes.
- [ ] 2.3 Check the watch scenes with the command of `landmark-rite-watch-perspectives` task 2.3. Verify: the same outcome as that task accepts.

## 3. Review and gates

- [ ] 3.1 Add the "Third options" section to `docs/lore/landmark-rites-review.md` per design D3. Verify: every archetype has either an option row marked pass or a stated reason; the test of 2.1 still passes.
- [ ] 3.2 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-third-option` and `openspec validate landmark-rite-third-option --strict`. Verify: all exit 0.
