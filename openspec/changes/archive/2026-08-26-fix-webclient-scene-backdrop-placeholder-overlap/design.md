## Context

`HudFrame.vue` reserves two stacked bands at the bottom of the stage: the action dock
(`bottom: 46px; height: var(--dock-h)`, `HudFrame.vue:173-178`) and, below it, the persistent command
line (`bottom: 0; height: 46px`, `HudFrame.vue:182-187`). So the *combined* height reserved at the
bottom of the stage — the distance from the viewport bottom up to the dock's own top edge — is
`--dock-h + 46px`, not `--dock-h` alone. `--dock-h` (defined once in `tokens.css:115` as `clamp(150px,
22vh, 184px)`) was designed to be consumed by exactly this kind of "sits above the dock" calculation
(`HudFrame.vue:167` and every rule in `SceneBackdrop.vue:335-424` already reference it), but every one
of those consuming rules only adds a small buffer (`Npx` for `N` in 12, 44, 56, 60) directly to
`--dock-h`, silently assuming the dock's top edge is `--dock-h` above the viewport bottom. It is
actually `--dock-h + 46px` above the viewport bottom. Every consumer is therefore short by the
command line's own height, and the effect is visible wherever the consumer's own buffer is small enough
not to accidentally absorb the missing 46px — which is every scene-backdrop caption (12–56px buffers)
and, with much less margin than intended, the narrative caption (60px buffer, needed ~106px).

## Goals / Non-Goals

**Goals:**
- Every surface that positions itself "above the dock" via `--dock-h` computes an offset that actually
  clears the dock's real top edge (dock height *and* the command line beneath it), at both 1440×900 and
  1280×720.
- Fix this once, at the shared-token level, so a future consumer of "the space above the dock" cannot
  reintroduce the same off-by-the-command-line-height error.

**Non-Goals:**
- Redesigning what the scene-backdrop captions say or when they appear (unchanged: same truthful-data
  branches, same testids, same text).
- Changing `--dock-h` itself, the dock's or command line's own anchor rules, or any other stage anchor's
  layout.

## Decisions

**Introduce `--stage-content-bottom` as the single source of "how far above the viewport bottom the
dock's top edge sits", rather than fixing each consumer's arithmetic independently.** Alternatives
considered:
- *Add `+ 46px` directly into each of the six affected `calc()` expressions* (five in `SceneBackdrop.vue`,
  one in `HudFrame.vue`) — fixes today's instances but repeats the same magic number six times, which is
  exactly the pattern that let the bug ship in the first place (a shared quantity re-derived by hand at
  each call site rather than named once). Rejected in favor of one named token, consistent with this
  repo's own precedent (the earlier `fix-webclient-hud-integration-gaps` change did the same thing for a
  duplicated z-index literal rather than patching each consumer's number).
- *Change the command line's height to a token and reference it from each consumer's `calc()`
  (`calc(var(--dock-h) + var(--cmdline-h) + Npx)`)* — technically equivalent, but keeps the "you must
  remember to add both tokens" burden on every future consumer. Rejected: a single pre-combined
  `--stage-content-bottom` token is one less thing to get wrong at each new call site, and the command
  line's own anchor rule (`bottom: 0; height: 46px`) does not itself need the new token — only the
  *consumers positioned above the dock* do.

**Fix the narrative-caption anchor's offset in the same change, not a follow-up.** It shares the exact
same root cause and the exact same fix; splitting it into a separate change would mean re-deriving and
re-reviewing the identical root-cause analysis twice for no isolation benefit — the caption's own
rendered content, testids, and behavior are otherwise untouched.

**Tokenize the command line's height as `--command-line-h`, consumed by the dock's `bottom` and the
command line's `height`.** Defining `--stage-content-bottom` with an inline 46px literal would leave the
magic number duplicated a third time — the same re-derivation pattern that let the original bug ship.
Following the earlier `fix-webclient-hud-integration-gaps` precedent (the change that tokenized a
duplicated z-index literal rather than patching each consumer's number), the quantity is named once; the
computed layout of the dock and command line rules is unchanged, only their source becomes the shared
token.

**Expose the SceneBackdrop handle through the `window.__elosernBridge` test hook.** The `__generating`
pending notice renders only when the scene is pending AND the client-local prior image is set, a state
the seed fixtures do not produce on their own. The hook is a plain `backdrop: null` property on the
`__elosernBridge` object; `AppClient.vue`'s `onMounted` writes its `sceneBackdropRef` template ref's value
(the SceneBackdrop instance's exposed interface) into that property at mount. The bridge object must be
created *before* `app.mount()` in `main.js`, because the registration callback fires during mount. A
plain property was chosen over a getter because `app._instance` — the natural "read the root component's
exposed ref" approach — is dev-only in Vue 3.5's production build (the `app._instance = vnode.component`
assignment sits inside the dev block of the esm-bundler dist), so a getter on it would silently return
`null` in production. This follows the repository's `__`-prefixed harness-hook convention
(cf. `main.js`'s existing `__elosernBridge` block). The managed-browser pending journey then seeds the
prior image with a data-URL built from the seed fixture's valid PNG, so no network request is involved.

## Risks / Trade-offs

- **Moving the narrative caption up by ~46px could reduce its available height budget** if the caption's
  own `max-height` is computed independently rather than from the same corrected anchor → verify
  `HudFrame.vue`'s feed anchor `max-height` (currently `calc(100% - var(--dock-h) - 110px)`,
  `HudFrame.vue:143,156`) does not need the same correction; if it also assumes the dock's top edge is
  `--dock-h` above the stage bottom rather than above the *content area* the caption occupies, it needs
  the identical fix for consistency, verified by the same non-overlap browser check.
- **Visual regression risk is low but not zero**: the affected captions are only visible when art
  generation is offline, pending, or the scene is missing/failed — not on a live, fully-generated scene.
  The existing `test_browser_art.py` coverage of these branches is the safety net; no new branch is
  introduced.
