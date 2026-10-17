# Proposal: character panel v8 for the viewed member

## Why

Design §5 and §6.3 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: `character` is built for the viewed member; persona and intimate sections move to `party_member`; traits with breakdown layers, disguise, guild and skill groups remain; the 狀態 tab also needs the condition rows (label, remaining time, modifier summary, source) and must work in combat. Today `character` v7 is puppet-only, exploration-only, and still carries persona/intimate.

## What Changes

- **BREAKING (pre-release)** `character` v7 → v8: adds `member_id` and `conditions` (`code`, `label`, `severity`, nullable `remaining_seconds`, `modifiers`, `source`); removes `persona` and `intimate`; built for the viewed member (fallback commander) using true traits; available in exploration and combat. The design text says "v5 → v6"; the repository is at v7, so this is v8 (recorded as a planning gap).
- Python validator, JS mirror, parity contract and fixtures move together; `party.view_member` affected panels add `character`.
- Transitional consumers: `CharacterStatusDrawer.vue` reads persona and intimate from `party_member` (commander section for the persona editor); `SkillBook.vue` reads skills from the viewed member's `character` and from now on sends `character.member_id` (not the controlled figure) as the caster and booking member, so the transitional book never mixes one member's skills with another's id.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-exploration-menu`: the character panel requirement (renamed to version 8).
- `webclient-contextual-hud`: the character-status drawer reads persona and intimate from `party_member` and stays useful in combat.
- `persona-editing`: the drawer and the persona action refresh read `party_member`.

## Impact

- `web/webclient/presentation/character.py`, `world/rules/status_query/` (condition rows with source for an arbitrary member), `web/webclient/actions/party_actions.py`, JS mirror and fixtures, `web/webclient-app/components/CharacterStatusDrawer.vue`, `composables/use-status-drawer-persona.js`, `composables/use-status-drawer-character.js`, stories fixtures.
- Tests: character presenter/validator/parity tests, Vitest drawer tests.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **16 of 32**.

- depends-on: party-member-panel

### Code and spec conflicts within the new batch

- `party-member-panel`: shared helper module `persona_sections.py` and `character.py` (F; that first).
- `character-skill-growth-fields`: shared file `character.py`, shared spec requirement (re-renamed to version 9) (F/S; this first).
- `webclient-party-window-member-tab`: re-modifies `persona-editing` "The character drawer shows and edits the four persona sections" to the 成員 tab (S; ordered).
- `webclient-party-status-tab`: removes the drawer requirement modified here (S; ordered) and `CharacterStatusDrawer.vue` (F).
- Protocol fixtures/parity files shared with every protocol change (F, conditional).

### Active change coordination

No active OpenSpec change. HUD `status` v3 is unchanged and still describes the stage figure.
