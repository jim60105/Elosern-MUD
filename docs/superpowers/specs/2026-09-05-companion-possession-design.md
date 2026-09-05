# Companion Possession — Design

**Date:** 2026-09-05
**Status:** Approved (brainstorming session 2026-09-05); third of three sequenced designs
(R3 → R2 → R1). Depends on both the profession registries design and the service-anchoring
design (`2026-09-05-profession-registries-design.md`,
`2026-09-05-service-anchoring-design.md`).
**Scope:** Temporarily transferring control (never ownership) from a player character to one of
their bound NPC companions — possession as a party-core-patterned single writer, the
`PlayerCharacter`-assumption gates it must thread, autonomy silencing, handback paths, and the
v1 presentation boundary.

---

## 1. Product Context

The game is single-player per design, but one account owns several characters. The initially
imagined route for "play from the companion's eyes" — two player characters partying and
switching via 進入世界/離開角色 — is architecturally unavailable: party membership is a star
model owned by one PlayerCharacter (`player.db.party` holds NPC dbids only; `join_party`
rejects non-NPC targets with `REASON_NOT_NPC`), and every downstream system (affinity,
friendly-fire, quest credit, auto-leave) is keyed on (NPC, player).

Possession instead changes **control, not ownership**: A temporarily puppets bound companion B.
The star model, affinity records, and the owner-companion quest-credit rule all survive
untouched — B's kills during possession credit A's quest log for free, because that rule was
always "actor is a bound companion of the owner". On handback, B's NPC subjectivity (schedule,
dialogue persona, autonomy) resumes intact. Evennia's puppet machinery and the
multichar-03/05 transition research (silently-refusing `puppet_object`, the verification +
recovery ladder, `retire_sequence`/epoch ordering) are reused wholesale.

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Possession is a party-core-patterned single writer**: `world/rules/possession.py` mirrors `pc.db.possession = {npc_dbid, since_tick}` and `npc.db.possessed_by = pc_dbid` inside one `transaction.atomic()` with snapshot/restore of both in-process surfaces and stable reason codes. | Exactly the proven `party.py` contract (mirrored attributes, atomic commit, idmapper-cache restore helper); no partial binding ever observable. |
| D2 | **Deterministic entry gates, all before any AI/dialogue work**: B is a live bound companion of A; co-located; no active combat session (`is_in_active_session` on either side); B has no open dialogue session; the account holds no other possession. | The combat gate reuses the existing party-adjustment boundary (already presented as 「戰鬥中無法調整隊伍」) and removes combat-AI, friendly-fire-scope, and turn-economy questions from v1 entirely. |
| D3 | **Control transfer rides Evennia-native puppeting** (`account.puppet_object(session, npc)`), with `puppet:id(<account>)` dynamically added to B's locks on entry and removed on handback; the multichar-03/05 transition timing, verify-`get_puppet`-after, and recovery-ladder lessons are reused verbatim. | One transition mechanism, already hardened against `puppet_object`'s silent-refusal branches; a custom "controller pointer" would fork every read path the engine keys on `sessions`/`puppet`. |
| D4 | **A stays in the room**, rendered as entranced/vacant. | The deterministic world keeps a physical position for A, keeps room truth honest, and preserves the narrative hook; possession is a camera move, not a disappearance. |
| D5 | **`is_player_driven(entity)` is the one unified predicate** (`world/rules/player_control.py`): true for puppeted `PlayerCharacter` or any NPC with `db.possessed_by`. It replaces the raw `isinstance(PlayerCharacter)` checks in `world/rules/movement.py::charge_movement`, the `commands/skip.py` safety gate, and the `characters.py` room-entry action-options trigger. | The world clock's "advances only on player action" rule (design D4 of the clock line) must keep holding with a puppeted NPC — the predicate widens *who counts as a player actor*, never when time moves. |
| D6 | **Autonomy silencing while possessed**: `settle_npc_schedules` skips NPCs with `db.possessed_by` (same consumer slot as the R2 traveling-host silence gate); `LLMNPC` dialogue is gated closed against the possessed self; quest-observer companion-credit rules are untouched. | "Possessed = autonomy suspended" is one mechanism with two triggers (party-travel, possession). B still earning A's quest credit is a feature kept by explicit decision, reviewed and ratified in the design walkthrough. |
| D7 | **Trimmed character cmdset mounts on B during possession** (movement, look, actions, out-of-combat act surface) via the same derive pattern `at_cmdset_get` uses, removed on handback. | Reuses the creation-gate cmdset idiom instead of inventing a second mechanism; keeps full character commands from leaking onto an NPC with stale expectations. |
| D8 | **Handback is explicit and every exit path is covered**: command surface (歸位) plus automatic release on (a) affinity auto-leave targeting B — release first, then leave, release-then-commit (the release cannot join the affinity DB transaction atomically because puppet side effects are not transactional; a failed release aborts before any delta is written), (b) session loss / disconnect via `Account.at_post_disconnect` (amended during change authoring: `at_post_unpuppet` fires on EVERY deliberate unpuppet in Evennia 6.1 — including possession's own release of A — so wiring cleanup there would clear fresh mirrors mid-possession; `at_post_disconnect` fires only from `ServerSession.disconnect()`), (c) possession-into-full-party or other gate failures never enter state. | Possession must never survive its preconditions; the auto-leave ordering prevents a released-too-late or left-but-still-puppeted hybrid. |
| D9 | **v1 presentation is honest hybrid**: actor re-points through the established epoch-reset transition; panels keep rendering **A's** wallet/quests/guild (NPCs own none of those fields) under a persistent banner 「你透過 B 的雙眼行動」; B's inventory/equipment render from **B's real attributes** (`toggle_equipment` already works on any `LivingEntity`); PartyDrawer gains `explore.possess` / `explore.possess_release` affordances. | The read-model adapters for NPC-owned panels are the last genuinely new work; deferring them keeps v1 shippable while everything B actually has already displays truthfully. |
| D10 | **v1 refusals, each a fixed message**: shop buy/sell while possessed (A's wallet may not be spent by B's hands — a later change may design purses), combat entry, initiating dialogue as B. | Each refusal is a spec scenario, not debt; the economy/combat surfaces involve PC-keyed state that possession must not silently launder. |

## 3. State Machine

```
unpossessed --enter(gates pass)--> possessing(puppet B, silence B, cmdset B, epoch reset)
possessing  --handback(command)----> unpossessed (unpuppet->re-puppet A, locks, attrs, epoch reset)
possessing  --auto-release---------> unpossessed (D8 triggers; inside the triggering transaction where one exists)
```

Entry order: gates → lock grant → puppet B (verify; recovery ladder) → mirror write → cmdset
mount → silence engages → epoch reset + actor re-point. Handback reverses. A rollback at any
step restores both mirror attributes through the party-core restore helper.

## 4. Data-Flow Notes

- **Clock**: B's movements call `charge_movement` under D5 → the world advances exactly as if A
  walked. B following *other* party members is impossible mid-possession (A is stationary;
  `follow_companions` keys on the moving PlayerCharacter).
- **Party truth unchanged**: A remains owner of B (and of any other companions, who keep
  following A, not B — their follow key is the moving owner, and the owner does not move while
  possessing). Party membership itself is untouched; dismissal of the possessed B from the
  same account is refused with "hand back first", never performed under possession.
- **Presentation**: `session.ndb.elosern_actor_id` re-points to B; snapshot panels are
  actor-keyed as in D9. The unpuppet transition reuses `send_unpuppet_transition`/
  `retire_sequence` sequencing from the localized OOC path.

## 5. Error Handling & Failure Modes

| Case | Behavior |
|---|---|
| `puppet_object` silent refusal mid-enter | Verify-then-recover ladder (multichar §11): attempt explicit re-puppet of A, end at an error-level log + 「你目前未附身任何角色，請使用「進入世界」」 — never a half-state |
| Mirror write fails after puppet | Unpuppet back to A (restore ladder), raise `PossessionWriteError`, gates re-checked fresh on next try |
| B auto-leaves (affinity < 70) while possessed | Release runs and commits BEFORE the affinity/party atomic opens (release-then-commit); notification after commit, per the affinity writer's caller-notify contract; a failed release leaves everything untouched |
| Session drops | `Account.at_post_disconnect` releases possession; B's attributes/schedule resume on the next settlement tick |
| B deleted while possessed | Entry gate requires a live bound companion; the deletion purge unwinds bindings — D8(b) session loss fires alongside and releases the puppet |
| Server reload mid-possession | Persisted mirror attributes + Evennia's session restore resume the possession; nothing possession-specific needs reload handling |

## 6. Testing

- Pure: gate matrix (one named reason per D2 condition), mirror-write atomicity and both-sided
  restore under injected failure.
- Integration (`EvenniaTest`/`EvenniaCommandTest`): entry/handback puppet transitions incl. the
  recovery ladder; clock predicate (possessed-NPC move charges, unpossessed NPC move does not);
  silence (schedule skipped, dialogue gate, cmdset mount/unmount); auto-leave ordering;
  disconnect cleanup; 歸位 command surface.
- Presentation: actor re-point + epoch bump; banner + A-panel hybrid on snapshot; `off_anchor`
  interaction with R2 (possessing a place-bound merchant away from anchor darkens his shop —
  already R2 semantics, asserted once here); refusals emit the fixed messages.
- Player-facing command surface (附身/歸位) updates `docs/game/commands.md` +
  `command-reference.md` with `tests/test_command_docs.py` green; shard manifest updated;
  spec-traceability anchors the new main capability `companion-possession`; no LLM/network.

## 7. Non-Goals

- PC↔PC party membership (rejected route), possession of monsters or unbound NPCs, possession
  in combat, NPC-owned wallet/quest panels, purse/economy transfer while possessed, dialogue as
  B, multi-possession, GM/admin remote-view tooling.

## 8. OpenSpec Change Mapping

Lands as the possession line **6 `companion-possession-rules` → 7
`companion-possession-transition` → 8 `companion-possession-webclient`**, after the profession
line (1–3) and the anchoring line (4–5). Full batch order is serial 1→8; the table lives in the
profession-registries design §9. Amendments from the pre-handoff rubber-duck review are woven
into D5 (release-then-commit wording is in D8) and D8/§5 (`Account.at_post_disconnect` replaces
`at_post_unpuppet` as the disconnect hook); the epoch bump is owned by
`reset_client_sequence` (transition change D-T1).

**Proposal list (this design):**

| # | Change | Delivers |
|---|---|---|
| 6 | `companion-possession-rules` | `possession.py` writer + gates, `is_player_driven` predicate, party release hooks, possess/歸位 commands, autonomy silencing, movement retitling |
| 7 | `companion-possession-transition` | real puppet-transfer ladder, cmdset mount, `Account.at_post_disconnect` wiring, entranced rendering |
| 8 | `companion-possession-webclient` | possess affordances, banner presentation, PartyDrawer integration, JS gates |

**Implementation batch order:** `6 → 7 → 8` strictly serial (7 fills 6's named seams; 8 renders
7's real state). **Cross-line coupling with multichar (MC1–MC5):** 7 has a HARD landing
dependency on MC3 (`multichar-03-character-switch-action`, itself still Proposed — its
"landed" claim was corrected in change 7's D-T1): the transition ladder rides MC3's verified
`_attach_puppet` helper, three-rung recovery ladder, and codified epoch semantics, and both
lines edit `typeclasses/characters.py` around `at_post_unpuppet`. Text-level contention points:
`typeclasses/accounts.py` (MC1 vs 7, different methods), `docs/game/command-reference.md` +
`tests/test_command_docs.py` manifest (MC1 vs 6), Storybook `component-manifest.json`
(MC5 44→45 vs 8 — second arriver rebases). Practical interleaving and the full table:
profession-registries design §9.
