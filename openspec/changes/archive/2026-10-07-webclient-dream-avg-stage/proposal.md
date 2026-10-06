## Why

The browser dream surface (`DreamPanel.vue`) works, but it plays as a web form instead of a scene. A 58vw dark box covers most of the bright cloud-throne artwork and shows everything at once: the opening prose (again on every turn), the scene, the dialogue, two status lines written as sentences, a large textarea, a direction editor nested two `<details>` deep, and three exit buttons whose differences are unclear. The exchange budget and the goddess's excitement track have no visual form. A failed generation discards what the player typed. Escape ends the finite dream with one keystroke. The webclient is being rebuilt as an AVG (visual-novel) stage, and the dream is now the one full-screen surface that ignores that language.

## What Changes

- Restage the dream as an AVG scene over the full-bleed artwork:
  - A title crest and a **keepsake card** (此刻的念頭) sit in the art's empty sky.
  - A **reply bar** docks to the top of a 2/3-width message band.
  - The band's right third stays open onto the goddess.
- Give both server-authored tracks a visual form:
  - The exchange budget becomes **six pips** on the reply bar, and the pip the next send would spend pulses.
  - The goddess's excitement becomes a **five-segment gauge** with the canonical level label on her name plate.
  - Both are exposed as `role="meter"` with textual values, so meaning never depends on colour alone.
- Pace the conversation:
  - On a first entry the opening types as narration.
  - A **live** exchange increase reveals the scene narration, then the goddess's line, through the shared typewriter clock, which honours motion level and text speed.
  - A mount or reconnect shows the current exchange in full, and the player can step back one beat (重讀).
  - While pending, the player's own words are echoed and the name plate breathes.
- Make the 念頭 (story direction) concept legible:
  - The keepsake card always shows the summary that would be carried out right now, where it came from (取自你剛才的話 / 已記下 / 已改寫・未記下), and which story it attaches to.
  - One flat modal **念頭 sheet**, with no nested disclosure, edits the summary (with a code-point counter), the thread (radios, filterable past eight), and the five preference lists (chips).
- Separate the exits by meaning. Card rows: ① edit the 念頭, ② 帶著這個念頭醒來 (confirm), ③ 記下念頭，繼續作夢 (draft), ✕ 醒來 (awaken). Digits 1–3 activate rows ①–③.
  - The single primary action is 訴說 while conversation is possible and the carry-out row once all six exchanges are spent.
- Recovery and safety:
  - A failed generation refills the reply bar with the words just sent (再說一次) and consumes nothing.
  - An empty or over-2000-character summary is refused locally inside the sheet, never silently truncated.
  - Awakening asks for confirmation only when local unsent words or unsaved 念頭 edits would be lost.
- **BREAKING** (player-facing input): Escape no longer awakens the dream. It closes the top layer, leaves a text field, or moves focus to the ✕ 醒來 row. Enter sends a reply and Shift+Enter inserts a newline. The browser paragraph of `docs/game/command-reference.md`, which said Esc awakens, is updated.
- No server, wire-schema (`dream` panel v2), action, or text-command change.

## Capabilities

### New Capabilities
- `webclient-dream-stage`: the browser presentation and interaction contract of the dream collaboration surface. It covers AVG layout over the official artwork, visual exchange and excitement tracks, beat pacing and reveal rules, the keepsake card and 念頭 sheet, exit semantics and the awaken check, failure recovery, keyboard and focus behaviour, and legibility over near-white art.

### Modified Capabilities
<!-- None. `dream-sleep-surface` already requires both clients to expose remaining
     exchanges, free text only below six, confirm/draft choices and awakening on every
     failure state; this change satisfies that requirement unchanged and only adds the
     browser-specific presentation contract. -->

## Impact

- **Docs:** `docs/game/command-reference.md` (the browser dream key map).
- **Code:** `web/webclient-app/components/DreamPanel.vue` (rewritten), `web/webclient-app/stories/World/DreamPanel.stories.js` (state stories: Storyboard/arrival, Conversing, Converging, Pending, Failed, Drafted, AtCap, ManyThreads, Disconnected, NoArt), `web/webclient-app/tests/dream.test.js` (rewritten for the new structure).
- **Traceability:** a new evidence bridge, `web/webclient/tests/test_vue_dream_stage_evidence.py`, owned by the existing `web.webclient.tests` shard label, runs the matching Vitest cases per `webclient-dream-stage` requirement; its `covers_requirement` annotations attach at archive once the delta sync creates the new main IDs.
- **Reused, unchanged:** `composables/use-typewriter.js`, `lib/message_reveal.js` (`effectiveCps`), `components/focus-trap.js`, the token sheet (`--motion-*`, `--band-h`, `--band-ornament`, `.ui-btn`).
- **Unchanged:** server (`server/dream_service.py`, `world/narrative/dream_surface.py`), panel validator (`protocol/panels/dream.js`), `AppClient.vue` mounting, the text `dream` command and its syntax, and the Storybook story id `World/DreamPanel` (component-manifest and showcase evidence stay valid).
