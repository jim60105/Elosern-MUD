## 1. Direction correction

- [x] 1.1 Correct `GUIDANCE_BEAT` prose in `world/onboarding/scenes.py` to the
      unambiguous route "先向北到南大道，再向東到冒險者公會外" (never "沿著南大道
      往北").
- [x] 1.2 Correct the 公會 keyword response in
      `world/onboarding/guide_dialogue.py` to place the guild on 南大道's east
      end.
- [x] 1.3 Correct the route sentence in the 新手引導 entry in
      `world/help_entries.py`.
- [x] 1.4 Amend `docs/superpowers/specs/2026-08-02-player-onboarding-design.md`
      (Beat 5 and the §3 player journey) so the guard's guidance records the
      map-authoritative two-step route (north to 南大道, then east to
      冒險者公會外).
- [x] 1.5 Update `world/onboarding/tests/test_onboarding_data.py` so the
      guidance-beat and dialogue tests assert the two-step route, and add a
      map-path check asserting 南門 → 南大道 → 冒險者公會外 and that the guidance
      never directs through 中央廣場; update
      `world/rules/tests/test_onboarding_journey.py` guidance assertions that
      encode the old direction.

## 2. Scripted dialogue mechanism

- [x] 2.1 Add `ScriptedDialogue` component (`name="scripted_dialogue"`,
      `dialogue_key` DBField) to `typeclasses/components.py`.
- [x] 2.2 Change the dialogue registry in `world/onboarding/guide_dialogue.py`
      to a frozen `DialogueDefinition(greeting: str | None, responses: tuple[
      KeywordResponse, ...])`; update `dialogue_response`/`dialogue_has_keyword`
      in `world/onboarding/guide.py` to read the `responses` tuple, keep the
      guard's definition at `greeting=None`, and register the immutable
      `guild_staff` definition (greeting teaching the guild commands plus
      keyword responses; `guild show` listed only when the
      `guild-quest-detail-view` dependency is satisfied).
- [x] 2.3 Add read-only `world/rules/dialogue.py` as the single lookup point:
      `resolve_dialogue_component(npc)`, `is_dialogue_host(npc)`,
      `dialogue_key_for(npc)`, `dialogue_response(npc, keyword)`, and
      `greeting_for(npc)` (None → no-response fallback); no state writes.
- [x] 2.4 Generalize `commands/talk.py` so keyword answers resolve through the
      shared `dialogue.dialogue_response` lookup for guard and generic hosts; the
      onboarding service records guard seen-keywords only for known keywords;
      no-keyword `talk` shows the guide prompt (guard), `greeting_for` (generic
      host, no-response when None), or the no-response line (no component).

## 3. Guild master sync

- [x] 3.1 In `world/rules/guild_economy.py` `sync_service_content`, attach
      `ScriptedDialogue(dialogue_key="guild_staff")` to the guild master host's
      component specs (idempotent by-name attachment).

## 4. Tests and traceability

- [x] 4.1 Add/adjust tests for every delta scenario: `guild_staff` greeting and
      keyword answers, missing-greeting fallback, unknown keyword no-understanding
      with zero writes, componentless NPC no-response, guard known-keyword writes
      `guide_progress` once and unknown keyword writes nothing, the help entry's
      exact two-step route, the map-path assertion, and a test asserting every
      taught guild command resolves to a registered command (omitting `guild show`
      when the dependency is unavailable).
- [x] 4.2 Annotate tests with
      `tools.spec_traceability.covers_requirement` for every modified
      `onboarding-guide` requirement, the added `guild-registration`
      requirement, and the new `scripted-dialogue` requirements, using canonical
      IDs from `python -m tools.spec_traceability list`.
- [x] 4.3 Run `uv run --locked python -m tools.spec_traceability check`, the
      focused onboarding/guild tests, the full Evennia suite
      (`uv run --locked evennia test --settings settings.py .`), then
      `openspec validate onboarding-guild-guidance-fixes --strict`.
