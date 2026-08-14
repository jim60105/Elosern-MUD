## Context

The custom character-creation flow (Telnet `character create` in
`commands/character_creation.py` and the WebClient creation dock) currently withholds the
information the player needs to make informed choices:

- The subrace prompt never lists the available subraces by name. `world/lore/races.py` has no
  human subraces at all, so the wizard falls back to "子種族（可留空或輸入 none）" and the web form
  to a "無子種族" radio. The player's premise — every race has a subrace — is currently false for
  human, and the user wants human subraces so that "none" genuinely disappears.
- The allocation step (`world/rules/character_creation.resolve_starting_profile`) computes a total
  `budget` and per-axis spans the moment race/subrace are chosen, but the Telnet wizard shows only
  each axis's `0–span` one at a time and reveals the budget/summing rule only in the final review.
- No background/flavor-text field exists in custom creation. A concept-generated persona
  (`personality`/`life_story`/`habit`) is persisted into `entity.db.persona` at activation but is
  never rendered anywhere — not in the WebClient character panel, not on 「看 自己」.
- The WebClient custom form's action buttons (確認建立 / 清除草稿 / 返回 / 套用構想) have no mouse
  click handlers; only keyboard Enter through the capture-phase `_formKeyBound` activates a subset.
  A mouse click therefore does nothing, and keydowns that the form does not claim fall through to
  the stock plugin handler (`webclient_gui.js`), which logs
  `NO plugin handled this Keydown`.

This change is scoped to the four issues above. The project has no released users; there is no
backward-compatibility or migration requirement.

## Goals / Non-Goals

**Goals:**
- Give human a set of selectable social-class subraces so every race has subraces, and make the
  subrace choice mandatory and explained in every creation surface.
- Present the full allocation contract (budget, six axes, per-axis 0–span, sum-must-equal-budget)
  before the player enters any allocation, in both Telnet and WebClient.
- Add a player-authored background/flavor field to custom creation, persist it into the persona
  record, display it when the player inspects their own status (Web character panel + in-game
  「看」) or looks at another player character, and let the player update it freely afterwards.
- Render NPC persona flavor text (including background) on look, authored through the AI
  scene-builder seam or the administrator import path.
- Make the WebClient creation form buttons mouse-operable and stop unclaimed keydowns from
  reaching the stock plugin handler.

**Non-Goals:**
- No change to preset/custom activation semantics, the adult gate, display-name rules, the
  all-or-nothing activation transaction, or `world/rules.character_creation`'s ownership/pending
  checks.
- No change to the concept proposal's `personality`/`life_story`/`habit` fields or to how the LLM
  writes them; the new `background` is player-authored (or NPC-authored) text, not LLM output.
- No change to the import loader (`world/imports/loader.py` keeps writing the opaque persona record
  verbatim for imported characters/NPCs); the new `background` write paths are the player update
  command and the scene-builder characterization seam.
- No per-entity visibility filtering of persona text: a persona-bearing living entity's block shows
  to whoever looks at it (single-player game; other-player look is rare but handled consistently).
- No data migration and no backward-compatibility layer.

## Decisions

### D1 — Human subraces are social classes, designed from the story settings

`world/lore/races.py` `SUBRACE_REGISTRY` gains human entries modeled on the human social ladder in
`tmp/story_settings/world_info.md` (皇族與大貴族 / 中小貴族 / 富裕平民 / 普通平民 / 底層平民) and the two
human character examples in `tmp/story_settings/character/`:

| key | display_name_zh | common_name_zh | specialty |
|---|---|---|---|
| `human_royal` | 王族 | 皇族與大貴族 | Royal blood and high-noble upbringing; education over combat. |
| `human_noble` | 貴族 | 中小貴族 | Minor nobility such as 侍從貴族 (薇歐蕾特's attendant 莉茲婭). |
| `human_wealthy` | 富裕平民 | 商人與高階冒險者 | Wealthy commoners: big merchants, senior adventurers, mages. |
| `human_commoner` | 平民 | 普通平民 | Ordinary commoners: artisans, shopkeepers, adventurers. |
| `human_laborer` | 底層平民 | 農民與勞工 | The lower class: farmers and laborers. |

Each entry follows the `Subrace` dataclass contract. `static_modifiers` are small and
**zero-sum** (`atk_phys + agility + defense == 0`, matching the beastfolk discipline) so a social
class skews starting stats without shifting aggregate physical power; `vital_overrides` stay
`None` except for one flavor band where it strengthens the documented pattern (e.g.
`human_royal` may raise the `mp` band modestly, mirroring foxkin's precedent). `population` is
`None` (world_info gives no per-class count). The 艾琳 preset (`human_wanderer`) takes a fitting
commoner class. `test_races.py` and `test_player_presets.py` update to assert the new entries and
the zero-sum rule for human modifiers.

Alternatives considered: keeping human without subraces (rejected — the user explicitly wants
subraces so "none" is impossible) and biological human variants (rejected — the story settings
model human identity as social class, not subspecies).

### D2 — Subrace becomes required in every creation surface

With all three races having subraces, the "無子種族 / none" option is removed:

- Telnet wizard (`CmdCharacter.func`): the subrace prompt lists every registry subrace for the
  chosen race with `display_name_zh` (+ specialty line) and requires a selection; `none`/empty is
  no longer accepted.
- WebClient custom form (`creation_dock.js` / `creation_menu.js`): the `subrace-none` item and the
  "無子種族" radio are removed; a subrace radio is always required.
- Deterministic preflight (`world/rules/character_creation.py`): for `mode="custom"`, a missing
  `subrace` is rejected with a stable message; `resolve_starting_profile` still accepts `None` for
  internal robustness but no player-facing path can reach it.
- Concept proposal (`world/ai/character_creation.py`): `subrace_key` becomes non-nullable in the
  output schema and `_validate_subrace` requires a registered subrace belonging to the race.
- Presets (`world/lore/player_presets.py`): the three human presets are assigned subraces
  (王族 for 薇歐蕾特, 侍從貴族→`human_noble` for 莉茲婭, `human_commoner` for 艾琳), so no preset
  card carries a null subrace.
- Character import (`world/imports/schema.py` + `world/imports/validate.py`): the character
  schema now requires `subrace`, and the semantic race/subrace check rejects a missing, blank,
  unregistered, or race-incompatible subrace — an imported character without a subrace is a hard
  rejection, so no imported entity bypasses the "every race has subraces" contract.

Tests that reply `"none"`/`""` for a human subrace update to a real `human_*` key.

**Repository-wide sweep (not just Telnet tests):** every fixture that produces a `subrace=None`
through a creation-facing surface is migrated in this change — the `creation_wizard` profile
construction (`(None,) + subrace_keys`), the web action/presentation payloads and draft
normalization, the browser seed/panel fixtures, the AI proposal matrix, and `PlayerPreset.subrace`
typing/validation. A `subrace=None` value remains legal only as an internal sentinel inside
`resolve_starting_profile` and other generic trait helpers; no player-facing or creation-facing API
may emit it. A `git grep subrace=None` gate in verification confirms the sweep is complete.

### D3 — The allocation briefing is derived, single-sourced, and precedes input

The Telnet wizard resolves the profile right after the subrace choice (already true today). Before
the allocation loop it prints one briefing block built from the resolved `StartingProfile`:

```
配點說明：共 6 個項目，可用點數 {budget}。
  hp 生命值：0–{span}　mp 魔力值：0–{span}　...
六項配點總和必須恰好等於 {budget}。
```

The web form renders the same facts from the panel's existing `profiles`/`axes` data: a briefing
line above the six fields stating the budget, the axis count, each axis's 0–span, and the
sum-equals-budget rule (the `creation_menu.js` `budgetFor`/`axisFields` already carry these; only
presentation is added). The rule text is single-sourced per surface (a `creation_wizard` constant
for Telnet, the menu model for the web) and never duplicated across modules.

### D4 — The background is a player-authored persona field, written by `world/rules`

A new optional `background` prose field (≤ `MAX_PERSONA_FIELD_LENGTH`, 600 chars) joins the persona
record for player characters:

- **Creation:** the custom wizard (Telnet) and the web custom form gain an optional
  "背景設定（風味文字）" field (maxlength 600). It travels in the `creation.custom` payload, is
  validated as bounded text, is stored in the custom draft, and is persisted at activation into
  `entity.db.persona` as a `background` key alongside the six import-card keys. A blank value is
  accepted and simply absent.
- **Persona record:** the activation write keeps the six import-card keys and adds
  `background` when the draft carries one. `PersonaStore` gains `background` in its `_FIELD_LABELS`
  (背景：) and exposes it through the existing `get`/`flatten(fields=...)` API; the default dialogue
  flatten fields are unchanged so NPC dialogue injection stays byte-identical.
- **Draft/persona merge semantics (precise):** `background` is a first-class custom-draft field.
  `save_custom_draft` validates and stores it; `_normalize_draft` accepts it with its bound and
  includes it in the fingerprint; the concept-apply service does not overwrite it. On activation the
  background is merged into the persona record together with any concept persona block: the six
  import-card keys are written first, then `background` when the draft carries one, inside the same
  transaction. End-to-end guarantees asserted by tests: background alone (no concept) persists;
  background survives a later concept-apply; background survives a custom save after a concept
  apply; background survives activation in every order.
- **Single-writer boundary:** a new `world/rules` function (e.g.
  `world/rules/persona_edit.update_background(character, text)`) is the only post-activation writer
  of a player's `background`. It validates the bound, creates the import-card-shaped persona record
  when none exists, preserves every existing persona key (including unknown keys) while
  writing/clearing only `background`, and never touches traits, identity, or the world clock. NPC
  personas are written by the import loader (verbatim opaque record, unchanged) and by the
  scene-builder characterization seam (D7) — the only two NPC-persona writers. The
  `world/rules/persona.py` module docstring and the persona-store tests are updated so the documented
  contract reads "`PersonaStore` is read-only; persona records are written only by the import
  loader, the `world/rules` deterministic services, or the scene-builder characterization seam"
  instead of "the loader is the only writer".
- **Update command:** a new `設定背景 <文字>` command (alias `背景`; no-arg shows current) routes
  through the `world/rules` function. An empty argument explicitly clears the background (removes
  the key); no-argument shows the current value. It is registered in the character command set and
  documented per the command-surface contract.

### D5 — Background and persona display surfaces

- **Web character panel:** `web/webclient/presentation/character.py` bumps
  `CHARACTER_SCHEMA_VERSION` 1 → 2 and adds a bounded `persona` section (`background` nullable
  string) to the exact payload; the JS validator (`protocol.js`) and the character menu/dock render
  it. The panel is display-only and read-only; the requirement that it never substitutes disguised
  values for true traits is unchanged.
- **In-game 「看」 (look) — any living entity:** the shared look appearance path appends a living
  entity's flattened persona block (including 背景 when present) when the player looks at themself,
  at another player character, or at an NPC — the single-writer persona record is the source, so a
  player-authored background and an NPC-authored persona block are rendered by the same code path.
  The block is appended ONLY in the look text via the existing `PersonaStore.flatten` seam; it never
  affects the room look, room/object descriptions, beat detection, or onboarding guidance. A record
  without content renders nothing, so entities without a persona (e.g. monsters) are unchanged.
  Because this is a single-player game, looking at another player is rare, but the design covers it
  so the shared appearance layer behaves consistently for every living entity.

### D7 — NPC flavor text authoring seam

NPCs already carry the persona mechanism: the import loader writes `entity.db.persona` verbatim
(the import schema treats `persona` as an opaque object), and `PersonaStore` reads it. Two authoring
paths fill it, both before look renders it:

- **AI scenario director (scene builder):** the quest/scene characterization seam
  (`world/quests/characterization.py` validator + `world/quests/scene_builder.py`
  `_apply_characterization`) gains an optional bounded `background` (and, when present, the
  import-card persona block) field. The scenario-director guardrail
  (`world/ai/scenario_director.py`) validates it through the same shared `characterize_errors`
  helper, and the scene builder writes it into the spawned NPC's `entity.db.persona` alongside the
  existing identity/portrait fields. So a generated NPC can carry authored flavor text from the
  moment it spawns.
- **Administrator (import):** the existing character import payload already accepts a `persona`
  object (opaque), so an administrator-authored NPC JSON can include the persona block (including
  `background`) and it lands verbatim at `entity.db.persona` through the unchanged loader. No
  schema change is needed beyond keeping `persona` opaque; the example import JSON is extended to
  show the `background` key.

Both paths converge on the single `entity.db.persona` read model, so look rendering needs no
NPC/player distinction and no new write path for NPC personas beyond the scene-builder seam.

### D6 — Creation form buttons become pointer-operable and keydowns are claimed

The creation dock (`creation_dock.js`) binds a delegated `click` listener on the form that routes
確認建立 / 清除草稿 / 返回 / 套用構想 through the same `_submitCustom` / `_openResetConfirm` /
`_leaveCustom` / `_submitConcept` handlers, gated by the router's `isMutationInFlight` /
`isAwaitingRevision` exactly like keyboard confirmation. The capture-phase `_formKeyBound` is
generalized to mirror the exploration rest form's contract: while the custom form owns focus, every
keydown is `stopPropagation`'d (so it never reaches `$(document).keydown(plugin_handler.onKeydown)`
and `NO plugin handled this Keydown` is never logged), with `preventDefault` applied only where the
form consumes the key (Enter/Escape/navigation), never on Tab or ordinary text input. The drawer
field (`.inputfieldwrapper`) is exempted exactly as the rest form does. The claim is at the router
layer only — it never calls `preventDefault` on Tab, modifier keys, IME composition, or character
input, so native focus movement, text input, and Chinese IME continue to work. The exact-once
submission contract is unchanged: a single deliberate activation (keyboard Enter, a keyboard-
synthesized click, or a real pointer click) emits at most one mutation, and the in-flight /
awaiting-revision gate plus the pointer bridge's primary-single-activation check keep a click and a
simultaneous Enter from double-submitting. Browser coverage asserts no "NO plugin handled this
Keydown" is logged while the form is focused.

## Risks / Trade-offs

- **Requiring a subrace is a behavior change for every existing custom-flow test and for the three
  human presets.** → Presets are reassigned subraces and all wizard/rule/Node/browser tests are
  updated in the same change; the deterministic preflight rejection message is stable and asserted.
- **Character panel schema bump (1 → 2) touches the exact-shape contract and JS parity.** → Both
  the Python validator and the JS validator are updated together with a dual-direction parity test;
  the additive `persona.background` stays within the OOB envelope bound (600-char ceiling).
- **Adding a `background` key beyond the six import-card persona keys.** → `PersonaStore` already
  tolerates unknown keys (reads by name, degrades to `None`), and the creation-persona-persistence
  scenario is amended explicitly; the import loader for NPC personas is untouched.
- **The web form's Enter-to-submit interplay could double-fire with new click handlers.** → Click
  activation shares the router's submission gate and repeat-guard semantics; a synthetic
  keyboard click on a focused button is handled exactly once by the existing `_formKeyBound`, and
  the click path skips the held-Enter guard but still obeys in-flight/awaiting-revision.
- **Persona block on 「看」 could alter onboarding look-beat detection.** → The block is appended
  only in the look text for a living entity, never in beat detection or the onboarding guidance;
  `displayed-stats-view`'s beat-invariance is preserved, and a persona-less entity renders no block.
- **NPC persona text could widen look output and change existing look tests.** → The block renders
  only when `entity.db.persona` has content; existing NPCs without a persona record are unchanged,
  and the scene-builder/import seams are the only new writers (both validated through the shared
  characterization helper), with dedicated look tests for a persona-bearing NPC.
- **Dialog flatten stays persona-dialogue byte-identical.** → The new `background` is excluded from
  the default `flatten()` field set; the change is additive and the persona-dialogue-injection
  baseline tests continue to pass.
- **The persona "sole writer" documentation claim becomes stale.** → The module docstring and
  persona-store tests are updated in the same change to state that `PersonaStore` is read-only and
  that persona records are written only by the import loader, the `world/rules` deterministic
  services, or the scene-builder characterization seam, so the new background writer never
  contradicts a documented contract.
- **A wide `subrace=None` fixture surface.** → A repository-wide sweep task and a
  `git grep subrace=None` verification gate ensure every creation-facing fixture migrates; the
  generic `resolve_starting_profile` keeps accepting `None` as an internal sentinel only.

## Migration Plan

No released users and no persistent schema migration: the new `background` key is additive on the
persona record and the character panel bump is versioned. Existing pending shells behave as
before until they reach a subrace step, at which point they must pick a (now required) subrace.
Rollback is a plain revert of the change; no stored data depends on the new field.

## Open Questions

- None blocking. The exact human modifier percentages and the one `vital_overrides` flavor band
  (D1) are tuned in implementation and locked by the registry tests.
