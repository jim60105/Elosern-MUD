# Tasks: defeat-aftermath-digest-narrative

## 1. Rulebook digest section + buffs

- [ ] 1.1 `world/rules/rulebook/defeat_aftermath.yaml`: `digest` section — first-match rows over a closed condition vocabulary (`sensitivity_level`, `shame_level`, `arousal_ordinal`, `outcome.climax_count`, `outcome.zero_landed`); the section validator rejects any race/species/persona condition key at load (test)
- [ ] 1.2 `world/rules/rulebook/buffs.yaml`: `aftermath_residue` + `aftermath_humiliated` rows on the shipped `bounds` surface with world-second durations

## 2. Digest phase + outputs

- [ ] 2.1 `world/rules/defeat_aftermath.py`: digest phase between the recovery advance and the wake lines; one pass per selected participant reading its SexualState terminal fields + the mapped `ViolationOutcome`; `DigestOutcome` rows for selected participants only; `WakeObservation` (separate type) for conscious unselected bystanders
- [ ] 2.2 Mount digest buffs through the existing attach path; EventLog `digest_outcome` open-vocabulary kind + zh-tw wake template families per digest + bystander observation line in `player_messages.py`

## 3. Narrator overlay render contract

- [ ] 3.1 Pure `render_aftermath(entries, profile) -> prose`: one paragraph per entry in order, appended after the fixed wake lines; no rewrite/duplication paths; failure/timeout/disabled discards the overlay wholesale
- [ ] 3.2 `narrator.system` prompt-library guidance covering the aftermath kind vocabulary (core + violation + digest kinds)

## 4. Tests (new module registered in `.github/evennia-shards.json` same change)

- [ ] 4.1 `world/rules/tests/test_defeat_aftermath_digest.py`: three bands (high sens + climax ⇒ residue; low sens + high shame + zero-landed ⇒ humiliated; mid ⇒ none); Monster pinned-shame ⇒ residue/none without a species read; loader rejects a species-keyed row; bystander gets observation only (no `DigestOutcome` row, no buff); core-only defeat (switch off) ⇒ no digest rows
- [ ] 4.2 Render contract stubs: disabled profile ⇒ template-only render byte-identical to offline; failing profile ⇒ same; succeeding profile for N entries ⇒ exactly N paragraphs in order, settled state unchanged
- [ ] 4.3 `covers_requirement` annotations for every requirement; `uv run --locked python -m tools.spec_traceability check` green
- [ ] 4.4 Focused run green: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_defeat_aftermath_digest world.rules.tests.test_defeat_aftermath_violation`; `tools.observability_lint check`; `git diff --check` clean
