## Why

This is change **C4** (wiring wave, depends on **C3**) of the Vue SPA WebClient migration (see the
migration roadmap at `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`). C3
proved the Vue app is live-capable in a test harness while **production stayed on the legacy shell**. This
change performs the **single atomic production flip** to the Vue client: `base.html` defaults to the Vue
bundle, the legacy GoldenLayout/jQuery loads are removed, the `webclient-desktop-shell` capability is renamed
from the GoldenLayout shell to the Vue SPA shell, and the **production** Playwright behavioral suite is
re-mapped to the preserved hooks. After C4 the client is fully Vue/store-bound with no legacy view plugin in
the load path (D1 then deletes the now-dead files).

## What Changes

- **Production flip:** `base.html` defaults to the Vite bundle (the XOR flag now permanently Vue), the
  legacy GoldenLayout/jQuery/plugin `<script>` loads are removed, and the app is the live mounted client.
  The page makes no remote runtime request.
- **`webclient-desktop-shell` rename:** "… local desktop **GoldenLayout** shell" → "… local **Vue SPA**
  desktop shell", rewording the mount/fallback + tab-strip scenarios from GoldenLayout to the Vue mount.
- **Production browser re-map:** the production Playwright behavioral suite is re-mapped row-by-row per
  the Phase-0 frozen audit (`docs/development/webclient-vue-frozen-contract-audit.md` §2.3): the
  PRESERVE-SAME-HOOK hooks (`#action-dock`, `action-`/`target-` keys, `#combat-row-0`, `#inputfield`,
  `.inp` / `.narrative-divider`, `#narrative-unread`, `#elosern-action-live`, `#elosern-offline-overlay`,
  `data-node` / `data-node-id`) stay unchanged; the REMAP-TO-TESTID ids (including `combat-detail` and
  `local-map-detail`) are served as `data-testid`; every other interactive surface gets a stable
  `data-testid`.
- **Offline/behavior regression:** bundle blocked → text playable; incompatible OOB → graphical locked with
  text round-tripping; reduced-motion honored; not-color-only status; 1440×900 and 1280×720 usable.

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-desktop-shell`: renames the GoldenLayout shell requirement to the Vue SPA desktop shell and
  rewords its mount/fallback + tab-strip scenarios for the Vue mount; the fallback scenario is re-expressed
  for the Vue mount (frozen audit entry C4-02).
- `webclient-narrative-markup`: at the flip, the converted-stream requirement stops naming the stock
  plugins ("the shell or the stock plugins" → "the shell"; the notice scenario "the stock handler" → "the
  shell") — frozen audit entry C4-03, applied in the same atomic flip that removes the stock plugin loads.
- `webclient-vue-application`: adds the requirement that the view layer is fully reactive and store-bound
  with no legacy imperative view plugin remaining (dispatch-only).

## Impact

- **Modified:** `web/templates/webclient/base.html` (default → Vue; legacy loads removed),
  `web/templates/webclient/webclient.html` (the live Vue mount), `web/static/webclient/css/*` (retire
  GoldenLayout runtime css), and the production Playwright slices under `web/tests/browser/` (selector
  re-map).
- **Depends on:** C3 (store-bound views + transport, proven).
- **Preserved:** the store-bound components (C3), `evennia.js` transport, the OOB dispatch contract, the
  offline invariant, the vanilla text console.
