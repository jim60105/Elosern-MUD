## Context

The deterministic creation milestone is complete and the WebClient foundation (23a), `login-creation-ux`, and `onboarding-guide` are all live. A new account's auto-created shell carries `creation_pending=True`; the coordinator already derives `mode="creation"` for it (`webclient-status-presentation`), and the `character` command offers preset and custom activation through `world/rules/character_creation.py`. But the browser has no creation surface: in creation mode every existing dock is absent, the `services` panel returns its unavailable form, and the player is left typing `character preset <key>` or answering a long prompt sequence. Roadmap item 23g (`webclient-character-creation-ui`) delivers the graphical equivalent.

This design implements the approved `webclient-character-creation-ui` delivery unit from
`docs/superpowers/specs/2026-08-02-webclient-ui-design.md` (§7.7) and
`docs/superpowers/specs/2026-08-02-webclient-service-creation-ui-design.md` (§7, §8, §9, §10).
That focused design covers two delivery units; **this change owns the character-creation UI only** —
service menus (23e), exploration menus (23d), and art remain out of scope. The browser stays a
read-only renderer, Telnet play is unchanged, and the single-writer rule is preserved: this change
adds a new deterministic draft service in `world/rules/` and calls only public APIs owned by
`world/rules/` (`preflight_character_creation`, `activate_player_character`) and
`world/rules/onboarding.py` (`relocate_to_starting_location`, `maybe_play_arrival`).

The existing deterministic entry points this unit consumes are all public:
`PLAYER_PRESET_REGISTRY`, `RACE_REGISTRY`, `SUBRACE_REGISTRY`, `resolve_starting_profile`,
`preflight_character_creation`, `activate_player_character`, and the onboarding relocation/arrival
functions. The adapter dispatcher contract in `webclient-action-dispatch` currently fixes the
production registry at exactly the three combat and seven service actions; this change amends that
contract to add four creation actions.

## Goals / Non-Goals

**Goals:**

- Present preset cards and a custom creation form as a bounded, keyboard-first dock in `creation`
  mode, with preset/race/subrace/allocation choices as finite controls and name plus adult ages as
  fields.
- Persist the server-accepted creation draft through a deterministic `world/rules` service so the
  browser reconnects at any saved wizard stage and no client can hide a field, skip a step, or
  activate an incomplete character.
- Register exactly four allowlisted creation adapters that re-validate through the existing
  deterministic creation service and never accept an actor/account/calculated-stat field.
- Keep the adult invariant server-authoritative: `age < 18` and `apparent_age < 18` are rejected by
  the deterministic service even when client-side validation is disabled or bypassed.
- Preserve all-or-nothing activation and the unchanged South Gate relocation plus onboarding arrival,
  publishing a full `exploration` snapshot so the creation dock hands off atomically.
- Extend the Node, Evennia, and managed Playwright gates with independent preset/custom/activation/
  reset/underage/reconnect journeys.

**Non-Goals:**

- No service-menu (23e), exploration-menu (23d), combat-menu, map, or art changes; `creation` is the
  only new panel, and it does not re-home existing dock surfaces.
- No new creation mechanics: the change does not alter `character_creation.py`'s validation, adult
  gate, subrace checks, allocation rules, sampling, or the atomic activation transaction.
- No client-side stat calculation, trait derivation, budget arithmetic as authority, or age
  validation as authority.
- No persona/import-only fields, no multi-character accounts, no alternate starting characters, and
  no change to the `character` command's own behavior or to Telnet.
- No generic `creation.command`; no action routed through the text command parser.
- No mobile acceptance, no new runtime dependency, no database migration, no backward-compatibility
  layer, no localStorage storage of canonical or draft creation state.

## Decisions

### D1. One read-only `creation` panel available only in creation mode

The production presentation registry registers a single `creation` panel (schema version 1),
available only while the puppet is `creation_pending`. Its available payload carries exactly
`schema_version`, `available`, `kind`, `draft`, `presets`, and `custom`. Outside creation mode it
uses the registered common unavailable form, exactly as `services` does. The presenter
(`web/webclient/presentation/creation.py`) validates its own output against the exact bounded schema
before returning it, following the `services.py` / `combat_panel.py` precedent.

**Why one panel instead of per-step payloads:** the focused design's "Shared Service Panel
Contract" idiom (§3) and the existing panel registry both describe whole-panel replacement; a single
`creation` panel keeps the `webclient-action-dispatch` and panel-allowlist deltas small and lets the
form descriptor and the saved draft travel in one snapshot so reconnect is one atomic adoption.

### D2. A frozen no-mutation creation view derives every control from immutable registries

`world/rules/creation_wizard.py` exposes a read-only view builder (alongside its state-writer API,
see D3) that composes preset cards from `PLAYER_PRESET_REGISTRY` and the race registry, and the
custom-form descriptor (name bounds, adult bounds, race options with descriptions and subraces,
per-race/subrace allocation axes and budget from `resolve_starting_profile`) from the immutable
lore registries. It performs no writes, never constructs a lazy handler, and never reads
`disguised_stats` or persona. The presenter serializes only that view. This keeps presenters thin
and deterministic builders in `world/rules/`, matching `service_view.py` / `combat_view.py`.

**Why not read registries directly in the presenter:** the project's established pattern (service
and combat read models) keeps every JSON-safe interpretation in one frozen rules module that pure
tests can exercise without an Evennia session, and keeps the presenter a thin serializer.

### D3. A server-owned creation wizard draft is the sole staging state

A new persistent attribute `creation_draft` on `PlayerCharacter` is written only by
`world/rules/creation_wizard.py`. Its storage is a small versioned dict that records the accepted
mode and values: for preset mode, `stage="preset_selected"` plus the validated `preset_key`; for
custom mode, `stage="custom_filled"` plus `display_name`, `age`, `apparent_age`, `race`, `subrace`,
and the six `allocations`. Writing a draft validates every value through the existing public
`preflight_character_creation` before persisting, so the server owns step order and accepted values.
`creation.reset` clears the draft idempotently.

**Activation and draft clear share one deterministic outer transaction.** `creation.activate` does
not call `activate_player_character` and then clear the draft in a second write — that would leave a
window where a completed character still holds a draft and a second activation could pass an early
pending check. Instead `world/rules/creation_wizard.py` exposes `activate_draft(account, character)`,
which runs a `transaction.atomic()` block that: (1) re-reads and re-validates the stored draft and
re-runs `preflight_character_creation` against the committed row; (2) re-checks that the actor is
still `creation_pending` and owned by the account immediately before the activation write (the
existing preflight enforces both, and the re-check runs inside the same transaction as the write);
(3) calls the public `activate_player_character(account, character, request)` to write identity,
traits, and initial mechanical state; and (4) clears the `creation_draft` attribute in the same
transaction, so the draft and activation commit or roll back together. Because the draft clear and
the activation writes share one atomic block, an injected draft-clear failure rolls back the
activation too, leaving the shell pending with its draft and trait snapshot restored by
`activate_player_character`'s existing rollback path. Double activation is additionally bounded by
Evennia's single-threaded Twisted reactor, the dispatcher's one-in-flight-per-session rule, and the
pending re-check inside the transaction: the first commit flips `creation_pending` to false, and any
later admission for the same shell fails its pending or ownership re-check rather than double-applying.

**Why persist a draft at all:** the focused design (§7.1, §8) explicitly requires that the browser
reconnect at any saved wizard stage and that Escape not discard saved server wizard state, which no
client-local form can guarantee across a WebSocket reconnect and reload. **Why a rules-owned
attribute rather than session state:** drafts must survive logout/login and server reload, and all
creation state writes must route through the deterministic core to preserve the single-writer
invariant.

**Relationship to `player-character-creation`:** the draft is a staging record, not canonical
identity. `creation_draft` never sets `age`, `apparent_age`, `race`, `subrace`, `key`, traits, or
`creation_pending`; those canonical attributes are written only by the atomic activation transaction.
This preserves the existing "invalid draft changes no character state" guarantee: a rejected
`creation.custom` leaves the prior draft and every canonical attribute unchanged, and an
unactivated character still has an empty trait set and no identity value persisted. Because the
original wording could be read to forbid any persistence at all, this change amends the
`player-character-creation` main spec with a `MODIFIED` delta that explicitly permits the bounded,
versioned, rules-owned `creation_draft` staging attribute and its atomic clearing on activation.

### D4. Four exact allowlisted creation adapters, all routing through the deterministic core

Following the `service_actions.py` template, `web/webclient/actions/creation_actions.py` defines
exact validators and narrow adapters:

- `creation.preset` — payload exactly `{preset_key}` (1..64 non-empty string). The adapter validates
  the key against `PLAYER_PRESET_REGISTRY`, persists the `preset_selected` draft, and refreshes the
  `creation` panel.
- `creation.custom` — payload exactly `{display_name, age, apparent_age, race, subrace,
  allocations}` with the wire bounds in the delta spec (name 1..80, ages integers 0..10000 so
  underage values reach the deterministic adult gate, race and nullable subrace registry keys
  1..64, allocations exactly the six axes each an integer 0..10000). The adapter builds a
  `CharacterCreationRequest(mode="custom", ...)`, runs the public
  `preflight_character_creation` (authoritative adult gate, registry membership, name rules,
  allocation bounds and budget), persists the `custom_filled` draft, and refreshes the `creation`
  panel.
- `creation.activate` — payload exactly `{}`. The adapter reads the stored draft through the wizard
  service and calls `world/rules/creation_wizard.activate_draft(account, actor)` (D3), which re-validates
  the draft and ownership inside one `transaction.atomic()` block, calls `activate_player_character`
  (all-or-nothing), clears the draft in the same transaction, then invokes the unchanged
  `relocate_to_starting_location(actor)` and `maybe_play_arrival(actor)`, and publishes a **full
  snapshot** so the exploration hand-off is atomic.
- `creation.reset` — payload exactly `{}`. The adapter clears the draft idempotently and refreshes
  the `creation` panel.

Every adapter obtains the owning account from the authenticated session's puppet (`actor.account`),
the same object the `character` command receives as `self.account`, and rejects any unknown or
authority-like field (actor, account, session, host, persona, skill, equipment, magic level, or
calculated stats). A `CharacterCreationError` from the deterministic service is mapped to a stable
rejection code and Traditional Chinese message through `world/rules/creation_messages.py` (D7).
No adapter assigns `.db`, traits, identity attributes, `creation_pending`, or the draft directly; all
writes are delegated to the rules service.

**Ownership is explicitly re-resolved, never assumed.** `actor.account` may be absent or may not own
the puppet in a malformed session, so each creation adapter explicitly verifies that the actor is a
`PlayerCharacter` with an accessible owning account and that `character in account.characters`
holds; a missing account, a non-character puppet, or an ownership mismatch is rejected with a stable
`creation_rejected` code before any deterministic write, matching the ownership check the
`character` command already relies on through `preflight_character_creation`. This keeps an abnormal
puppet from surfacing as an internal error or reaching a write path.

**Preset selection is a two-step confirmation in the browser, not an immediate activation.** The
existing `character preset <key>` command activates in one step; the WebClient intentionally splits
"choose a preset card" (`creation.preset` saves the validated `preset_selected` draft) from "confirm
and activate" (`creation.activate`), matching the focused design's "Choosing a preset submits the
stable preset key. Confirmation calls the existing creation path and activation service." Both paths
share the same deterministic activation service; only the interaction flow differs, and this is
documented so the command and the WebClient are not expected to have byte-identical step counts.

**Why `creation.custom` validates the whole form and `creation.activate` is separate:** this mirrors
the command wizard's flow (collect → confirm → activate) while keeping every authoritative check in
one deterministic transaction. The separate activate step is what makes a saved draft meaningful and
what makes "hidden or skipped controls cannot activate" enforceable: activation requires a validated
stored draft, never a partial client submission.

### D5. Activation publishes a full exploration snapshot and reuses the onboarding seam

After a committed activation the actor's `creation_pending` becomes false, so the next presentation
must change mode from `creation` to `exploration` and replace every panel. Rather than declaring an
affected-panel subset, `creation.activate` returns no affected panels, which makes the dispatcher
emit a full snapshot — the focused design's "after activation and puppet refresh, the server sends a
full exploration snapshot" (§7.5). The adapter performs the relocation and arrival through the
existing public onboarding functions so the South Gate move, map-knowledge recording, and welcome
message remain byte-for-byte unchanged, and a failed relocation preserves activated state with the
existing degradation notice instead of reopening creation.

**Why a full snapshot rather than `status`+`services`+... panels:** the mode change is part of the
envelope, and almost every panel changes meaning (status gains real resources, `services` and
`local_map` become available, `creation` becomes unavailable). One snapshot is the simplest correct
hand-off and avoids ordering assumptions between panels.

### D6. The creation dock is keyboard-first, form-capable, and owns the action dock in creation mode

A DOM-independent `elosern/creation_menu.js` model reduces the validated panel into preset cards,
the custom form (selected race/subrace, six allocation inputs, name and two adult age fields), the
saved-draft restoration, and the confirmation state, and produces the exact wire payloads. A
`creation_dock.js` GoldenLayout plugin renders it into the action dock in creation mode, following
the `combat_dock` / `services_dock` exclusive-mode ownership pattern: it mounts from the canonical
snapshot, unregisters its keyboard handlers and discards local state when a non-creation snapshot is
adopted, and never resets the KeyboardRouter it does not own. Arrow keys navigate finite lists and
buttons; Tab/Shift+Tab move through text/numeric fields; Enter activates or submits a complete
server-declared form; Escape pops exactly one menu level without discarding the saved server draft.
Activation and the destructive custom reset each require an explicit confirmation screen. Disabled
entries stay focusable with their explanation and submit nothing; validation messages are bound to
their field and announced through the existing accessible live region. A stale revision preserves
typed unsent values locally where safe, refreshes server-declared choices, and asks the player to
review rather than automatically resubmitting.

**Why Tab/Shift+Tab in addition to arrows:** the focused design (§8) specifies real form-field
navigation for text and numeric inputs; arrows remain the finite-list/button navigator exactly as
the shell requires. **Why the dock does not store creation state in localStorage:** the shell already
restricts localStorage to layout and safe display preferences, and the draft lives on the server.

### D7. Stable rejection codes and Traditional Chinese messages live in one mapping

`world/rules/creation_messages.py` maps every deterministic creation rejection —
`CharacterCreationError` raised by `preflight_character_creation` or `activate_player_character` for
unknown preset, invalid name, markup delimiter, underage actual/apparent age, unknown race, unknown
or incompatible subrace, malformed/out-of-span/off-budget allocations, not-pending, and
already-complete — to a stable `code` and a safe Traditional Chinese message mirroring the command
output. The browser and Telnet therefore present identical reasons. An unknown/unmapped exception
falls back to a generic `creation_rejected` code with a safe message and never exposes a traceback or
raw payload, mirroring `service_messages.py`.

### D8. The change touches no existing deterministic domain API

No rule, quest, guild, shop, combat, or onboarding behavior changes; `webclient-action-dispatch` and
`player-character-creation` are the only spec-level contracts amended (the latter to explicitly permit
the bounded rules-owned staging draft it otherwise could be read to forbid), and only `registry.py` /
`protocol.js` allowlists, the new creation dock surface, and the new `creation_draft` attribute change
in landed code. `world/rules/character_creation.py`'s public functions are consumed unchanged, and
`world/rules/onboarding.py`'s relocation/arrival are consumed unchanged. This keeps the single-writer
boundary intact and lets the change be reviewed entirely at the presentation/adaptation layer plus one
new deterministic staging service.

## Risks / Trade-offs

- [The custom-form descriptor can grow past the envelope budget] → Bounds are small (at most 8 presets, 8 races, 16 subraces, 16 profiles, six axes per profile, all strings ≤ 512 code points) and sized so a simultaneous-max payload stays far below the 65,536-byte envelope; a worst-case serialization test proves the structurally maximal realistic payload fits and an all-ceilings payload is rejected by the byte gate, both mirrored in Node.
- [A persisted draft could conflict with the "no identity persisted before activation" guarantee] → The draft is a separate staging attribute; canonical identity attributes, traits, and `creation_pending` are written only by the atomic activation transaction, a rejected save leaves them and the prior draft untouched (D3), and the `player-character-creation` main spec is amended with a MODIFIED delta that explicitly permits the bounded, versioned, rules-owned staging attribute and its atomic clearing on activation.
- [Activation and draft clearing could race or split across two writes] → `activate_draft` runs preflight, the activation writes, and the draft clear inside one deterministic `transaction.atomic()` block with the pending/ownership re-check against committed state; a concurrent or later activation fails its pending check, and an injected draft-clear failure rolls the whole transaction back (D3).
- [The browser could submit a calculated stat, an actor field, or a skipped step] → Exact payload schemas reject unknown fields; adapters re-validate through `preflight_character_creation`; activation requires a stored validated draft, never a partial submission (D4).
- [An abnormal puppet could reach a write path or surface as an internal error] → Every creation adapter explicitly verifies the actor is an owned `PlayerCharacter` with an accessible account and rejects ownership mismatch with a stable reason before any deterministic write (D4).
- [A bypassed client could send an underage record] → The adult gate is enforced by the deterministic `_validate_adult` inside preflight on every `creation.custom` and `creation.activate`; client constraints are advisory only, and a regression test asserts both underage fields are rejected with client validation disabled (D7).
- [Reconnect could double-activate or replay a draft] → The dispatcher's epoch/revision/request-ID/in-flight rules are reused unchanged; a stale or duplicate `creation.activate` never runs twice, and activation clears the draft inside the transaction (D4).
- [A mode change could desync or double-render the dock] → The client atomically adopts mode+panels at one revision; the creation dock unloads synchronously on a non-creation snapshot and only the active mode's dock owns action-dock focus (D6).
- [A failed post-activation relocation could reopen creation] → Relocation is a best-effort step after the committed activation, exactly as the command already does; a failure reports the existing degradation notice and the character stays activated (D5).
- [An unmapped rejection could leak internals] → Every deterministic creation reason is mapped to a stable code and Traditional Chinese message; an unmapped exception degrades to a generic safe message with no traceback (D7).

## Migration Plan

No stored schema changes and no data migration: the project is unreleased with zero users, the new
panel, draft attribute, and adapters are additive, and only the production registry's allowed action
set grows plus one staging attribute on pending shells. Implement in dependency order: creation
messages → wizard draft service → panel presenter + schema → action adapters and registry → client
protocol allowlist + `creation_menu.js` → `creation_dock.js` → Node and Evennia gates → managed
Playwright journeys → spec sync, traceability, and coverage. Rollback is the ordinary code-revision
rollback; no dual reader or data restore is needed because the change adds no canonical persistent
field beyond the staging draft and never weakens an existing deterministic check.

## Open Questions

None. The observable scope — one read-only `creation` panel, a server-owned wizard draft, four
allowlisted creation adapters, a keyboard creation dock with confirmation screens, the
server-authoritative adult gate, and the full exploration hand-off — is fixed by the approved parent
and focused designs. The two amended contracts are `webclient-action-dispatch` (grows to fourteen
actions) and `player-character-creation` (explicitly permits the bounded rules-owned staging draft),
and the existing service/combat docks' exclusive-mode ownership is the explicitly reused seam for the
exploration hand-off.
