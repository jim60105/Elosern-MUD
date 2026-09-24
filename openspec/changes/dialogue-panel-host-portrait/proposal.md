## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §4, §5.2, §8.2) puts the dialogue host's standing portrait in the stage's `actor-right` anchor, "sourced from the `art` panel's `portrait_catalog` entry for the dialogue host". The client cannot find that entry today. The `dialogue` panel's `host.portrait_ref` is `null` by schema:

- `web/webclient/presentation/dialogue.py` `_validate_host` rejects any other value ("portrait_ref must be null in this schema version"), and the presenter hard-codes `None`.
- The client mirror `web/static/webclient/js/elosern/protocol/panels/misc.js` rejects it the same way.
- The main spec `webclient-dialogue-session` says "`null` in this schema version".

So `stores/dialogue-view.js` always yields `portraitRef: null`, and the dialogue avatar has only ever shown the name's initial. The art catalog already carries the host: `world/rules/art_view.py` `_exploration_entities` includes every `is_dialogue_host` NPC and every named-portrait character in the room, keyed by `portrait_catalog_key(pk)`. The client must not build that opaque key itself (the combat participant frame's rule). The server must send it, as `world/rules/combat_view.py` already does for combat participants. This change (C10a in the AVG stage series) ships the reference, so the dialogue stage (C10b) has a portrait to stand up.

**Implementation profile:** logic. This is a presenter, validator, protocol mirror, and test change with no layout or look-and-feel judgement; a non-visual implementer completes it by making the server and protocol tests pass.

## What Changes

- **BREAKING (protocol): dialogue panel version 2.** `web/webclient/presentation/dialogue.py`:
  - `DIALOGUE_SCHEMA_VERSION = 2`.
  - `_validate_host` accepts `portrait_ref` as `null` or an opaque decimal catalog key of at most 32 characters. This is the same rule and bound as a combat participant's `portrait_ref` (`combat_panel.py` `MAX_PARTICIPANT_REF`).
  - `dialogue_presenter` builds the art view the `art` panel is built from (`world.rules.art_view.build_art_view(actor)`). When the host's identity is among that view's entities, it sets `portrait_ref` to `portrait_catalog_key(npc.pk)`; otherwise, and when the art view raises `ArtViewError`, it sets `null`. The key therefore matches a catalog entry exactly when the committed `art` panel carries one, including a placeholder entry.
  - The module docstring stops saying the host triple carries a null portrait.
- `web/static/webclient/js/elosern/protocol/constants.js`: `DIALOGUE_SCHEMA_VERSION = 2`. `web/static/webclient/js/elosern/protocol/panels/misc.js`: the dialogue host validator mirrors the new `portrait_ref` rule (the party-row validator in the same file keeps its null rule).
- `web/webclient-app/stores/dialogue-view.js`: comment only. `portraitRef` now carries a real key; the header stops naming the deleted `keywordMenuFor`, if C9 left that reference.
- Tests:
  - `web/webclient/presentation/tests/test_dialogue_panel.py`: the exact-vocabulary case expects the host's catalog key, and new cases cover a host absent from the art view (`null`), an art-view failure (`null`), the key matching the `art` panel's catalog key in the same snapshot, and validator drift (a non-decimal, over-bound, or numeric `portrait_ref` rejects; a decimal key validates).
  - `web/static/webclient/js/tests/protocol_dialogue.test.js`: version 2 fixtures; the drift list moves the `"42"` case from reject to accept and adds non-decimal and over-bound rejections.
  - Every client fixture of an available `dialogue` panel bumps `schema_version` to 2 (Vitest dialogue tests and stories).
  - `tests/test_panel_schema_version_parity_contract.py` needs no edit: it compares the constants, which move together.
- No client presentation change: the existing avatar code already resolves `portraitFor(artPanel, portraitRef)`, so it starts showing the image once the key ships. The stage portrait itself is C10b's work.

Out of scope:
- `StageActor`, the host in `actor-right`, and the speaking state: `webclient-dialogue-stage-actors` (C10b).
- The dialogue choices over the stage and the paged dialogue line: `webclient-dialogue-choices-overlay` (C10c).
- The party panel's `portrait_ref` (still `null` in its own schema) and the exploration descriptors' `portrait_ref`: no stage surface needs them.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-dialogue-session`:
  - REMOVED "The dialogue panel is an exact read-only version-1 presentation panel".
  - ADDED "The dialogue panel is an exact read-only version-2 presentation panel": the host's `portrait_ref` is the art catalog key when the host is in the art view, else `null`.

## Impact

- Server: `web/webclient/presentation/dialogue.py`.
- Protocol mirror: `web/static/webclient/js/elosern/protocol/constants.js`, `protocol/panels/misc.js`.
- Client comment: `web/webclient-app/stores/dialogue-view.js`.
- Tests:
  - Python: `web/webclient/presentation/tests/test_dialogue_panel.py`.
  - Node: `web/static/webclient/js/tests/protocol_dialogue.test.js`.
  - Vitest and stories: every file `grep -rln 'kind: "dialogue"' web/webclient-app/tests web/webclient-app/stories` lists (after C6c: `tests/message_window_dialogue.test.js`, `tests/dialogue_view_model.test.js`, `tests/dialogue_store.test.js`, `tests/store/store_slices.test.js`, and the `MessageWindow` / `AppShell` stories).
- Spec traceability: `webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-1-presentation-panel` (one annotation in `test_dialogue_panel.py`) re-anchors to `…-version-2-presentation-panel`.
- Dependencies: archive order C9 (`explore-talk-open-action`) → C10a (this change) → C10b → C10c. No hot-spot client file is touched, so this change can be implemented in parallel with any client change; only its archive position is fixed.
