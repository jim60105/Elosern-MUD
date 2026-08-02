## Context

A new player's first session currently shows Evennia's default connection screen and a bare
prompt-based `character` wizard. The project already ships a wired-in
`server/conf/connection_screens.py` (the default `CONNECTION_SCREEN_MODULE` target) with a minimal
generic screen, and a functional preset/custom activation flow in `commands/character_creation.py`
backed by `world/rules/character_creation.py`. This change restyles only the presentation; the
activation semantics stay untouched.

Player-facing prose is Traditional Chinese; lore data lives in immutable registries
(`world/lore/player_presets.py`, `world/lore/races.py`).

## Goals / Non-Goals

**Goals:**
- Replace the default Evennia login presentation with a project-authored connection screen
  (title banner, premise, CONNECT / CREATE prompts).
- Show a world introduction to a pending character after login, before creation.
- Restyle the `character` command with registry-derived preset previews and explanatory custom
  prompts.

**Non-Goals:**
- No change to preset/custom activation logic, validation, the adult gate, or atomicity.
- No onboarding state (beat engine, guard, `onboarded` flag) — that is the `onboarding-guide` change.
- No multi-character accounts.

## Decisions

**D1 — Connection screen lives in the existing `server/conf/connection_screens.py`.**
Rewrite the `CONNECTION_SCREEN` string variable: title banner, one-line premise, CONNECT/CREATE
prompts, and the retained note that new accounts must create an adult character. No new module and no
new setting; the default `CONNECTION_SCREEN_MODULE` already points here. A static string suffices —
nothing on the screen is dynamic.
- *Alternative considered:* a `connection_screen()` function returning dynamic text. Rejected: no
  dynamic content exists; a function would be speculative.

**D2 — World introduction is hooked in `Account.at_post_login(session)`.**
Add the hook in `typeclasses/accounts.py`, calling `super()` first, then sending the introduction only
when the account's auto-created character is still `creation_pending`. After the introduction, the
hook also renders the `character` command's no-argument start screen (see D6), so the player sees the
creation interface immediately. Because a pending character can only use the creation command set,
the introduction reliably precedes the creation interface on every login until activation.
- *Note on ownership:* this hook is a single coordinator. The `onboarding-guide` change depends on
  this one and extends the same hook (calling `maybe_play_arrival` for activated characters) rather
  than adding a second hook.
- *Alternative considered:* sending the introduction from the pending command set's creation. Rejected:
  the introduction should appear on login itself, and gating on `creation_pending` already scopes it
  to new players exactly once per session.

**D3 — Introduction prose lives in a new read-only module `world/intro.py`.**
A single constant (`WORLD_INTRODUCTION`, 2–3 lines) imported by the account hook. Kept out of the
command modules so the same prose is reusable by any future entry surface. This change owns this
module; `onboarding-guide` does not depend on it.

**D4 — Preset previews are registry-derived, with minimal registry extension.**
- Add `description: str` to the frozen `RaceProfile` dataclass (one Traditional Chinese one-liner per
  race) and populate the three registry entries. This is a natural fit: lore is the single source of
  truth, and `look`/help can reuse the same descriptions later.
- Add `emphasis: str` and `background: str` to the frozen `PlayerPreset` dataclass and populate the
  three presets.
- The restyled no-argument `character` output renders: framing line → for each preset, race one-liner
  (from `RACE_REGISTRY`) + emphasis + background (from the preset). Custom-mode prompts gain an
  explanatory line per race and per allocation axis, drawn from the same registries.
- *Alternative considered:* hard-coding preview strings inside `CmdCharacter`. Rejected: the project's
  invariant is that consumers read registry values instead of duplicating balance/presentation data.

**D5 — Activation semantics are untouched.**
`world/rules/character_creation.py` is not modified. Only `CmdCharacter` output text and the new
registry fields change.

**D6 — The creation start screen is a reusable renderer.**
The no-argument `character` presentation (framing + preset previews + custom prompt) is extracted
into a callable so `Account.at_post_login` can render it right after the introduction (D2) and
`CmdCharacter` can reuse it. The activation path itself is unchanged.

## Risks / Trade-offs

- [Frozen dataclass field additions break existing constructors] → New fields are keyword-only at the
  end of each dataclass; the three registry entries are updated in the same change; run the full
  relevant test suite to catch any positional construction.
- [`at_post_login` hook ordering] → Call `super().at_post_login()` first and keep the hook side-effect
  free for activated accounts, preserving Evennia's default login flow.
- [Connection screen not covered by integration tests] → Test the module's exported screen content
  directly; EvenniaTest does not exercise the unlogged-in portal screen.
