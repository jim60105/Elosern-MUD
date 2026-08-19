## Why

This is change **C3** (wiring wave, depends on **C2** and **B5**) of the Vue SPA WebClient migration (see
the migration roadmap at `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`).
This change makes the Vue app **live-capable**: it wires the store to the `evennia.js` OOB transport and
makes the showcase components the store-bound renderers, then proves it **end-to-end in the managed-browser
test harness against a real Evennia server**. The **production `base.html` stays on the legacy shell** here,
so the existing production behavioral browser suite is untouched; the production flip to Vue is **C4**.

## What Changes

- **Transport binding:** the store subscribes to the `evennia.js` OOB events (snapshot/update/result/
  protocol-error), adopts snapshots, and dispatches only through the unchanged allowlisted action path
  (dispatch-only, one-mutation-in-flight, reconnect/epoch/lock preserved).
- **Store-bound views:** the B-wave components become the live renderers bound to the C1 store; components
  emit only user-intent dispatches.
- **Harness proof:** a managed-browser slice mounts the Vue app (via A2's XOR flag in the **test config
  only**, not the production default) against a real server and asserts: transport round-trip, store
  adoption, dispatch, and that the vanilla text console is the fallback (bundle blocked → text playable).
- **No production flip:** `base.html`'s production default is NOT changed, the legacy loads are NOT removed,
  and the `webclient-desktop-shell` requirement is NOT renamed here — all three are **C4**.

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-vue-application`: adds the requirement that ordinary text stays playable when the Vue
  graphical surfaces are unavailable (proven in this change's harness).

## Impact

- **New:** store transport binding + the store-bound component wiring + a new managed-browser harness slice
  (mount in test config) proving transport round-trip + the text fallback.
- **Depends on:** C2 (bridge/façades), B5 (all components present).
- **Preserved:** the production legacy `base.html` (unchanged), `evennia.js` transport, the OOB/action
  dispatch contract, the vanilla text console, the offline invariant, and the existing production browser
  suite.
