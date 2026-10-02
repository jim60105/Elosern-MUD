## Why

The project authored Chinese names and terms with two competing middle dots — U+00B7 `·` MIDDLE DOT
(the registry/content convention: NPC names like 瑪爾特·金秤, item names like 暗影鋼刀·影, webclient UI
strings) and U+30FB `・` KATAKANA MIDDLE DOT (the namegen-pipeline convention, pinned by the
`namegen-corpus-registry` and `npc-name-generation` specs) — producing visually inconsistent,
混雜 renders. The owner has decided: every authored name/term separator becomes U+2027 `‧`
HYPHENATION POINT, the MOE-standard 正體中文 間隔號 (https://zh.wikipedia.org/zh-tw/間隔號,
https://language.moe.gov.tw/001/Upload/FILES/SITE_CONTENT/M0001/HAU/h14.htm). A single canonical
separator removes the last convention drift between lore content, the namegen pipeline, the
webclient, and the prompt bank.

## What Changes

- **BREAKING** Flip the single registry-layer composition constant `world/lore/names.py::NAME_SEPARATOR`
  from `"・"` (U+30FB) to `"‧"` (U+2027); every composed display name (`compose_display_name`,
  `roll_name`, the scenario-director `name_inspiration` bank) renders with ‧ from then on.
- **BREAKING** Mechanically replace U+00B7 `·` and U+30FB `・` with U+2027 `‧` at every authored
  site: lore/dialogue/item/rulebook data and comments (py/yaml), synthetic test fixtures,
  codepoint-pinning tests, webapp components/stories/tests, Node gate tests, the vendored namegen
  corpus `label` fields and the fantasy-name-generator skill asset, and `docs/lore` prose.
- Update the naming-format prose in `docs/lore/settlement-locations.md` (姓名格式 「名·姓」) to ‧.
- Update the skill-asset constant `.agents/skills/fantasy-name-generator/scripts/namegen.py::NAME_SEPARATOR`
  and its corpus `label` fields (a standalone authoring-tool duplicate of the separator — the
  runtime `name_inspiration` bank rolls through `world.rules.namegen`, but a stale ・ in the skill
  would keep emitting mixed-dot names into authored content).
- No validator changes: ‧ is category Po, printable, non-whitespace, and outside the reserved
  separator set `|{}/:`, so `validate_npc_name` / `validate_npc_title` / `character_creation._validate_name`
  / art subject-key rules all accept it unchanged; the U+3000 full-width-space ban is unaffected.
- Out of scope (historical evidence, NOT rewritten): `openspec/changes/archive/**` and
  `docs/superpowers/specs/**`. The 2026-09-20 settlement-shops design doc's "Registry names use
  U+00B7" note becomes superseded; the supersession is recorded in this change's design.md instead
  of editing that doc.
- No command-surface changes: `docs/game/commands.md` and `docs/game/command-reference.md` contain
  zero middle dots and are untouched (verified).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

The literal separator codepoint is pinned in spec text across eight capabilities; each gets a
delta that keeps every requirement **title** byte-identical (so `covers_requirement` annotation IDs
stay stable) and changes only body/scenario codepoints and example strings:

- `namegen-corpus-registry`: separator requirement pins `NAME_SEPARATOR = "・"` (U+30FB) and the
  「加斯帕・斯諾」 scenario → U+2027.
- `npc-name-generation`: roll form `given.zh・surname.zh` with "U+30FB separator" → U+2027.
- `blueprint-portrait-policy`: npc_req example `莉絲·晨星` → ‧.
- `church-ordination`: clergy NPC literals `艾莉安娜·寒水` → ‧.
- `skill-registry`: 轉生祝福·悠花/悠奈/伊洛希雅 boon labels and the fire-family 「HP・消滅」 reference → ‧.
- `webclient-component-showcase`: frozen-manifest literal `同伴 · 隊伍` → ‧.
- `webclient-contextual-hud`: name-plate ` · 羈絆`, legend `數字鍵 1–9 · …`, drawer titles
  `背包 · 裝備` / `同伴 · 隊伍`, subtitle `主動 {n} · 被動 {m}`, tag `真值 · 偽裝不影響`, and related
  scenarios → ‧.
- `webclient-exploration-menu`: keyboard-only acceptance requirement's `背包 · 裝備` drawer wording → ‧.

## Impact

- **Code**: `world/lore/names.py` (constant + docstrings), `world/skills/registry/*` comments,
  `world/lore/{guild.py,dialogue/*,npc_profiles/*,settlements/places_*}`,
  `world/lore/items/data_named_equipment.py`, `world/rules/rulebook/status_display.yaml`,
  prompt-bank tests (`world/prompts/tests/*`, `world/ai/tests/test_scenario_director_prompts.py`),
  codepoint pin `world/lore/tests/test_names.py`, synthetic fixtures
  (`world/rules/tests/test_titles/_support.py`, `world/tests/synthetic_data/data_world.py`,
  `web/browser_support/browser_fixtures_data/grafting.py`, web tests, Node
  `web/static/webclient/js/tests/protocol_core.test.js`), webapp
  (`web/webclient-app/` components/stories/tests), legacy static client
  (`web/static/webclient/js/elosern/exploration_menu.js`), skill asset
  (`.agents/skills/fantasy-name-generator/` incl. `scripts/namegen.py`, `SKILL.md`, corpus pack
  `label` fields), vendored corpus labels (the `label` field of each
  `third_party/fantasy-namegen/data/packs/*.json`, e.g. 奇幻・矮人; the `zh` name parts, region and
  translit tables carry no dots and stay untouched).
- **Docs**: `docs/lore/**` (items.md, magic-system.md, skill-trees/*, settlement-locations.md,
  overview.md, npc-persona-roster-review.md), `docs/design/**` mock copy.
- **Specs**: the eight modified capabilities above; archived changes and `docs/superpowers/specs/**`
  remain as historical evidence.
- **No API/schema/DB-shape changes**: separator bytes flow through existing string fields. No
  migration (pre-release clean cutover): existing persisted worlds are NOT upgraded — authored
  service hosts carry a never-rename/never-retitle convergence contract
  (`docs/lore/settlement-locations.md:76`) and quest occupants persist `display_name` into
  `npc.db`, so any stale DB keeps old-dot names until reset/reseed; the pre-release assumption is
  a clean database.
- **Traceability**: `covers_requirement` IDs anchor on requirement titles, which are unchanged;
  `tools.spec_traceability` check and `tools.contract_gate` run green at the end.
