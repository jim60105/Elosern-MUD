# Tasks

Total estimate: **5.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Server actions and selection (2h)

- [ ] 1.1 Add required `actor_id` to `validate_skill_preview_payload` and `validate_field_cast_payload`, store the caster in the selection, and call `cast_as_member` from the cast adapter; verify the exact-schema rejections, forged caster rejection without commander substitution, and companion cast parity with the rule in the skill-use action tests.

## 2. skill_use v2 (2h)

- [ ] 2.1 Bump `skill_use` to v2 with `actor_id`, make `preview_field_skill` caster-relative (companion openings validated with the companion as initiator) and re-authorize on publication; update the JS mirror, parity contract and fixtures; verify presenter tests for commander and companion and the mirrored validator in the Node gate.

## 3. Client and integration (1.5h)

- [ ] 3.1 Send the controlled figure's `actor_id` from the skill-use store and keep the opening row's 開戰並施放 confirmation bound to the previewed caster; verify the Vitest skill-use tests, run `node --test web/static/webclient/js/tests/*.test.js` for the touched files, annotate canonical IDs for the three modified `webclient-skillbook-casting` requirements, run `uv run --locked python -m tools.contract_gate` and `openspec validate companion-field-cast-actions --strict`.
