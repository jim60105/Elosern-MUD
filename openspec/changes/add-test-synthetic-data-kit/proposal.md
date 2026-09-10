## Why

The gate change (`add-test-data-independence-gate`) makes shipped-content coupling in
behavior tests a CI violation, but a rule without an alternative is unimplementable:
today's tests get `healing_potion`, `fire_ball`, `capital_altoria`, `elysa_snow`, or
`治療藥水` only from the shipped registries. The 291-file debt corpus needs one shared,
synthetic stand-in world that behaves like the real catalogs (same dataclass shapes, same
lookup semantics) so a migrated test exercises mechanics against fixtures it controls.

## What Changes

- Add `world/tests/synthetic_data.py` — the synthetic test-data kit:
  - catalog dicts shaped exactly like their shipped counterparts (items, skills,
    subraces/races, player presets, npc/monster tiers, anchors, regions, city gates,
    scene archetypes, shops/economy, quests, titles, dialogue, buffs and other rulebook
    maps, sexual-act entries), keyed with a reserved `t_` prefix (e.g. `t_ember_spray`,
    `t_iron_fang`) and carrying invented Traditional-Chinese display prose, so no kit key
    or label can ever collide with a shipped token;
  - a registry-target table recording, per catalog, the owning module and its injection
    strategy (`patch.dict` on plain dicts, or the `patch.object` attribute-swap seam the
    `add-test-*-off-real-data` migrations land for frozen `MappingProxyType` catalogs);
  - scoped helpers (`synthetic_registries(...)`, a class decorator + context manager)
    that patch the targets for one test/class and restore them exactly — the same
    restore-the-previous-registry contract `evennia-test-optimization` already mandates;
  - an AST discovery pass that enumerates every consumer module binding which
    name-imported a target attribute (patched for the scope, verified by self-test —
    no hand-maintained binding list), including the `world/lore/sync.py` import-time
    capture used by DB mirroring;
  - an idempotent `install_synthetic_catalogs()` process bootstrap (kit design D2b)
    that the browser-test settings module activates under an opt-in flag, so the
    managed-browser seed and server processes — which mirror catalogs into a private
    SQLite DB at bootstrap and are unreachable by in-process patching — also run on
    synthetic data;
  - factory helpers that build synthetic definition objects (`make_item`, `make_skill`,
    `make_region`, ...) from keyword overrides, mirroring the frozen dataclasses, so a
    test needing one exotic entry can build it locally instead of widening a shared
    catalog.
- Add the JS/TS mirror for the pnpm-owned corpora: `web/webclient-app/tests/support/
  synthetic-data.mjs` and `web/static/webclient/js/tests/support/synthetic-data.js`
  (filenames deliberately outside the `*.test.js` collection glob) exporting the same
  `t_` ids and prose payloads used by presentation/action payloads.
- Add kit self-tests `world/tests/test_synthetic_data.py` proving: kit catalogs mirror
  the shipped dataclass shape; patch/restore is exact; no kit key or label is flagged by
  the test-data lint (the kit is its own first client); JS mirror loads under
  `node --test` and carries the same ids.
- Register the new Evennia test module in exactly one shard of
  `.github/evennia-shards.json` (AGENTS contract) and add the kit pointer section to
  `docs/development/evennia-testing-guide.md`.
- No changes to production code or shipped data; no existing test file is migrated here.
  (`web/tests/browser/browser_settings.py` is browser-test-only settings; the install
  flag is default-off.)

## Capabilities

### New Capabilities

(none — requirements land in the `test-data-independence` capability created by
`add-test-data-independence-gate`)

### Modified Capabilities

- `test-data-independence`: adds the synthetic-kit requirements — a shared,
  registry-compatible synthetic world with scoped patch/restore, mirrored for JS test
  corpora, self-proven gate-clean.

## Impact

- New files: `world/tests/synthetic_data.py`, `world/tests/test_synthetic_data.py`,
  `web/webclient-app/tests/support/synthetic-data.mjs`,
  `web/static/webclient/js/tests/support/synthetic-data.js`.
- Touched: `.github/evennia-shards.json` (one new label), `docs/development/
  evennia-testing-guide.md`.
- The browser wiring + end-to-end `t_`-key proof belongs to
  `migrate-browser-tests-off-real-data`, the kit's first process-scope client.
- Depends on `add-test-data-independence-gate` (the gate is the kit's independence proof).
- Unblocks all 17 `migrate-*-off-real-data` changes; none of them may invent a competing
  kit.
