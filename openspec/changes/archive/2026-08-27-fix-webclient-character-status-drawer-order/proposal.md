## Why

The 角色狀態 (character-status) drawer's section order, and the content of its `屬性` (traits)
section, diverge from `docs/design/elosern-redesign/index.html`'s `#dr-status` markup, which
`2026-08-25-webclient-hud-redesign-roadmap-design.md` §4 makes binding wherever the roadmap and the
`webclient-contextual-hud` spec are silent on a visual detail (they are silent on section order and
on which keys populate `屬性`).

Verified live in Storybook (`Data/CharacterStatusDrawer` → `Full`) against the 設計稿's `#dr-status`
markup:

- **Section order is wrong.** Shipped: 生命量 → 狀態(conditions) → 屬性 → 裝備人偶 → 偽裝 →
  計數・公會 → 錢包 → 背景. Design: 生命量 → 屬性 → 計數・公會 → 條件/修正 → 偽裝. Conditions render
  second instead of after the guild-counter group, and the guild-counter group renders next-to-last
  instead of third.
- **`屬性` duplicates two other sections' values instead of showing only attributes.** The section
  renders `character.traits[]` unfiltered. That array's `_GAUGE_KEYS` (`world/rules/status_query.py:39`)
  and `_COUNTER_KEYS` (`:41`) members are `hp`/`mp`/`sp` and `magic_level`/`guild_merit` — the same
  quantities the `生命量` section already renders from `status.resources` and the `計數・公會` section
  already renders from `character.guild`. The screenshot shows `生命 231/405` and `功績 140` each
  rendered twice, under two different section headings, once even under a different label (`魔力` in
  `屬性` vs `氣力` in `生命量` for the same MP value — see next point). The design's `屬性` section
  shows only `攻擊`/`敏捷`/`防禦`/`魔階` — the four true attribute keys, no vitals, no counters.
- **The MP/SP labels used inside this one drawer disagree with the rest of the app.** This
  component's local `VITALS` constant (`web/webclient-app/components/CharacterStatusDrawer.vue:46-50`)
  labels `mp`/`sp` as `氣力`/`精力`. The left-HUD `VitalsTrack.vue:29-33` (H2, already shipped) and the
  設計稿 both use `魔力`/`耐力` for the same two resources. A player opening the drawer sees the same
  gauge named two different things inside the same session.
- **Two more labels in the same two sections disagree with the 設計稿, the same defect class.** The
  `屬性` row for `magic_level` shows the server's `TRAIT_LABELS["magic_level"]` value `魔法階級`
  (`world/rules/status_query.py:36`), where the 設計稿 abbreviates it to `魔階`
  (`index.html:1074`). The `計數・公會` section's rank row is hardcoded `階級`
  (`CharacterStatusDrawer.vue:272`), where the 設計稿 uses `公會階級` (`index.html:1078`).

None of this needs a server change: `status.resources`, `character.traits[]`, and `character.guild`
already carry every value involved — only which section reads which key, and in what order the
sections render, needs to change. This is scoped separately from the 親密狀態 (intimate-status)
gap, which requires a new presenter field and its own proposal.

## What Changes

- Reorder `CharacterStatusDrawer.vue`'s sections to 生命量 → 屬性 → 計數・公會 → 狀態(conditions) →
  偽裝, matching the 設計稿's `#dr-status` order. (裝備人偶, 錢包, and 背景 are not positioned by the
  設計稿's `#dr-status` markup — see design.md for their placement.)
- Filter the `屬性` section to the four true attribute keys (`atk_phys`, `agility`, `defense`,
  `magic_level`) and stop rendering `hp`/`mp`/`sp`/`guild_merit` rows there, so each quantity renders
  in exactly one section.
- Fix `CharacterStatusDrawer.vue`'s local vitals labels from `氣力`/`精力` to `魔力`/`耐力`, matching
  `VitalsTrack.vue` and the 設計稿; display the `屬性` section's `magic_level` row as `魔階` (a
  client-side display override, not a server label change) and the `計數・公會` rank row as `公會階級`.
- Add a Python contract test asserting `world/rules/status_query.py`'s `_STATIC_KEYS + _COUNTER_KEYS`
  (minus `guild_merit`) matches the client's `ATTRIBUTE_KEYS` allowlist exactly, so a future server-side
  trait addition fails CI instead of silently never appearing in `屬性`.
- Update `web/webclient-app/tests/data/character_status_drawer.test.js` and the
  `Data/CharacterStatusDrawer` Storybook stories for the new section order, the filtered `屬性` set,
  and the corrected labels.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: the character-status drawer requirement's section list ("vitals,
  traits, conditions, guild counters, disguise, persona") gains an explicit rendering-order clause and
  an explicit statement that `屬性`/traits excludes the vitals and guild-counter keys already owned by
  other sections.

## Impact

- `web/webclient-app/components/CharacterStatusDrawer.vue` — template section order, the `屬性` row
  source, and the local `VITALS` label constant.
- `web/webclient-app/tests/data/character_status_drawer.test.js` — assertions on section order and on
  which keys appear under `屬性`.
- `web/webclient-app/stories/Data/CharacterStatusDrawer.stories.js` — no prop-shape change, but the
  rendered order changes; visual review only, no story-arg edits expected.
- `world/rules/tests/test_status_query.py` — a new contract-test case pinning `_STATIC_KEYS +
  _COUNTER_KEYS` (minus `guild_merit`) against the client's attribute allowlist; no production code in
  `world/rules/status_query.py` changes.
- No change to `web/webclient/presentation/character.py`, `web/webclient/presentation/status.py`, or
  any OOB payload shape — this is a pure view-layer reorder/filter plus one Python-side test guardrail.
