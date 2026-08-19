## Context

Part **C3** (wiring wave; depends on C2 + B5). C3 makes the Vue app live-capable and proves it; C4 flips the
production default to Vue. Splitting them keeps a single atomic production flip (C4) and keeps C3
independently green (production behavior is unchanged until C4).

## Goals / Non-Goals

**Goals** — store bound to the OOB transport; components store-bound as live renderers; a harness slice that
mounts the Vue app and proves transport round-trip + the text fallback.
**Non-Goals** — no production `base.html` flip, no legacy load removal, no `webclient-desktop-shell`
rename, no production Playwright re-map (all C4); no invented data.

## Decisions

- **D1 — Reuse the transport; dispatch only.** The store binds `evennia.js` OOB events to the C1 store core
  and sends only allowlisted `ui_action` dispatches (one-mutation-in-flight, reconnect/epoch/lock per the
  existing contract). No local model mutation.

- **D2 — Prove in a harness, don't flip production.** The managed-browser slice turns on A2's XOR flag in
  the **test config only**, so the Vue app mounts and talks to a real Evennia server while the production
  `base.html` still defaults to legacy. The existing production behavioral suite therefore still targets the
  legacy client and stays green. A check asserts the production default is unchanged at C3's archive.

- **D3 — Components are passive, store-bound.** The B-wave components render committed store state and emit
  dispatch intents only; the keyboard router keeps focusing the preserved `#action-dock`. Store-binding here
  is what lets C4's flip be a pure "point production at the now-working Vue app."

## Risks / Trade-offs

- **Harness ≠ production serving** → the harness uses the same A2 `dist` + serving config; a check asserts
  the production default still loads legacy before C4 flips it.
- **Transport wiring bugs (epoch/revision/reconnect/lock)** → the store reuses the tested reducer (C1); the
  harness slice asserts reconnect/epoch/lock against a real server.
- **Two clients coexist (production legacy + harness Vue)** → intended and single-scoped; C4 is the only
  change that moves the production default.

## Migration Plan

No production effect (harness only). Rollback = remove the binding/harness slice. No server/protocol/Telnet
impact; `base.html` is untouched.

## Open Questions

- None; the XOR flag and `dist` are fixed by A2; the production flip is fixed as C4.
