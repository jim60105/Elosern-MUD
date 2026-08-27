## Context

`CharacterStatusDrawer.vue` (H4, `webclient-hud-04-reference-drawers`) composes the drawer body from
two committed panels — `status` (resources + conditions) and `character` (traits + equipment +
disguise + guild + wallet + persona) — and renders them as a flat sequence of `<section>` blocks. The
設計稿's `#dr-status` (`docs/design/elosern-redesign/index.html:1062-1103`) renders a different
section sequence and a narrower `屬性` set than the shipped component, verified side by side in
Storybook (`Data/CharacterStatusDrawer` → `Full`, screenshotted against the design file during
research for this proposal).

The 設計稿's `#dr-status` markup carries exactly five main sections plus the (separately-proposed)
親密狀態 collapsible: 生命量, 屬性, 計數・公會, 條件/修正, 偽裝. It has no equipment doll, wallet line,
or persona/background section — those either live in a different drawer (`#dr-inv` owns the paper-doll
markup, per `docs/design/elosern-redesign/index.html:957-961`) or have no 設計稿 counterpart at all.
The shipped component additionally renders `裝備人偶` (EquipmentDoll), `錢包`, and `背景`, none of
which this proposal relocates — moving the equipment doll to `InventoryPanel.vue` is a materially
larger change (a new doll inside a component that currently only lists flat rows) and is not what was
reported (the report was section order and duplicate values, not equipment placement). It is called
out as a follow-up, not silently dropped.

## Goals / Non-Goals

**Goals:**
- Match the 設計稿's five-section order for the sections it defines: 生命量 → 屬性 → 計數・公會 →
  狀態(條件) → 偽裝.
- Make `屬性` show only the four true attribute keys (`atk_phys`, `agility`, `defense`,
  `magic_level`), eliminating the `hp`/`mp`/`sp`/`guild_merit` duplication against `生命量` and
  `計數・公會`.
- Make the MP/SP labels inside this component agree with `VitalsTrack.vue` and the 設計稿
  (`魔力`/`耐力`, not `氣力`/`精力`).

**Non-Goals:**
- Relocating `EquipmentDoll` out of this drawer (design.md's Context explains why; tracked as a
  follow-up, not attempted here).
- Adding 親密狀態 — separate proposal (`add-webclient-intimate-status-section`), because it requires a
  new presenter field, not a view-layer reorder.
- Any change to `status.py` / `character.py` presenters, or to any OOB payload shape.

## Decisions

**Placement of the three sections the 設計稿 doesn't define (裝備人偶, 錢包, 背景).** Each of the
three keeps the same section it immediately followed before this change — 裝備人偶 still renders
directly after 屬性 (its position today), and 錢包 then 背景 still render directly after 偽裝 (their
position today) — while the five 設計稿-defined sections around them move to the 設計稿's order.
Rationale: the 設計稿 is silent on where these three go inside this drawer (裝備人偶's canonical home
is a different drawer entirely — see below), so anchoring each to its current neighbour minimizes
template churn and avoids inventing a new default. Final template order:
生命量 → 屬性 → 裝備人偶 → 計數・公會 → 狀態(條件) → 偽裝 → 錢包 → 背景.

**Filtering `屬性` by an explicit allowlist, not by excluding the vitals/counter keys.** The component
defines `const ATTRIBUTE_KEYS = ["atk_phys", "agility", "defense", "magic_level"]` and filters
`character.traits` to rows whose `key` is in that list, rendered in that fixed order — matching the
設計稿's 攻擊→敏捷→防禦→魔階 order — rather than rendering every trait row *except* a blocklist of
`hp`/`mp`/`sp`/`guild_merit`. An allowlist fails closed: a future server-side trait key addition
renders nowhere (visible in review/showcase-coverage as a silently absent field) rather than leaking
into `屬性` unreviewed. This mirrors the existing `NAMED_SLOTS`/`OTHER_SLOTS` allowlist pattern already
used by `EquipmentDoll.vue`.

**Reusing `VitalsTrack.vue`'s label pair instead of importing it.** `CharacterStatusDrawer.vue`
already carries its own local `VITALS` constant (parallel structure to `VitalsTrack.vue`'s `GAUGES`,
not a shared import) — this proposal only corrects the two string values, not the ownership: a shared
constant would touch a file (`vitals.js`) both components import from a wave-owned area of the H2/H4
split, which is unnecessary churn for a two-string fix.

**Overriding `magic_level`'s display label client-side instead of editing the server's
`TRAIT_LABELS`.** `world/rules/status_query.py:36` labels `magic_level` as `魔法階級`; the 設計稿
abbreviates it to `魔階` only inside `#dr-status`'s `屬性` tile. `TRAIT_LABELS` is a shared server
constant — grepping its callers shows `_trait_label()` also feeds the disguise `displayed[]` rows and
any other future consumer, so shortening it there would silently reshorten every one of those, not
just this one tile. A small local override map in `CharacterStatusDrawer.vue` (keyed by `atk_phys` /
`agility` / `defense` / `magic_level`, only `magic_level` actually overridden) keeps the server label
intact for every other consumer and keeps this proposal server-change-free. The `計數・公會` rank
row's `階級` → `公會階級` fix has no server label to preserve — it is corrected in the template string
directly.

**Adding a pinned Python contract test instead of a cross-language coverage check.** The 🟡 review
finding that `showcase-coverage` (`scripts/component-coverage.mjs`) only diffs Storybook story titles
against `component-manifest.json` — it has no per-field/per-trait-key notion, so it would not notice a
new `world/rules/status_query.py` key absent from the client's `ATTRIBUTE_KEYS` — is correct; the
original design.md draft's rationale was wrong and is corrected here. A true cross-language check (the
Python test importing and diffing against the Vue source) is disproportionate for a 1-workday change.
Instead, `world/rules/tests/test_status_query.py` gains one case asserting
`_STATIC_KEYS + _COUNTER_KEYS` (minus `guild_merit`) equals the literal tuple
`("atk_phys", "agility", "defense", "magic_level")` — the same four keys `ATTRIBUTE_KEYS` hardcodes.
This is a *pin*, not a live cross-file check: it does not read the Vue file, so it cannot catch drift
introduced only on the JS side. What it does guarantee is that nobody can add a fifth key to
`_STATIC_KEYS`/`_COUNTER_KEYS` on the server without that addition being called out by name in a
failing Python test — forcing a conscious decision to also update `ATTRIBUTE_KEYS`, rather than the
new key silently never appearing in `屬性`.

## Risks / Trade-offs

- **Reordering sections changes the drawer's scroll/tab order** → this is exactly the point (matching
  the 設計稿); the drawer's existing focus-trap and Escape-close (`HudDrawer.vue`) are unaffected since
  they operate on the drawer chrome, not this component's internal section order.
- **Filtering `屬性` to a fixed allowlist could silently drop a legitimate future trait** → the four
  keys are the only members of `_STATIC_KEYS`/`_COUNTER_KEYS` minus `guild_merit`
  (`world/rules/status_query.py:40-41`) today; the new pinned Python contract test (see Decisions)
  turns a future server-side key addition into a loud, named CI failure instead of a silent gap —
  it does not auto-sync the two sides, but it guarantees the drift cannot go unnoticed.
- **Two existing Vitest assertions in `character_status_drawer.test.js` will fail once the template
  changes** → `:100-103` hardcodes the section-label order array and `:105-115` asserts the DOM trait
  node count equals `CHARACTER_PANEL_SAMPLE.traits.length` (8); both are expected failures that task
  2.1 fixes as part of this change, called out by line number in tasks.md so the implementer isn't
  surprised mid-implementation.

## Migration Plan

View-layer only, no data migration. Lands as a single PR; no flag, no phased rollout — the component
has no persisted state that depends on section order.

## Open Questions

- Should `EquipmentDoll` move to `InventoryPanel.vue`'s `#dr-inv` per the 設計稿? Deferred — flagged in
  proposal.md's Impact and here as a follow-up, not blocking this change.
