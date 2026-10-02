## Why

P2-3: a valid editable greeting may contain Evennia tokens such as `|/`, `|r`, or MXP markup; current text consumers interpolate the field directly into `msg`. Plain author text must display literally without altering stored prose, raw OOB values, or trusted default formatting.

## What Changes

- Distinguish editable instance overrides from trusted table/profile defaults during greeting resolution.
- Escape only override text once at each Evennia text-output boundary, covering both no-keyword command branches, browser talk-open narrative/action messages, and LLMNPC degraded speech.
- Keep canonical storage, editor values, dialogue-session/OOB lines, and settled-line callbacks raw; browser plain-text surfaces remain plain text.
- Preserve default greeting formatting and keyword behavior; explicitly reconcile persona-editor privacy wording with its already-authorized public greeting presentation.
- No global markup disabling, stored-text stripping, greeting budget change, companion rewrite, or LLM integration feature.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scripted-dialogue`: literal editable greeting presentation across all no-keyword/degraded text consumers.
- `npc-persona-editor`: private editor data remains private while intentional public greeting speech is explicitly permitted.

## Impact

One engineer-day: `world/rules/dialogue.py`, `commands/talk.py`, `typeclasses/npcs.py`, `web/webclient/actions/exploration_actions.py` and focused consumer/transport tests. Retain current 300-code-point single-paragraph bound (the review's 600 statement does not match current source). No database migration or in-place cutover (§13b); companion instance greetings stay derived from their sole preset source (§13a).

## Batch:

depends-on: npc-persona-visible-targets

Code-conflict notes: ordering is for integration, not a runtime dependency: `exploration_actions.py` is also changed by visible-target filtering. `typeclasses/npcs.py` overlaps `npc-authored-canonical-ages` in a different function. Persona-action and dialogue test modules may overlap other fixes; preserve separate assertions. No `npc_card.py` normalization edits belong here.
