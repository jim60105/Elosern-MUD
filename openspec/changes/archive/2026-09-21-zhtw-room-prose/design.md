## Context

`room_desc_zh` holds English. So does every grid room's `desc`. The field name, the project conventions and one capability's spec all say otherwise, and nothing enforces any of them.

## Goals / Non-Goals

**Goals.** Nine descriptions converted. One rule, stated where it covers every room. A guard so this cannot silently recur.

**Non-Goals.** No new rooms, no re-description — the converted text says what the English said. Not a translation pass over anything but rooms: items, dialogue, scene archetypes and Limbo are already Chinese.

## Decisions

### The rule goes on `grid-room-sync`, not on each settlement

`village-ciaran-map` already carries a Chinese-prose requirement, which is why the village is the only place the violation is formally a violation. Stating it per settlement means the next settlement's author has to remember to restate it.

`grid-room-sync` is the capability that owns rooms as a category, so the rule lands there once and covers the capital, the village and whatever comes next.

### The guard checks prose, not characters

"Contains a CJK character" passes on a Chinese room name with an English body, which is exactly today's state. The check is on the description text: it must be predominantly Han, and must not contain a run of English words long enough to be a sentence.

That is deliberately a heuristic rather than a parser. It catches the failure that actually happens — someone writes an English description — without pretending to judge translation quality.

### The two map modules are excluded, and that is a sequencing decision

Both are being rewritten by other changes in this set, and both of those changes author their new prose in Chinese. Converting them here would collide on the same files and produce prose that is then discarded. This change takes the nine descriptions nobody else is rewriting.

The consequence is that this change must land **after** the capital replan and the village expansion, or the guard will fail on map rooms those changes have not converted yet. That ordering is stated in the tasks.

## Risks

**The guard may fire on a legitimate mixed string.** A description naming a command, or a proper noun kept in Latin script, could trip a naive word-run check. Mitigated by tuning the threshold against the converted corpus rather than picking a number first, and by the check being on run length rather than on the presence of any Latin character.
