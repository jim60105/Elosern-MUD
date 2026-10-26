# Authored scene schema

Reference for `world/lore/dialogue/content/<NpcProfile.key>.yaml`. The parser is
`world/lore/dialogue/codec.py`; the loader is `world/lore/dialogue/loader.py`; the
runtime contract is the `authored-*` specs under `openspec/specs/`. Behaviour
(selection, refusal, reading, notifications) is documented in
`docs/development/adding-npcs.md` Step 3 — do not restate it here.

## Root

| Key | Type | Rule |
|---|---|---|
| `schema_version` | integer | exactly `1` (not `1.0`, not `true`) |
| `greeting` | string or null | static cap 2000 code points and 8192 UTF-8 bytes |
| `topics` | list | 0..16 topics |

Forbidden root keys: `npc_id`, `profile_key`, `owner`, `dialogue_key`. Ownership
comes from the filename (host profile key) plus the place row (`dialogue_key`).
Unknown keys anywhere are rejected, so no comment or note fields.

## Topic

| Key | Required | Rule |
|---|---|---|
| `topic_id` | yes | `<dialogue_key>.<suffix>`, suffix `[a-z][a-z0-9_]{0,31}`, whole ID ≤96 chars |
| `keyword` | yes | 1..32 code points; what a text client can type |
| `label` | yes | 1..32 code points; the menu entry |
| `fallback` | yes | scene; the unconditional body |
| `variants` | no | 0..8; unique `variant_id` and unique `priority` |
| `requires` | no | one condition; makes availability conditional |
| `unavailable` | no | `hidden` (default) or `locked` |
| `refusal` | no | scene; required when `unavailable: locked` |
| `predecessors` | no | 0..16 stable topic IDs from the same file, acyclic |
| `disclosure` | no | `qualified` (default) or `pure_chain` |

`pure_chain` requires at least one predecessor, forbids `requires`, and forbids
any ancestor with `requires`.

## Scene and line

| Key | Required | Rule |
|---|---|---|
| `scene_id` | yes | `[a-z][a-z0-9_.-]{0,95}`, unique across the whole file (fallbacks, variants, refusals) |
| `revision` | yes | printable ASCII, 1..32 chars; bump when the lines of an already-shipped scene change (`r1` → `r2`), and keep the current value while polishing inside the same unmerged change |
| `lines` | yes | 1..32 lines |

Each line is exactly one of:

```yaml
- kind: speech
  speaker: actor      # acting body: player character or possessed companion
  text: 「我想問問這件斗篷。」
- kind: speech
  speaker: host       # the NPC being talked to
  text: 「羊毛料子，山裡擋風夠用。」
- kind: narration
  text: 她把斗篷抖開，就著窗光看縫線。
```

`fallback` and every `variant.scene` must begin with an `actor` speech line.
A `refusal` scene may begin with the host.

## Variant

```yaml
variants:
- variant_id: guild_member
  priority: 20
  when:
    kind: all
    children:
    - kind: guild_rank_at_least
      rank_key: D
    - kind: carries
      item_key: adventurer_field_ration
  scene:
    scene_id: guild_staff.topic_03_veteran
    revision: r1
    lines: [...]
```

Selection: the highest matching `priority` wins; no match uses `fallback`.
`when` is required, `priority` is required, duplicate priorities are rejected.

Give a combined condition (`all` of rank plus carried item, elf *and* exposure)
`20` and a single trait `10`; when two variants can both match, the more specific
context must carry the higher number, otherwise the general scene shadows it.
Every topic keeps an unconditional `fallback` as the base scene.

## Conditions

`all` / `any` take 1..16 `children` (nesting depth ≤4). Every leaf operand must
exist in the canonical permitted catalog
(`world/rules/dialogue_references.py::static_dialogue_references()`); one unknown
key rejects the whole snapshot.

| `kind` | Operands | Semantics |
|---|---|---|
| `all` | `children` | conjunction |
| `any` | `children` | disjunction |
| `race_is` | `race_key` | acting body's race (`human`, `beastfolk`, `elf`) |
| `social_identity_is` | `identity_key` | acting body's membership tag (`noble`, `clergy`, `official`, `adventurer`) |
| `guild_rank_at_least` | `rank_key` | owning player's guild rank (`F`..`A`) |
| `quest_is` | `definition_key`, `state` | owning player's quest state: `not_accepted`, `in_progress`, `completed`, `reward_claimed`, `failed`, `invalidated` |
| `affinity_at_least` | `stage_key` | host-to-owner affinity stage (`acquaintance`..`absolute_bond`) |
| `carries` | `item_key`, `minimum` (default 1) | acting body carries at least N; inspection never consumes |
| `companion_present` | `source_kind` (`preset`/`profile`/`package_role`), `source_key` | that companion is bound to the owner and physically present |
| `time_period` | `start_daypart`, `end_daypart` | in-world daypart interval `[start, end)`, endpoints differ (`midnight`, `dawn`, `noon`, `dusk`) |
| `skill_owned` | `skill_key`, `min_proficiency` (optional) | acting body owns the skill, optionally at the threshold |
| `exposure` | `minimum`, `maximum` (at least one, inclusive, integers 0..4) | acting body's effective exposure; worn gear counts |

Ordinal `0..4` maps to `EXPOSURE_LEVELS` = 極低／低／中等／高／極高
(`world/lore/sexual_vocab.py`); the condition never takes the label itself.
Operand sources for the canonical keys:

| Operand | Registry |
|---|---|
| `race_key` | `world/lore/races.py::RACE_REGISTRY` (`human`, `beastfolk`, `elf`) |
| `identity_key` | `world/lore/social_identities.py::SOCIAL_IDENTITY_REGISTRY` (`noble`, `clergy`, `official`, `adventurer`) |
| `rank_key` | guild ranks `F`..`A` (`world/lore/guild.py`) |
| `skill_key` | `world/skills/` `SKILL_REGISTRY` |
| `item_key` | item registry; the same key must appear in the host's assortment before the prose promises it |
| `stage_key` | affinity stages (`world/rules/affinity*`) |
| companion `source_key` | `PLAYER_PRESET_REGISTRY` for `preset`, a profile key for `profile` |
| `definition_key`, `state` | quest definition registry and the states listed above |

An unknown operand rejects the whole snapshot at startup, so a typo is a load
failure rather than a silently dead variant.

Actor-versus-owner is not a stylistic choice: race, social identity, carried
items, skills and exposure read the acting body; guild rank, quest state,
affinity and reading progress read the owning player. A possessed elf companion
qualifies on her race while the owner's guild rank still governs guild topics.
Hints are generated from these declarations with canonical public labels, so the
prose never has to explain a requirement.

## What the schema cannot check

The parser validates shape, references and budgets. It cannot see that a line
invented a place, a price, a title or a commission type, and it cannot judge
whether a scene reads like a conversation. Those are the review pass's job:
resolve every proper noun to a registry row, then read the file as speech.

## Limits

| Scope | Limit |
|---|---|
| file | 256 KiB, UTF-8, regular file (no symlink), single document |
| line text | 2000 code points |
| scene | 32 lines, 16000 code points, 8192 canonical UTF-8 JSON bytes |
| topic | 8 variants, 16 predecessors |
| dialogue file | 16 topics, 24576 canonical bytes for the whole panel |
| delivery | 16384 bytes for the selected scene plus every reachable pure-chain successor |

Exceeding any of these is a `DialogueSourceError`; the whole snapshot is
rejected, so one oversized scene blocks startup.

## YAML safety

Strict safe loading: no anchors, aliases, merge keys, duplicate mapping keys,
custom tags, multi-document streams, or non-JSON primitive types. Write literal
UTF-8 Chinese text; do not escape it.

## Worked example

The example illustrates shape and technique. Its names, stock and prices belong
to that host only; never copy them into another scene.

```yaml
schema_version: 1
greeting: 櫃檯後的裁縫抬起頭，把捲尺往脖子上一掛：「要改衣服，還是挑布？」
topics:
- topic_id: body_measure.tailor_wares
  keyword: 布料
  label: 布料
  fallback:
    scene_id: body_measure.tailor_wares_scene
    revision: r1
    lines:
    - kind: speech
      speaker: actor
      text: 「店裡有哪些布？」
    - kind: speech
      speaker: host
      text: 「架上那幾匹都在。山羊毛的厚，城裡人冬天穿；細麻的薄，夏天透氣。」
    - kind: narration
      text: 她伸手把一匹灰藍色的布往你面前推了推。
    - kind: speech
      speaker: host
      text: 「這匹染得勻，做外袍不刺眼。摸一摸，喜歡再談價。」
  variants:
  - variant_id: noble_customer
    priority: 20
    when:
      kind: social_identity_is
      identity_key: noble
    scene:
      scene_id: body_measure.tailor_wares_noble
      revision: r1
      lines:
      - kind: speech
        speaker: actor
        text: 「店裡有哪些布？」
      - kind: speech
        speaker: host
        text: 「裡間還有幾匹沒擺上架。絲的光澤勝過外面這些，你若要見，我去取。」
      - kind: speech
        speaker: host
        text: 「城裡幾位大人也都用這家的料子。價錢照舊，只是得等兩日。」
- topic_id: body_measure.tailor_past
  keyword: 往事
  label: 往事
  requires:
    kind: affinity_at_least
    stage_key: trusted
  unavailable: locked
  refusal:
    scene_id: body_measure.tailor_past_refusal
    revision: r1
    lines:
    - kind: speech
      speaker: host
      text: 「那種事我向來不跟人說。你換個話題，我都答。」
  fallback:
    scene_id: body_measure.tailor_past_scene
    revision: r1
    lines:
    - kind: speech
      speaker: actor
      text: 「你在這裡做多久了？」
    - kind: speech
      speaker: host
      text: 「從我母親那時候就在了。這條街換過三次招牌，裁縫桌沒換過。」
    - kind: speech
      speaker: host
      text: 「這把剪刀跟了我母親大半輩子。我留著，換一把就得重新學手感。」
```
