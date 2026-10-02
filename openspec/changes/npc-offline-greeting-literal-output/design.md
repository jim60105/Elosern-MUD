## Context

Static sources: `normalize_offline_greeting` (`world/lore/npc_card.py:324–338`) normalizes and bounds a single paragraph at **300**, not 600, code points; it intentionally accepts `|/`. `offline_greeting_for` (`world/rules/dialogue.py:176–187`) returns the non-empty field raw, otherwise table/profile default. `commands/talk.py:124–135` interpolates both host and componentless greetings; `LLMNPC.at_talked_to` (`typeclasses/npcs.py:613–624`) sends degraded greeting via `msg` and passes the same string to `settled_line`; `_talk_open_adapter` (`exploration_actions.py:531–541`) stores raw line but also sends/returns an interpolated message. Installed Evennia ANSI escape utility `evennia.utils.ansi.raw` (614–624) doubles pipe and brace markers. ANSI parser documentation (140–141, 264–266) describes literal doubled pipe handling.

The current persona-editor privacy requirement says no greeting text in narrative/panels, contradicting the existing public greeting behavior. Amend it narrowly: private editor payloads stay private; selected greeting speech/session line is intentionally public. Do not relax hidden-card restrictions.

## Goals / Non-Goals

**Goals:** Literal editable greeting text on every actual speech consumer, raw canonical OOB/state values, preserved trusted formatting.

**Non-Goals:** Global ANSI/MXP disable, stripping/escaping stored text, keyword/script rewrite, escaping all generated LLM output, new greeting schema/budget, companion characterization changes.

## Decisions

### Keep one resolution policy with source information

Introduce a minimal immutable resolved greeting value containing raw text and an `is_override` distinction, resolved from the instance field first, then authored table/profile defaults, else absent. Migrate all greeting consumers to that one resolver; remove the obsolete string-only resolver rather than adding permanent aliases or duplicating precedence at callers. Keep `authored_greeting_for` for the editor default preview. A companion's preset-seeded instance field follows the override rule because that field is editable; it needs no separate trusted-origin database flag. Classification follows the source branch, not string equality: an override equal to its default is still plain text.

### Escape only at Evennia message composition

Use the established Evennia literal-markup escaping convention (the installed ANSI `raw` utility, or the repository-equivalent pipe escaping that demonstrably neutralizes the same grammar). Apply to the resolved raw override **once** when building an Evennia-facing message; authored fallback strings are untouched. Protect `|/`, `|r`, `|n`, `|lc…|lt…|le` command links and `|lu…|lt…|le` URL links, as well as already doubled pipes. Do not mark the whole message `raw=True`: that would also change trusted wrapper/default formatting.

Consumer matrix:

| Consumer | Evennia message/action text | Session/OOB/callback text |
|---|---|---|
| `CmdsTalk` scripted host, no keyword | Escape override before interpolation; usage line remains trusted | No new session write |
| `CmdsTalk` componentless/profile NPC, no keyword | Same single-boundary policy | No new session write |
| `_talk_open_adapter` | Escape override in `actor.msg` and matching narrative action-result message | `open_or_refresh_dialogue` receives raw text; dialogue panel receives raw line |
| `LLMNPC.at_talked_to` degraded | Escape override in `character.msg` | `settled_line` receives raw line only while existing completion gates pass |
| Persona editor read/update/default preview | No greeting speech | Raw stored/default text, unchanged |

Browser dialogue/editor text nodes continue treating raw values as text, not HTML/ANSI. Audit actual renderer before implementation and adjust only a consumer that interprets these raw slots as markup; do not pre-escape raw protocol values. A reconnect/republication must not escape a persisted escaped copy or display doubled pipes. The raw resolver itself does not mutate storage, advance versions, or suppress visibility/schedule/stale-persona gates.

### Keep formatting of trusted defaults

Empty override resolves through authored table then profile precedence. Default markup continues through the existing parser unchanged. Known keywords and misunderstanding lines never read the editable field. No normalizer/stripper is added to the output path, and output expansion from escaping does not alter raw code-point budget acceptance.

## Risks / Trade-offs

- [Double escaping or markup re-interpretation] → Future verification runs messages through actual Evennia ANSI/MXP and browser narrative renderers, not assertions on an escape helper alone; include paired-pipe input.
- [Session pollution] → Assert raw greeting equality after opening and after degraded callback, then reconnect and inspect panel display.
- [Source confusion] → Regression saves override identical to a formatted default and confirms it stays literal; clearing restores formatted default.
- [Privacy drift] → Public greeting speech is the sole exception, not card fields/default preview broadcast or logged editor payloads.

## Migration Plan

No migration or origin metadata needed. Existing editable field values are treated as plain text regardless of producer. Trusted registry defaults remain trusted. Development adoption continues to use reset documentation (§13b); official companion prose/preset sources remain preserved (§13a).
