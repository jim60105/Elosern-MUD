## Why

P3-4: browser `trim()` and Python `strip()` disagree on boundary characters, including U+FEFF and U+0085. This can change validation, dirty-state equality, no-op versioning, and reconnection comparisons for the same card/greeting.

## What Changes

- Define one explicit finite boundary-whitespace set for NPC card leaves and editable greetings, shared by Python and JavaScript instead of host-language defaults.
- Specify exact CRLF/lone-CR conversion, preserve interior text, and retain code-point budgets, optional clears and normalized equality.
- Add meaningful shared fixtures and future save/no-op/reconnect verification without touching generic player persona normalization.
- No Unicode NFC/NFKC rewrite, transport limit relaxation, migration, companion rewrite, bundle or LLM integration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-persona-card`: normative normalization order and exact boundary character set.
- `npc-persona-editor`: card/greeting mirror agreement including normalized outputs and equality.
- `webclient-npc-persona-editor`: dirty/no-op/reconnect behavior uses that same normalized equality.

## Impact

One engineer-day: `world/lore/npc_card.py`, `web/static/webclient/js/elosern/npc_persona_card.js`, existing shared boundary fixtures, and only necessary NPC editor-model/composable equality paths. Existing 600/600/2000 card bounds and 300-code-point greeting bound remain unchanged. No generic `PersonaStore` or player editor behavior changes; development DB reset remains the adoption mechanism (§13b).

## Batch:

depends-on: npc-offline-greeting-literal-output

Code-conflict notes: ordering is for shared `npc-persona-editor` specification/test integration and greeting semantics, not a runtime dependency. Greeting escaping remains a presentation concern and must not enter normalization. Potential shared tests: persona actions/editor browser fixtures and shard registration. Python/JS normalizers and NPC editor equality paths are exclusive to this fix.
