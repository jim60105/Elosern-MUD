## Why

The owner capped this sub-project at eight hours (one engineer-day) per
OpenSpec change; the superseded `implement-church-core` is re-cut into five
changes (foundation + four layers), and this is its **enrollment layer**:
`church join` becomes the player's first
visible contact with the church — the deterministic three-stage rite, the
subrace/sex-gated Saintess office branch, and the unconditional vestment
handover — plus the `violet_altoria` preset surgery and the lore/spec
amendments the owner's amendments mandate. The substrate (ledger, rulebook
gates, `ChurchHost`, `church` venues) lands first in
`implement-church-foundation`. Authoritative design:
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.1/§7/§9.

## What Changes

- `commands/church.py::church join` (aliases 入教／洗禮): resolve a local
  `ChurchHost` (`resolve_local_service_host` pattern) → schedule gate
  (`interaction_reason(host, "service_church")`) → deterministic
  `world/rules/church.py::enroll(caller, host)` — ledger create,
  `church_enrolled` on_commit, re-enrollment rejection 「你已屬光明教會」,
  rollback byte-identical. Zero AI import; the flow passes with the dialogue
  model stubbed to raise.
- **Subrace/sex office branch** inside the same transaction: a female
  `human_royal` enroller is granted `saintess_vessel` through the canonical
  granted-passive write path, reusing the existing
  `saintess_vessel_granted` event exactly once. No office uniqueness — every
  eligible royal becomes a saintess. Trickle stays disarmed pre-enrollment.
- **Unconditional vestment handover** via the deterministic `QuestReward`
  item-quantity rail (the LLM `give_item` intent is NOT the channel):
  `sister_vestments` (ordinary) or `saintess_vestments` (vessel branch) —
  exactly one vestment per enrollment, no holding check, transactional with
  the ledger write.
- **BREAKING (preset data):** `violet_altoria` drops `saintess_vessel` from
  `passive_skills` and `saintess_vestments` from `starting_items`; the
  persona's religious narrative (聖女/聖女繼承人 wording, temple-blessing
  passages, consecration sentences) is DELETED, not rewritten into a successor
  framing — pre-enrollment she is simply 王女. Preset data-contract tests
  follow; a repo-wide authored-content search proves the retired framing is
  gone (successor reframings count as failures).
- Lore realignment: `docs/lore/overview.md` 宗教信仰 once-per-generation 聖女
  framing retired; `docs/lore/skill-trees/light.md` 聖女 footnote → enrollment
  grant; `docs/lore/settlement-locations.md` 神殿／聖所 〔提案〕→〔已實作〕 tags.
- Docs trio for the `church join` surface (+ 入教／洗禮 aliases) in
  `docs/game/commands.md` + `docs/game/command-reference.md`,
  `tests/test_command_docs.py` green.
- **§9 saintess-vessel delta:** the two preset-grant-era requirements are
  REMOVED and replaced (validator forbids MODIFIED-block scenario replacement
  and same-name ADDED+REMOVED): the enrollment grant path replaces the preset
  grant; the title-invariant requirement is amended to sanction exactly one
  predicate-family extension — the church redeemed-count family (shipped by
  `implement-church-order-catalogue`) — while reaffirming the global 聖女
  office-name title ban. Vessel tests re-annotated with the replacement IDs.

## Capabilities

### New Capabilities
None — the `church-ordination` capability is opened by
`implement-church-foundation`; this change's delta purely ADDS its four
enrollment requirements onto it.

### Modified Capabilities
- `saintess-vessel`: the preset-activation grant path is REPLACED by the
  church-enrollment grant path (design §9.1), and the title-invariant
  requirement is amended to sanction exactly one predicate-family extension —
  the church redeemed-count family — while reaffirming the no-title-state
  decision and the 聖女 office-name ban (design §9.2). This delta travels with
  this change only.

## Dependencies

depends-on: implement-church-foundation

Needs the `db.church` ledger + single-writer primitives, the `ChurchHost`
component on the two clergy roster rows, the derived `church` venue set, and
the `church.yaml` pray/accrual rows the ledger gates against. Consumes
verbatim: `guild-registration`'s three-stage host pattern, the
`QuestReward` item-quantity rail, the granted-passive write path
(`lineage_ownership_closure` shape), `place-driven-service-sync`.

Size: ≤ 8 tasks / one engineer-day.

## Impact

- New: `commands/church.py` (`church join` only — pray/offer arrive with
  `implement-church-accrual`, redeem/merit with `implement-church-redemption`);
  enrollment section of `world/rules/church.py`.
- Edited: `world/lore/player_presets/data_pack_cards.py` (`violet_altoria`),
  preset data-contract tests, vessel test annotations (new delta IDs),
  `docs/lore/overview.md`, `docs/lore/skill-trees/light.md`,
  `docs/lore/settlement-locations.md`, the docs trio,
  `.github/evennia-shards.json`.
- No quest channel, no affinity gate, no LLM participation (offline
  determinism); no backward-compat shims (unreleased project).

## Batch:

depends-on: implement-church-foundation

Code-conflict notes: owns `commands/church.py` (created here; accrual and
redemption changes append subcommands after it lands) and the saintess-vessel
main-spec text at archive. Touches no catalogue file —
`REDEEM_CATALOG`/`OFFERING_CATALOG`/`church.yaml` price edits belong to the
redemption change. Queued behind foundation; accrual and redemption queue
behind this change (they require enrollment to exist for their ledger-gated
flows); order-catalogue's §9.2 predicate sanction is the saintess-vessel delta
landing here.
