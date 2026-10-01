## Context

See proposal.md for motivation. Current declarations (declaring preset → partner preset, relationship label):

| Declaring preset | Partner (companion) | Partner race/sex | Label |
|---|---|---|---|
| `violet_altoria` 薇歐蕾特 | `lidzia_rosenthal` 莉茲婭 | human/female | 貼身近侍 |
| `lidzia_rosenthal` 莉茲婭 | `violet_altoria` 薇歐蕾特 | human/female | 殿下 |
| `yuka_darknight` 悠花 | `yuna_darknight` 悠奈 | elf/female | 雙胞胎姊姊 |
| `yuna_darknight` 悠奈 | `yuka_darknight` 悠花 | elf/female | 雙胞胎妹妹 |

`world/rules/starting_companions.py::_build_persona_record` returns `preset.persona.to_record()` with `social_connection[player.key] = relationship`. The builder has no transaction of its own and deletes the partial NPC on failure; `activate_player_character` wraps it in its atomic block. `world/lore/` must not import `world/rules/`, which is why the rules-side sweep exists.

The user's amendment (design doc §13a): the partner preset is the single authored source for the companion's characterization. The template is a build-time input only — every built companion (one per activating player character, so the shipped world can hold several) is an independent persisted instance that detaches from the template, exactly like the derived persona card. The five official presets (the four companions plus 伊洛) keep their established persona prose; only the two new NPC-need fields are authored.

## Goals / Non-Goals

**Goals:** companion NPC personas derive only from the partner preset's extended persona plus a factual owner line; the companion is otherwise mechanically identical to its partner preset; every card write goes through the shared persona writer with companion provenance; the authored offline greeting persists on the instance so no runtime consumer needs a lore lookup.

**Non-Goals:** changing any non-companion preset, the player activation persona record, or party/affinity mechanics; rewriting the five presets' established prose (official designed characters); companions already built in an existing database (the cutover owns those); voice read routing (dialogue-consumption owns it); a fixed-dialogue editor or profile registry entry for companions.

## Decisions

### D1. `PresetPersona` gains two optional NPC-need fields

`speech_style: str = ""` and `greeting: str = ""` join the frozen dataclass with empty defaults, so every shipped non-companion preset and `to_record()` output stay byte-identical: **neither field is projected into the player persona record** — activation writes the same six keys it writes today, so a player activating `violet_altoria` sees no change. Lore-side shape validation: `greeting` normalizes through `world.lore.npc_card._normalize_text_leaf` and rejects a newline or > 300 code points after normalization (the `NpcVoiceLines` bounds, reused from the same lore module the profile shape already uses). The four companion presets author both fields; `speech_style` is new prose per companion (twins must not differ only by name), `greeting` is the offline first-contact line. Companion declarations keep exactly `preset_key`/`affinity`/`relationship` — no fourth field, no profile reference.

Alternative rejected: a thin `companion_*` profile holding only the voice lines while the persona comes from the preset — that splits the authored facts across two registries, which is exactly the second-source problem the amendment removes.

### D2. The compact card derives deterministically from the preset persona

One pure lore-side derivation (lives with the preset vocabulary or the card contract; rules and cutover both call it, never re-implement it):

- `identity.public` / `identity.hidden` ← preset identity layers verbatim.
- `personality`, `life_story`, `habit` ← preset fields verbatim.
- `speech_style` ← the new preset field verbatim (required non-empty: a companion preset with an empty `speech_style` cannot derive a valid card).
- `appearance` ← the preset's authored non-empty appearance sub-keys, in `_SUBKEY_ORDER`, joined with `；` (one text leaf; the card has no structured appearance). Rejected: authoring a second flattened appearance string on the preset — a second copy of the same visual facts.
- `social_connection` ← one factual owner line `f"{owner_key}：{relationship}"` first, then each preset `social_connection` entry as `name：relationship` lines in declaration order, when the preset authors any. `owner_key` is the owning player character's key at build time. Rejected: storing the relationship only in metadata — the NPC's own prompt must know whose companion it is.
- The preset's `background` is player-creation prose with no card leaf and is not derived.

The rules sweep at `world/rules/starting_companions.py` import time replaces the old relationship-length check: for each companion-declaring preset, derive the card with a synthetic 64-code-point owner key (`NAME_MAX_LENGTH`) and validate it through the compact card contract (every required leaf non-empty, each leaf ≤ 600, rendered block ≤ 2,000). A preset that cannot fit fails rules import naming the preset, so a real activation can never fail the contract on a long name.

### D3. The builder derives, writes, and persists the voice line

`build_starting_companion` replaces `npc.db.persona = _build_persona_record(...)` with, at the same point in the build and inside the existing `try` whose `except` deletes the NPC:

1. `initialize_npc_persona(npc, card, {"kind": "companion", "profile": partner_preset_key, "owner": player.pk})` where `card` is D2's derivation for this owner. `_build_persona_record` is deleted.
2. `npc.db.npc_offline_greeting = greeting` when the preset authors one — the per-instance offline-greeting field (plain text, ≤ 300 code points after normalization, single paragraph), **not** inside `db.persona` (the card is exactly seven fields) and **not** inside `db.npc_persona_meta` (metadata is never prose). It is a generic contract any future producer with an authored greeting (offline bundles, quest director, imports) can write; this change ships the companion writer only. Dialogue reads it (routing specified by `npc-persona-dialogue-consumption`); the author editor edits it (transport specified by `npc-persona-editor-window`'s server delta), and a greeting-only edit advances `persona_version` like any changed leaf, so the version-checked update and the stale-persona gate cover it without a second version counter. The preset only seeds the field at build; later edits detach from the template.

The preset is still read for every mechanical value. A failure of either write deletes the partial NPC and re-raises, inside `activate_player_character`'s atomic block as today.

### D4. The empty `companions` profile slice is deleted

`world/lore/npc_profiles/companions.py` (`ROWS = ()`, an archived-registry seam awaiting change 9) and its assembly entry in `world/lore/npc_profiles/__init__.py` are removed: with the preset as anchor, a companion profile slice has no referent, and an orphan-profile future check would otherwise have to exempt it. The four `starting_companion` rows in `world/lore/npc_profiles/inventory.py` keep their `companions` owner label (the inventory names the owning change slice, and this change owns the companion sources' characterization rule); the roster's resolution rule for that kind becomes "derive from the partner preset's extended persona" (change 19's artifact carries that wording).

## Risks / Trade-offs

- [Preset persona drifts past the card budget as prose evolves] → the D2 import-time sweep re-sweeps on every boot; a drift fails loudly naming the preset, before any activation.
- [Existing activated characters in a dev DB keep old companion personas and no offline-greeting field] → expected; `npc-persona-roster-cutover` re-derives from the same D2 rule and writes the field from the preset, recomputing the owner line from the existing binding.
- [The amendment contradicts the parent design's older companion clauses] → §13a records the user's supersession explicitly; the archived profile-registry main spec's inventory requirement stays valid because the inventory rows remain and only the resolution rule moves.
- [A future author sets `speech_style`/`greeting` on a non-companion preset] → the fields are inert for players (never projected); harmless by construction, and `adding-player-presets.md` documents them as companion-NPC fields.
- [The player edits a greeting the preset never authored (empty instance field)] → the editor presents the field as empty and editable; clearing it restores silence-on-degrade, which is the authored equivalent, and never falls back to the preset value at read time.
- [Preset authoring docs contract pins the persona field list] → update the documentation in the same change and run `tests.test_preset_authoring_docs_contract`.
