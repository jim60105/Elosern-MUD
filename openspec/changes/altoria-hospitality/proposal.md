## Why

三件套 — 「城鎮公共浴場、酒館、市集」 — is how the world document describes ordinary town life, and the capital has none of the three. The applicability matrix marks 酒館, 旅店 and 公共浴場 all 「有」 for a capital, each with a named host, and the lower city was laid out around them: 客棧巷 is an inn lane with no inn on it and 浴場前 is a bathhouse frontage with no bathhouse.

These are the locations that make a city somewhere a player lives rather than somewhere they shop. The tavern in particular is the document's designated place for 招募同伴 and 打聽情報, and `invite` and `talk` already work — they just have nowhere to happen.

## What Changes

- Add three `attendant` places in the lower city, with their dialogue tables:
  - **聖潔王都醉月酒館** off 客棧巷, hosted by 蘿溫·古橡, 聖潔王都酒館老闆.
  - **聖潔王都爐火旅店** off the same lane, hosted by 溫弗蕾德·古林, 聖潔王都旅店老闆娘.
  - **聖潔王都公共浴場** off 浴場前, hosted by 伊莎貝爾·葦沼, 聖潔王都公共浴場管理員.
- Author each host's dialogue so the location's existing affordances are discoverable in it: the innkeeper explains that `rest`, `sleep` and `practice` work in her rooms, the tavern keeper points at `talk` and `invite`, the bathhouse keeper explains the men's and women's sides.
- Introduce **no new mechanism**. The document marks lodging fees 〔提案〕 at line 308, drinking and gambling effects 〔提案〕 at line 285, and bathhouse mechanics 〔提案〕 at line 352. All three stay unimplemented, and this change pins that they do — 「本文不預先發明數值」 applies to the change that lands the location too.

## Capabilities

### New Capabilities
- `altoria-hospitality`: the capital's tavern, inn and bathhouse as narrative locations that host existing mechanics and add none, and the rule that a location may not invent the systems its own document marks as unproposed.

## Dependencies

This change lands after `place-attendant-profession`, `altoria-capital-replan`, `altoria-place-slices` and `place-kind-vocabulary`.

## Impact

- `world/lore/settlements/places_altoria_lower.py` — three rows, two sharing 客棧巷.
- `world/lore/dialogue/altoria.py` — three dialogue tables.
- `docs/lore/settlement-locations.md` — lines 287, 310 and 354: three placeholder host names.
- No rulebook, no commerce, no runtime code. These places sell nothing.
