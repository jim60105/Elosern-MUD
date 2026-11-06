# Human review: the elf sex rejection message

This is the change's named review document. It covers the one piece of **player-facing prose**
this change adds and nothing else. It is a human review: no requirement in the delta specs
asserts the wording, because wording is a judgement, not a mechanism.

## What the human reviews

| Surface | Exact text proposed | Where it lives |
| --- | --- | --- |
| Creation rejection shown by the WebClient creation dock and by the Telnet creation output | `所選種族不允許這個性別。` | `world/rules/creation_messages.py`, code `sex_not_allowed_for_race` |

For reference, the neighbouring lines of that table already read `性別不是可用的選項。`
(`unknown_sex`) and `精靈的屬性親和由子種族決定，不能自行選擇。` (`elf_affinity_rejected`), so
the new line keeps the table's register: one short Traditional Chinese sentence, no command or
mechanic named, no English, no punctuation outside the full stop.

## Review checklist

1. **Canon fidelity.** The sentence must state a world fact, not a UI rule: the character's race
   does not allow that sex. Compare against the canon paragraph in `docs/lore/overview.md` that
   says every elf is female, and against the rest of `CREATION_REASON_MESSAGES`, which describes
   the world-side situation rather than the input field.
2. **Register and length.** Traditional Chinese, one sentence, under the WebClient message bound
   (1..512 code points), matching the tone of the sibling rows. Confirm it does not read as a
   second sentence glued on or as an internal code name.
3. **No OOC vocabulary.** It must not name a command, a panel, a field name, a mechanic, or the
   words 種族清單/下拉選單/伺服器 — the sibling rejections keep to the fiction's own vocabulary.
   (The English field name `sex` stays in the English diagnostic message and the English spec
   text; the player-facing line is the Chinese one.)
4. **Truthfulness of the Telnet path.** The same string is what a Telnet player reads after
   activating an elf draft whose stored sex the race forbids (the wizard cannot submit one, but a
   tampered draft can reach activation). Confirm the sentence still makes sense there without a
   field label next to it.
5. **No other copy.** Confirm no other player-facing string changed: the success lines
   (`已儲存自訂角色資料。`, `已儲存預設角色選擇。`) and the `creation` panel descriptor are
   untouched, and `SEX_VALUES`' labels (`女性`, `男性`, `其他`) are unchanged.

## Disposition

The reviewer's findings are recorded here (or in a `review-disposition.md` beside it) before the
change is archived, and any accepted rewording lands as a follow-up commit editing
`CREATION_REASON_MESSAGES` only — no behavior test is added or removed for it, since the
mechanism requirement covers the code, not the prose.
