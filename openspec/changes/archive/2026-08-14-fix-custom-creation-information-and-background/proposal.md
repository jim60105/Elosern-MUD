## Why

The custom character-creation flow keeps the player guessing until the very end. The subrace
prompt never tells the player which subraces exist (and offers "none" even though human currently
has no subraces at all), the allocation step hides the total point budget and the summing rule
until the final review, there is no background/flavor-text field anywhere in the flow (and a
concept-generated persona is never shown when the player inspects their own status), and the
WebClient creation form's action buttons are not mouse-clickable and leak
"NO plugin handled this Keydown" to the console.

## What Changes

- **Human subraces.** Add a set of selectable human subraces (social classes) to
  `SUBRACE_REGISTRY`, designed from the social ladder in `tmp/story_settings/world_info.md`
  (皇族與大貴族 / 中小貴族 / 富裕平民 / 普通平民 / 底層平民) and the two human character examples in
  `tmp/story_settings/character/` (薇歐蕾特＝王族 royal, 莉茲婭＝侍從貴族 minor noble). Each entry
  follows the existing `Subrace` dataclass contract (display names, specialty, zero-sum
  `static_modifiers`, optional `vital_overrides`) and updates the shared lore consistency tests.
- **BREAKING: subrace becomes required in custom creation.** Now that every race has subraces,
  the "無子種族 / none" option is removed. The Telnet `character create` wizard and the WebClient
  custom form require a subrace selection, the deterministic custom preflight rejects a missing
  subrace, the concept proposal must always pick a registered subrace, and the three human
  presets are assigned a subrace (王族 for 薇歐蕾特, 侍從貴族 for 莉茲婭, and a fitting commoner
  class for 艾琳) so every preset card stays valid.
- **Subrace choices are explained.** The Telnet subrace prompt lists every available subrace with
  its display name (and specialty) instead of bare registry keys or a bare "none". The web form
  lists the same registry-derived names and drops the "無子種族" radio.
- **Allocation briefing before the allocation step.** Once race and subrace are chosen, both the
  Telnet wizard and the web form state the total point budget, the number of axes (six), each
  axis's 0–span range, and the rule that the allocations must sum exactly to the budget — all
  derived from `resolve_starting_profile`/the panel profiles, before the player enters a single
  value. The final review no longer reveals the rules for the first time.
- **Player-editable background (風味文字).** A new bounded background field is collected during
  custom creation (Telnet wizard and web form), persisted into the character's persona record as an
  editable `background` field, displayed in the WebClient character panel and in-game when the
  player looks at themself OR at another player character (「看」自己 / 「看 <名字>` / `look self` /
  `look <target>`), and freely updatable afterwards through a new command
  (e.g. `設定背景 <文字>` / alias `背景`). The concept-generated persona fields
  (性格/人生經歷/習慣) are unaffected.
- **NPC flavor text on look.** NPCs carry the same persona record mechanism already (the import
  loader writes `entity.db.persona`, and `PersonaStore` reads it), but the persona block is never
  rendered. This change makes the look appearance path append a living entity's persona block —
  including its `background` — so a player sees the flavor text when looking at any NPC (as well
  as at themself or another player). NPC persona text can be supplied at creation time by the AI
  scenario director (through the scene-builder characterization seam) or by an administrator
  (through the existing character import payload), so NPC flavor text is authored once and shown on
  look.
- **Creation form buttons become mouse-operable and silent.** The WebClient creation form's action
  buttons (確認建立 / 清除草稿 / 返回 / 套用構想) gain pointer activation that traverses the shared
  focus/disabled/submission gate, and the form claims the keys it handles so no keydown falls
  through to the stock plugin handler and "NO plugin handled this Keydown" is never logged while
  the form owns focus.
- **Player-facing command documentation** is updated for the new background command and the
  `character create` subrace-required behavior, keeping `docs/game/commands.md`,
  `docs/game/command-reference.md`, and `tests/test_command_docs.py` green.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `persona-store`: the read-only handler and its flatten labels cover the `background` field, and
  the look appearance path appends a living entity's persona block (including background) when the
  player looks at themself, another player character, or an NPC.
- `scene-builder`: the NPC characterization seam accepts an optional bounded `background` (and
  optional persona block) so the AI scenario director can author NPC flavor text that the look
  appearance path renders; the scenario-director guardrail validates it through the shared helper.
- `import-reference-example`: the reference character import example demonstrates the `background`
  key inside the opaque persona object, so an administrator-authoring NPCs has a documented shape to
  copy.
- `lore-registries`: the subrace-registry requirement gains human social-class subraces, replacing
  the current elf-only + beastfolk-only coverage; the registry-consistency scenarios update
  accordingly.
- `player-character-creation`: custom mode requires a compatible subrace (no "none"), the custom
  request persists an optional bounded background into the persona record, and the deterministic
  preflight/activation contract reflects both.
- `character-creation-ux`: the Telnet custom prompts list available subraces with display names,
  print an allocation briefing (budget, axis count, per-axis ranges, summing rule) before the
  allocation step, and collect the background field.
- `webclient-character-creation-ui`: the custom form drops the "無子種族" radio, shows the
  allocation briefing block, adds the background field, and makes the form action buttons
  pointer-operable with no unclaimed keydown logging.
- `creation-persona-persistence`: the persona record gains a player-editable `background` field
  written at activation alongside the import-card keys; the concept/custom draft contract is
  updated so the background survives reconnect and is cleared with the draft.
- `webclient-exploration-menu`: the character panel payload gains a bounded background/persona
  section so the player's own status shows their flavor text.
- `game-command-docs`: the new `設定背景` command and the `character create` subrace-required
  behavior are documented as canonical command surface.
- `generative-character-concept`: the concept proposal schema/validation requires a registered
  subrace for every race instead of allowing a null subrace.

## Impact

- **Lore/data:** `world/lore/races.py` `SUBRACE_REGISTRY` gains human entries; `world/lore/
  player_presets.py` human presets gain subraces; `world/lore/tests/test_races.py` and
  `test_player_presets.py` update.
- **Imports:** `world/imports/schema.py` requires `subrace` and `world/imports/validate.py`
  rejects a missing/incompatible subrace, so an imported character always carries a registered
  race-compatible subrace.
- **Rules:** `world/rules/character_creation.py` custom-mode subrace validation and the persona
  `background` write; `world/rules/creation_wizard.py` draft storage/custom-save contract;
  `world/rules/persona.py` flatten labels; a deterministic background-update path (new `world/rules`
  write function for the single-writer boundary).
- **Commands:** `commands/character_creation.py` Telnet wizard prompts/briefing/subrace-required;
  a new `設定背景` command; `commands/default_cmdsets.py` registration.
- **NPCs:** `typeclasses/entities.py`/`typeclasses/characters.py`/`typeclasses/npcs.py` look
  appearance appends the persona block; the scene-builder characterization seam
  (`world/quests/characterization.py` + `world/quests/scene_builder.py`) accepts an optional
  bounded background/persona block so the AI scenario director can author NPC flavor text; the
  import loader keeps accepting persona (including background) for administrator-created NPCs.
- **WebClient:** `web/webclient/presentation/creation.py` (background field + briefing data),
  `web/webclient/presentation/character.py` (persona/background section, schema bump), the JS
  creation menu/dock (subrace-required, briefing, background, pointer/keydown), and the
  exploration-menu JS; protocol validators and parity tests.
- **AI layer:** `world/ai/character_creation.py` proposal schema/validators require a subrace.
- **Docs:** `docs/game/commands.md`, `docs/game/command-reference.md`.
- **Tests:** command, wizard, rules, lore, Node, and managed browser suites plus the repository
  contract tests for command docs and OOB parity.
