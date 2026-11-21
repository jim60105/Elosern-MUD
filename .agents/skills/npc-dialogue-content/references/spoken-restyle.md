# Spoken-prose restyle

Field notes from the 2026-11-21 rewrite of every file under
`world/lore/dialogue/content/` (83 files, 19 host voices, 45 residents). Use
this with `SKILL.md`; it does not replace the schema or the source gate.

The voice target itself is `references/writestyle-request.md`. This file is that
brief applied to the authored-scene format, plus what the pass measured.

## The register in this scene format

A spoken light-novel voice, not an essay voice. The format splits it in three:

| Line kind | Whose voice | What it carries |
|---|---|---|
| `speech` / `host` | the NPC's own first person | self-assessment, asides, self-mockery, a digression that comes back to the point |
| `narration` | third person | one or two sentences of sensory detail and attitude; may name the host and address the guest as 你; never the player's 我, race, gear or identity |
| `speech` / `actor` | the guest | a complete spoken question with a follow-through, never a menu label, never a commitment |

The interior voice lives in the host's speech. Do not try to move it into
narration: narration has no speaker attribution, and a first-person narration
line reads as the player and breaks the possessed-companion contract.

## Rhythm

- A short line lands the answer; the long line explains it. Vary the length
  inside one scene; uniform sentence length is the clearest tell of generated
  prose.
- Complete the turn. A clipped ending either disappears or becomes a
  reason-bearing closing line.
- The host answers in speech, not in headings. A one-to-four character verdict
  sentence opening the answer (`「收。」` `「踏昏。」` `「有。」`) is now a lint WARN:
  fold it into the next clause (`「新鮮的獸肉我都收，放上檯面過磅。」`) or keep the
  particle (`「收啊，……」`).

## Decompress

Generated Chinese deletes the subject, the connective, and the content of the
event. Restore them; the line gets longer and easier to read.

| Compressed | Restored |
|---|---|
| `她目光如刀。` | `她看了我一眼，先看手，再看肩膀，像在估我能撐幾下。` |
| `一併零售。` | `也擺在牆上一起賣。` |
| `當熱源。` | `借她的窯火加熱。` |
| `溫柔又體貼的她。` | `她講話前會先停半拍，像怕撞到人。` |
| `散發出威嚴。` | `她一站直，旁邊的人就自動閉嘴。` |

The last row is the commonest failure: a physical verb on an abstract object.
Name the mechanism instead.

## Voice separation

The brief is shared, the person is not. Before handoff, list every host in your
batch with one line of their `speech_style` and check that no two share a
sentence pattern. A watch captain who speaks in orders, a jeweller who talks
with her hands, and a herbalist who answers in numbers of days must not all
open with the same aside.

## Tics spread and must be measured

One suggested phrase in the brief reached 44 of 83 files in a single pass:
「我這人」 50 times, 「像在」 25 times. Every NPC then sounded like the same
narrator, and every locked 私語 refusal shared one sentence frame.

Cap them before handoff:

| Pattern | Cap |
|---|---|
| a self-referential formula (`我這人`, `說來`, `老實說`) | at most 3 files |
| a simile frame (`像在`, `像是`, `彷彿`) | at most 8 files |
| a refusal opener construction | one per file; never two hosts in one village |

Measure with a count over the directory, not by memory:
`grep -c '我這人' world/lore/dialogue/content/*.yaml | grep -v ':0'`.
Rewrite per character; replacing one shared formula with another shared formula
does not fix it.

## Bans that the lint cannot fully see

- 古風: 之／其／乃／矣／焉／兮, four-character set phrases, 對仗, 排比,
  `彷彿／宛如／好似／猶如`, em dash, mid-sentence colon, `就像`.
- 武俠: 江湖, 客官, 過招, 招式, 劍招, 刀招, 祕技, 拜師, 功法, 內力, 真氣,
  掌門, 功夫.
- AI phrases: 往往, 確保, 至關重要, 一個事實, 關鍵差異, 系統性地, 很精準,
  誠實面對, 只有…才能…, 不是…而是…, 不只…更…, 這不是…是….
- Translation-variant characters: write 曬, not 晒; 個, not 个.

## Structure is not yours

A restyle changes prose and `revision` only. Before handoff, diff every file
against `HEAD` and prove:

- every `topic_id`, `scene_id`, `keyword`, `label`, `requires`, `unavailable`,
  `predecessors`, `disclosure`, and every variant `variant_id`/`priority`/`when`
  is byte-identical;
- each changed scene's `revision` rose by exactly one, scene by scene (a file can
  carry `r3` and `r5` at once);
- formal scenes still open with a complete actor line and still contain a host
  line;
- a locked refusal may be a single line; the schema minimum is one and the
  shipped files use one.

## Handoff hygiene

- Write plain YAML. A file whose first line is `*** Begin Patch` breaks the
  whole snapshot; never pass a patch envelope as file content. After writing,
  import `world.lore.dialogue.DIALOGUE_SNAPSHOT` at once: one bad file blocks
  startup and the error names the file.
- `altoria_guild_master.yaml` carries a `services:` root block. The dialogue
  codec allows it (`allowed_root` includes `services`) and the guild turn-in
  binding needs it, but the lint's root-key check still reports it as an
  unexpected key. Keep the block; that one ERROR is a stale whitelist, not a
  content defect.
- A whole-directory restyle refreshes every affected `dialogue_table` row in
  `docs/development/npc-editorial-review.md`: same row per source, disposition
  rewritten with the file's current per-scene revision map. The row count stays
  equal to the number of live dialogue keys; never add a second row for a source.

## Final read

Read one scene from each village aloud as a conversation. Stiff actor questions
and clipped host answers are the defects that pass both linters.
