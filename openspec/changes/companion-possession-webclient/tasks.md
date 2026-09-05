# Tasks: companion-possession-webclient

## 1. Rules-side seam

- [ ] 1.1 Ensure `world/rules/possession.py` exposes a pure gate-verdict function
  (`possession_verdict(player, npc) -> reason | None`) shared by `enter_possession` and the
  affordance builder; extract read-only if change 6 landed only the raising gate.

## 2. Action codes and vocabulary

- [ ] 2.1 `web/webclient/actions/exploration_actions.py`: validators + adapters for
  `explore.possess` (`{"npc_id"}`) and `explore.possess_release` (`{"npc_id"}`), calling the
  rules writer/release; gate rejections surface as outcome `rejected` with the gate's code/line.
- [ ] 2.2 Production registry registration (action-dispatch delta) + the updated exact-list test.
- [ ] 2.3 `web/webclient/presentation/affordances.py`: allowlist gains both codes; possess entries
  per bound companion with verdict-driven enabled/disabled; exactly-one release entry while
  possessed; possessed-actor vocabulary keeps shop/talk/engage entries visible-disabled with the
  stable refusal codes.

## 3. Possession refusals at the adapters

- [ ] 3.1 `shop.buy`/`shop.sell`, `explore.talk_scripted`/`talk_freeform`, `explore.engage`
  adapters: zero-write `possessed_shop`/`possessed_talk`/`possessed_engage` rejections before
  any state read, fixed zh-TW lines.

## 4. Banner panel

- [ ] 4.1 Server: register `possession_banner` panel (schema v1: `schema_version`, `available`,
  `host_name`, `since_tick`; unavailable form shared); presenter reads the session actor's
  possession mirror; coordinator re-pushes on the possession seams.
- [ ] 4.2 UMD protocol mirror + Vue store allowlists gain `possession_banner` in lockstep; the
  three-allowlist contract test green.
- [ ] 4.3 Vue shell: persistent banner line 「你透過{host}的雙眼行動」 beside the TopBar switcher;
  Storybook story + showcase manifest entry.

## 5. PartyDrawer

- [ ] 5.1 Companion rows render the vocabulary's possess affordance (enabled/disabled + reason
  verbatim); release control while a release entry exists; dispatch through the shared
  `ui_action` path; Vitest component tests for enabled/disabled/release rows.

## 6. Tests

- [ ] 6.1 Server vocabulary tests: gate-mirrored enabled/disabled, exactly-one release,
  possessed-actor honest-disabled refusal surface, suggestible-exclusion rows (possession codes
  never in `default_cards()`).
- [ ] 6.2 Adapter tests: possession success/failure round-trips, `possessed_shop` zero-write
  byte-identity, epoch-guard suppression of a stale refusal.
- [ ] 6.3 Banner hybrid pins: wallet payload byte-identical to A's while possessed + banner
  available; inventory rows come from B's keys; OOC switch while possessing releases via the
  change-7 hook (integration).
- [ ] 6.4 New Python test modules registered in `.github/evennia-shards.json`;
  `covers_requirement` annotations across all four delta files.

## 7. Verification

- [ ] 7.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py
  --keepdb web.webclient world` focused.
- [ ] 7.2 `pnpm test`; `pnpm run build`; `pnpm run build-storybook`;
  `pnpm run showcase-coverage`.
- [ ] 7.3 `tools.spec_traceability check`; `tools.observability_lint check`;
  `compileall -q web world`.
