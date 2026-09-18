## Context

The divine-mystery registry block currently holds four inert placeholders plus two orphan single nodes.
The lineage validator already supports n-ary prerequisite DAGs with multi-parent canopies (the element
trees ship two-parent capstones), derives each node's cap from the maximum `min_proficiency` of the
edges consuming it, and fails closed at registry load. `EffectPolicy` is index-aligned with `effects`
and supplies both the per-occurrence scale and the audience. See `proposal.md` — Why for motivation, and
`docs/lore/skill-trees/divine-mystery.md` §2 for the authored node table this change transcribes.

## Goals / Non-Goals

**Goals:**

- Land the authored tree exactly as the lore prices it, using only vocabulary the wave has shipped.
- Keep every existing owner of `status_disguise` and `dominion_art` valid without a data migration.
- Replace data-echo test coverage with behavior coverage.

**Non-Goals:**

- Any new engine primitive. If one is missing, it is a defect in the change that owns it.
- The 情慾秘術 divine line, `divine_sexual_arts`, `divine_sexual_mastery` and the seven 神性 acts. They
  keep their category, their gate, their counters and their effects byte-for-byte.
- The four uncatalogued mysteries (time, space, matter, life). They are documented as deliberately
  unsystematized and carry no keys.
- Presentation work. The category already renders as 神之秘法 in the combat view and the status read
  model; the node count changing is not a presentation change.

## Decisions

### D1: The two orphans become roots, not mid-chain nodes

`status_disguise` and `dominion_art` are claimed by three authored preset cards. Authoring them as
roots with no prerequisites means those cards stay valid untouched; authoring them deeper would rely on
the lineage auto-seed to invent proficiency for skills the cards never claimed. Keeping their keys also
avoids aliases.

### D2: The four placeholders retire wholesale, no aliases

A repository-wide scan finds no preset, import example, lore registry or rulebook row naming them; the
only references are the dev-era echo test and the gate test's category-derived fixture. With no released
users, an alias would preserve nothing.

### D3: Scale lives in `EffectPolicy.coefficient`, audience in `EffectAudience.ALLIES`

Both are the shipped vocabulary (`conferral-grant-store` D4 and the wind 神速領域 precedent). The chain
ladders therefore differ only by coefficient and audience, which is exactly how the lore reads them, and
no node needs a bespoke field.

### D4: The capstone declares three parents at the tip cap

`crown_apotheosis` requires the three chain ends at `Lv.10`. The validator's cap derivation then gives
each chain end a cap of 10 automatically, and the elements' two-parent capstones prove the n-ary shape
works. Its own effects are the three chain verbs at their strongest, each as its own occurrence with its
own policy.

### D5: Behavior coverage, not catalog echo

The retired `DivineMysteryRegistryTests` asserts that specific rows exist with specific labels — it
restates the registry rather than establishing a mechanic, and it is exactly the data-echo shape the
project's testing rule discourages. Its replacement asserts properties and compositions: that no node in
the category carries a combat verb or a cost, that a conferral ladder's higher rung yields a larger
effective value on a synthetic target, that an ally-audience conferral reaches every party member, and
that a multi-parent capstone stays unusable until every parent meets its threshold. Those tests compose
synthetic skill definitions and need no shipped-content names and no data-contract tagging.

### D6: The `divine_mystery` effect prefix stays registered

After this change no shipped skill declares it. The recognized-prefix requirement in
`skill-effect-model` explicitly requires retaining every previously recognized prefix, and the lore keeps
an inert-flavor form as a legitimate shape for a future node, so the prefix and its handler stay as they
are rather than being retired here.

## Risks / Trade-offs

- **The gate test's category-derived fixtures silently change meaning** → `test_divine_mystery_gate.py`
  builds its fixture by filtering the registry for the category, so it will now exercise the new nodes.
  That is desirable, but the task list requires reading it and confirming each assertion still describes
  a mechanic rather than a placeholder's inertness.
- **A caster owning many conferrable passives makes the capstone very strong** → `crown_apotheosis`
  confers at 0.50 to an ally audience, and `conferral-grant-store` D3 makes a cast lend EVERY
  conferrable passive the caster directly owns, so the capstone hands a whole party everything its
  caster is. The lore was amended to say so explicitly (§2 and §6) rather than leaving the node table
  reading "一項": in practice the largest owned multiplier dominates the result and the lesser
  rule-table passives contribute single digits, and the whole thing is bounded by the caster's own
  achievements, the 80–90 game-day cadence cost, and the revocation counter-play. If playtesting says
  otherwise, the dial to turn is the capstone's coefficient, in data, in this change.
- **Retiring an echo suite reduces raw coverage numbers** → accepted; the aggregate branch-coverage gate
  is a floor, not a target, and the replacement tests establish mechanics the echo suite never did.
