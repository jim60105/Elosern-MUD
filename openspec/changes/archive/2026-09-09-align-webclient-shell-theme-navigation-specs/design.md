# Design: align-webclient-shell-theme-navigation-specs

## D1 — Spec deltas record shipped behavior; stacking order is explicit

The dock gold accent, the top navigation bar, the frameless bag, the reference-entry
filtering, and the location-line fix are already implemented and verified in this branch's
working tree. The deltas therefore describe the shipped contract, not a pending redesign.
The `webclient-exploration-menu` MODIFIED block is stacked verbatim on
`align-webclient-waiting-practice-specs`'s delta of the same requirement (which carries the
gold tab-bar wording); its tasks include the rebase step: archive + sync that change first,
then this delta applies against the synced text. If the two changes are ever reordered, this
delta's base must be re-taken from the synced spec before archive.

## D2 — `--gold-600` value: readability-bound, hue-anchored

The token was consumed by `RestForm.vue`, `CharacterSwitcher.vue`, `app-shell.css`, and
`ReferenceArtwork.vue` but never defined, so every consumer silently fell back to its
fallback value or an unset property. The definition is `#8f713c`: one perceptual step below
`--gold-500` (`#b99a60`) on the same hue, dark enough that the switcher's white label keeps
a ≥ 4.5:1 contrast ratio (the label is 14 px semibold, below WCAG's large-text threshold).
The gold ramp's block comment is updated from the stale "single seal-red accent" framing to
the two-family reality (seal-red semantic + gold emphasis).

## D3 — Showcase census stays 51; governance closes in-document

`DesktopNavigation` and `ReferenceArtwork` grew into the 51-title census without a
spec-change lockstep, which the `webclient-component-showcase` governance requirement
disallows. The honest reconciliation is documentary: this change's surfaces delta is the
change that ships the bar's contract (retroactively covering `DesktopNavigation`'s census
entry), and change 4 (`add-webclient-reference-artwork-pointer-selection`) is the change
that ships `ReferenceArtwork`'s story and manifest entry. The manifest is not edited here.

## D4 — Root projection is described observably, not by implementation seam

The shipped projection lives in the store resolver's descriptor filtering (with the
`resolveDescriptor` frozen-sentinel guard against the non-extensible prototype), but the
delta deliberately phrases the requirement as observable reachability: the tab bar and the
keyboard root carry no 角色狀態 / 任務 / 背包 entry, the remaining order is unchanged, and
the top bar is the sole stop. The requirement stays true under any future mechanism, and
the keyboard geometry (flex-wrapped tab bar, per-viewport dock height clamp) is covered by
the already-shipped dock workspace geometry tests, not re-pinned here.

## D5 — Regression test is a global token-resolution check, not a pin

The Node gate gains a check that every `var(--x)` custom property consumed by shipped
CSS/Vue style blocks resolves against the union of definitions across the same files
(`--gold-600` fails it before the token is added). Custom properties inherit globally at
runtime, so the union is the correct semantic; no allowlist is needed because no shipped
style references a runtime-only property (the JS-set `--prose-scale` keeps its `: 1`
definition in `tokens.css` and is only overridden).
