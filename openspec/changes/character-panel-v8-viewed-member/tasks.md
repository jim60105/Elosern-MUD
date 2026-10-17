# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Viewed-member read model and conditions (2.5h)

- [ ] 1.1 Build `character` v8 for `resolve_viewed_member(context)` in both modes, add `member_id` and `conditions` with `source`, and drop `persona`/`intimate`; verify presenter tests for commander and companion, possession-identical payloads, combat availability, a buff with source and remaining seconds, an indefinite debuff, true values under disguise, and the read-only attribute snapshot.

## 2. Validator, mirror and selection wiring (2h)

- [ ] 2.1 Update the server validator, JS mirror, parity contract and fixtures to v8 (maximal conditions within the byte bound) and add `character` to the `party.view_member` affected panels; verify the Node mirror tests and the parity contract.

## 3. Transitional drawer (1.5h)

- [ ] 3.1 Rebind `CharacterStatusDrawer.vue` persona and intimate sections to `party_member` and its persona editor to the commander section; switch the transitional `SkillBook.vue` caster/booking id to `character.member_id`; verify the Vitest drawer and SkillBook payload tests, a persona edit refreshing from `party_member`, and the combat-mode drawer rendering traits.

## 4. Integration (1h)

- [ ] 4.1 Annotate canonical IDs for the renamed/modified requirements in `webclient-exploration-menu`, `webclient-contextual-hud` and `persona-editing`, update stories fixtures, run `uv run --locked python -m tools.contract_gate` and `openspec validate character-panel-v8-viewed-member --strict`.
