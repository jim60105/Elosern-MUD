# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
This change edits authored content only. Do not add or change any test or code.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-performer-picking` is merged and the delivery substitutes the placeholder: `grep -n "{name}" web/webclient/actions/rite_actions.py` prints at least one line. If not, stop and report.

## 2. Watch scenes

- [ ] 2.1 Author the watch scenes of `spring`, `statue`, `megalith`, `tower` and `tree` per design D1 and D2. Verify: the test prefix with `world.lore.tests.test_rite_content_document` passes.
- [ ] 2.2 Author the watch scenes of `grave`, `mine`, `gate`, `cliff` and `plaza` the same way. Verify: the same test label passes.
- [ ] 2.3 Check the watch scenes: `uv run --locked python -c "import yaml; d=yaml.safe_load(open('world/lore/rites/content/landmark_rites.yaml', encoding='utf-8')); bad=[(a,o['key'],l['text']) for a,v in d['archetypes'].items() for o in v['options'] if o['watch'] for l in o['watch']['lines'] if any(c in l['text'] for c in '她他妳')]; print(bad); assert not bad"`. Verify: it exits 0, or every reported line is a word that only contains the character without being a pronoun for the companion (for example 其他); list those lines in the hand-off. Then confirm every watch scene contains `{name}` at least once with the same kind of one-line check.

## 3. Review and gates

- [ ] 3.1 Add the "Watch perspectives" section to `docs/lore/landmark-rites-review.md` per design D3, correcting the document where a rule fails. Verify: every option has a row and every row is marked pass or listed as solo-only with a reason; the test of 2.1 still passes.
- [ ] 3.2 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-watch-perspectives` and `openspec validate landmark-rite-watch-perspectives --strict`. Verify: all exit 0.
