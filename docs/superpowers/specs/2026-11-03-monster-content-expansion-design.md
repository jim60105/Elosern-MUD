# Monster Content Expansion: Weak Species and High-Tier Bosses

**Date:** 2026-11-03  
**Status:** Seven design sections approved in conversation; written-spec review required before implementation planning.  
**Scope:** The third of three approved monster-world redesigns. This document approves content and delivery contracts, not feature implementation.

## 1. Relationship to the population redesign

[Regional Monster Population and Encounter Configuration](2026-11-03-regional-monster-population-design.md) defines sparse authored habitats, individual density, delayed recovery, manual placement, actual-entity observation, stable identity, and whole-cell combat. [Monster Field Behaviour, Aggression, and Escape](2026-11-03-monster-field-behaviour-and-escape-design.md) defines activity areas, cohesive movement, global game-time journeys, aggression, paid escape, reserve failure, and re-engagement.

This document adds the approved content for three weak prototypes and two powerful manual bosses. The selected approach combines one new high-tier species with one high-tier variant of an existing species. The resulting batch adds four species and five variants. Completion of a species definition grants only its explicit placement permissions, never world-wide automatic coverage.

The governing creative source remains [Monster Creation Guidelines](../../lore/monster-creation-guidelines.md). The first bestiary batch's low/mid approval remains historical; this separately approved batch adds the two specified high-tier entries. Calamity-tier creatures and new civilized peoples remain outside this batch.

## 2. Affirmative monster prose

The user requires affirmative descriptions for every newly written or rewritten monster passage. Public prose states observable appearance, behaviour, ability scope, material requirements, and costs directly. A reader learns the creature through what it does.

Keep technical exclusions and implementation constraints in author-facing sections. Public descriptions must not become lists of rejected powers or comparisons with abilities the creature lacks. The approved Traditional Chinese passages below provide the canonical content baseline, while later editorial rewording remains free within their approved meaning.

Use the same principle when updating the crocodile's current bestiary section and when adding the editorial rule to the creation guidelines during implementation. Existing unrelated species sections are outside this rewrite. Structural tests prove identities and relationships; manual editorial review establishes affirmative phrasing and semantic fidelity. Do not pin sentences or police prose through production-content string assertions.

World mysteries remain open. Private author fields record the preserved origin boundary and each species' ecological rationale. Publish only observer-accessible facts; species descriptions, portraits, and quest text do not acquire author-private origins or unapproved conjectures.

## 3. Identity and authoring scope

| Species identity | Public name | New variant | Variant label | Tier and individual grade | Classification |
| --- | --- | --- | --- | --- | --- |
| `mudfilm_slime` | 泥膜史萊姆 | `mudbank_dweller` | 濕岸型 | Low, F | Ordinary species baseline |
| `sticky_palm_goblin` | 膠掌小鬼 | `hanging_nest_forager` | 懸巢型 | Low, F | Ordinary species baseline |
| `wax_pouch_rat` | 蠟囊鼠 | `wax_cache_forager` | 藏穀型 | Low, F | Ordinary species baseline |
| Existing `tide_devouring_crocodile` | 吞潮鱷 | `reservoir_warden` | 蓄潮型 | High, A | Stronger variant of the existing species |
| `ember_bristle_boar` | 焙鬃野豬 | `warm_den_boar` | 焙窩型 | High, B | Ordinary baseline of a rare high-tier species |

Each new species uses its listed ordinary variant as its default. The crocodile retains its existing default and ordinary variants. `reservoir_warden` is a complete standalone record, not an override chain or an in-place buff of `bay_warden`.

The generic tier-example labels and art-only keys `slime`, `goblin`, and `giant_rat` do not become aliases for these identities. Existing art-only declarations remain a separate authoring representation; no art record grants combat eligibility. Construction and placement use canonical species/variant references through the existing deterministic owner.

Individual nicknames are display facts, separate from species, variant, quest, site, and reward identity. The crocodile's designated specimen is called 「閉灣者」, and the boar's is called 「赤背」. Both names describe local observation and do not imply a new personal-naming tradition.

## 4. Approved species and variant dossiers

### 4.1 泥膜史萊姆

**Public description**

> 泥膜史萊姆棲息於潮濕溝岸、舊灌溉支渠與滲水洞口，以水膜中的腐葉碎屑及微小生物為食。透明膠體外膜黏集細泥，收縮時將泥粒壓成薄韌護膜；移動時，泥紋沿著體表摺疊。

**Public appearance**

> 半透明膠體貼著濕地起伏，外膜浮著細緻泥紋。收膜時，泥粒聚成較深的環帶，撞擊留下的缺口隨著身體舒展露出濕亮膠質。

**Public ecology and local relationship**

> 牠通常獨自行動，濕潤處可見數隻分散覓食。靠近的腳步會使牠縮向陰濕處；遭到逼近時，牠收緊泥膜護住身體，再以短距離撞擊自衛。聚集的個體將細泥帶到狹窄分水口，農人會疏通渠口並處理反覆停留的個體。牠的活動集中於保有水膜的陰濕地帶，護膜則由體表已附著的細泥形成。

| Authoring face | Approved content |
| --- | --- |
| Familiar prototype | Small gelatinous slime with a recognizable flowing silhouette. |
| Distinct ecology | Attached silt becomes a folding protective film; movement can concentrate mud at narrow channels. |
| Habitat compatibility | `eastern_plains`, `western_hills_valleys`, limited to explicitly authored damp cells. |
| Social policy | A birth occurrence contains one to three individuals, each with its own movement unit. |
| Aggression | Passive contact policy; ordinary self-defence after engagement. |
| Combat role | Slow, low-tier defensive individual; personal film guard and innate contact attack. |

### 4.2 膠掌小鬼

**Public description**

> 膠掌小鬼是耳大、四肢細長、掌面寬的小鬼型魔獸，活動於丘陵灌木、廢棄採石地與岩棚下。掌部的短效黏液將枯枝、碎石及獸毛黏成懸掛巢，也協助牠攀附粗糙表面。

**Public appearance**

> 瘦長身軀覆著淡綠色粗皮，寬掌與細長手指在攀爬時張開。指尖帶著黏亮痕跡，身旁的懸巢掛著細枝、繩絮與零碎石片。

**Public ecology and local relationship**

> 小群個體共同覓食、搬運巢材，以短促啼叫與敲擊傳遞警戒。牠們熟練運用手邊物件，能合作驅趕靠近巢穴的動物。人類工地留下的繩束、木片及保溫材料容易被搬進巢中；巢群占據通風口或岩棚通道時，工人會請人處理。黏液適合附著輕小巢材，雨水使膠膜逐漸稀薄。近身抓扯讓對手短暫失去動作節奏，覓食個體則傾向沿岩面退避。

| Authoring face | Approved content |
| --- | --- |
| Familiar prototype | Animal-level goblin-shaped creature with grasping hands and opportunistic social learning. |
| Distinct ecology | Temporary palm adhesive supports hanging nests, climbing, and cooperative collection of light materials. |
| Habitat compatibility | `western_hills_valleys`; sparse remote scrub and disused quarry habitat. |
| Social policy | Two to four individuals form one cohesive activity group. |
| Aggression | Defended-nest contact policy, with retreat-oriented ordinary foraging. |
| Combat role | Low-tier physical grab with a brief landed-hit agility penalty. |

The approved taxonomy is an ordinary monster species. Its communication is animal signalling and learned object use. Language, writing, trade, and civilized settlements are outside the approved actor model; introducing those would require a separately reviewed people/culture design. Keep its registry and depiction distinct from beastfolk.

### 4.3 蠟囊鼠

**Public description**

> 蠟囊鼠是約家貓大小的鼠類，活動於平原田界、荒廢糧站與丘陵運糧道旁。牠的頰囊分泌薄蠟，把收集的穀粒裹成小團，藏在潮濕巢穴中。

**Public appearance**

> 灰褐毛皮貼著圓身，鼓起的頰側帶著細亮蠟痕。腹側毛略顯光滑，長尾在鑽縫時貼向身後；巢邊常留著帶齒痕的蠟封穀團。

**Public ecology and local relationship**

> 小型家族共同覓食與搬運穀粒，蠟膜替巢中的穀團提供短期防潮。牠們也把少量蠟抹在腹側毛上，沿濕窄縫隙滑行。遇人時多半退避，藏糧巢口遭到封堵時便聚集自衛。待運穀物、破損糧袋與廢棄倉底提供覓食和築巢機會；妥善封存糧食、清理舊巢，能減少反覆接觸。近身時，牠靠咬擊與靈巧翻身應對威脅。

| Authoring face | Approved content |
| --- | --- |
| Familiar prototype | Large rat with cheek-pouch food storage. |
| Distinct ecology | Short-lived wax wrapping protects collected grain from dampness; a light belly coating supports narrow-gap movement. |
| Habitat compatibility | `eastern_plains`, `western_hills_valleys`; specific remote field margins and abandoned transport facilities. |
| Social policy | Two to five individuals form a cohesive family foraging unit. Explicit manual strays are supported. |
| Aggression | Defended-cache contact policy, with retreat-oriented ordinary foraging. |
| Combat role | Low-tier fast individual with an active, short self-agility improvement and innate bite. |

### 4.4 吞潮鱷・蓄潮型

The parent species remains `tide_devouring_crocodile`, including its approved close-contact MP-transfer ecology. Add the following public variant content to that species' current section.

**Public variant description**

> 蓄潮型長期占據偏遠潮汐支流的深灣，利用退潮後留下的窄水道伏擊。頸側與背脊的發達皺褶維持著薄水膜，咬合接觸活物時吸取部分魔力，再將自身魔力投入短暫護膜。

**Public variant appearance**

> 寬厚背脊沿著水面低伏，頸側皺褶映著濕亮水光。收緊護膜時，薄水膜貼合鱗甲，咬合與轉身使背上的水紋聚散。

**Public ecology and local relationship**

> 牠會在吸取魔力與護住身體之間取捨，反覆使用深灣、窄汊與遮蔽泊岸處。薄水膜集中緩衝近身衝擊，維持護膜消耗牠自己的魔力；普通咬擊則依靠咬合力量。占灣個體迫使小船改走外側航線，渡運者從固定水道與護膜習性辨認牠。指定個體被當地人稱為「閉灣者」。

| Authoring face | Approved content |
| --- | --- |
| Parent and variant | Existing crocodile species, stronger standalone `reservoir_warden` variant. |
| Distinct ecology | Sustained occupation of a tidal backwater with alternating contact drain and a resource-limited defensive film. |
| Habitat compatibility | Existing `southeast_coast` parent habitat, restricted to an explicitly authored remote backwater site. |
| Social policy | One independently persistent territorial individual. |
| Aggression | Immediate hostile contact inside the authored defended bay area. |
| Combat role | High-tier A individual; existing contact MP drain plus an active personal defense buff funded by its own MP. |

### 4.5 焙鬃野豬

**Public description**

> 焙鬃野豬生活於西部偏遠岩林與廢棄燒炭地，會用肩背鬃毛的局部熱力烘乾泥窩、烘軟挖出的根莖。粗鬃末端在發熱時透出暗紅色，巢地留下乾燥土圈與烘焦根皮。

**Public appearance**

> 厚實肩背披著粗硬鬃毛，短獠牙從寬吻兩側向外彎出。發熱時，鬃尖透出暗紅光；轉身時，乾燥根皮與土屑沿著背側抖落。

**Public ecology and local relationship**

> 牠通常獨居，長期使用少數泥窩與覓食路線，從根莖與林地食物取得日常養分。舊炭窯與背風岩坡提供乾燥住處，重複使用的運料道也可能成為領域的一部分。工人遇上占路個體時會改道，再委託熟練隊伍處理。牠以自身魔力維持鬃熱，配合身體力量作短程衝撞與近身甩鬃；熱力與動作都受自身資源支配。首隻指定個體因醒目的背鬃被稱為「赤背」。

| Authoring face | Approved content |
| --- | --- |
| Familiar prototype | Solitary wild boar with localized heat-bearing bristles. |
| Distinct ecology | Warmed wallows and softened roots connect its fire affinity to shelter and feeding. |
| Habitat compatibility | `western_hills_valleys`; explicit remote rocky woodland and abandoned charcoal-worksite placement. |
| Social policy | One individual per manual boss site in this batch. |
| Aggression | Immediate hostile contact inside the authored defended den/path area. |
| Combat role | High-tier B ordinary baseline; physical-power-based fire contact attacks using MP and SP. |

## 5. Executable kits and capability scope

The entries below define executable behavior. Ecology observations such as nesting, mud accumulation, food wrapping, and warmed dens are authored world relationships; they do not silently enable terrain mutation, crafting, weather systems, or inventory transfer.

| Owner variant | Skill identity and label | Target and committed effect | Resource authority |
| --- | --- | --- | --- |
| `mudbank_dweller` | `mudfilm_guard`, 泥膜收束 | Self; short defense improvement, independent of a hit. Innate ordinary attack remains a contact impact. | Positive authored SP cost. |
| `hanging_nest_forager` | `sticky_palm_grab`, 黏掌抓扯 | One enemy; ordinary elementless physical strike, with a brief negative agility modifier only on a landed hit. | Positive authored SP cost. |
| `wax_cache_forager` | `wax_pouch_slip`, 滑蠟翻身 | Self; short positive agility modifier, independent of a hit. This action changes combat modifiers rather than location. | Positive authored SP cost. |
| `reservoir_warden` | Existing `tide_devouring_bite`, 吞潮咬擊 | Existing near-contact damage and actual-loss MP transfer, with its current targeting, payment, and transfer rules. | Existing skill declaration. |
| `reservoir_warden` | `reservoir_guard`, 蓄潮護膜 | Self; short defense improvement independent of a hit. | Positive authored MP cost paid from the actor's current pool. |
| `warm_den_boar` | `ember_tusk_charge`, 熱鬃衝撞 | One enemy; a physical-school, fire-element strike. | Positive authored MP and SP costs. |
| `warm_den_boar` | `ember_bristle_sweep`, 熱鬃橫掃 | All eligible enemies; physical-school, fire-element strikes with ordinary per-recipient hit and defense resolution. | One authored MP/SP payment per cast. |

Keep damage school separate from element. Boar fire attacks use `atk_phys` under the existing physical-school contract and the normal elemental rules. Retain the current monster tier's `magic_power` band; authoring a fire element does not justify raising that independent stat.

Every temporary modifier uses the existing buff lifetime and refresh rules. A repeated cast refreshes its declared effect rather than accumulating an unbounded same-source stack. The goblin's penalty preserves normal movement and flee availability. Slime and crocodile guard affect their caster, while the rat's agility improvement affects the rat. These self effects have no target-hit prerequisite.

Executable capabilities stop at the specified effects. The batch adds no immobilization, equipment dissolution or theft, disease, poison, terrain fire, permanent food preservation, world-tide manipulation, long-range drain, passive full healing, encounter lock-in, or universal fire immunity. Do not derive those mechanics from names, body materials, or an element tag. These are author-facing constraints, not boilerplate paragraphs for the bestiary.

Register and select owned skills through the existing shared engine. Choose existing combat-AI archetypes appropriate to a retreat-oriented weak animal, territorial defensive crocodile, or aggressive boar. Add explicit validated bindings for each new variant. Resource availability and context eligibility decide whether a skill is selectable; ordinary attack and legal innate flee remain available under their existing rules.

## 6. Complete profiles and balance authority

Every new variant declares `profile_required=True`, a complete `MonsterCombatProfile`, its approved danger grade, owned kit, and combat behavior binding. All seven profile values (`hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, `magic_power`) are literal authored values in the registry. Stored base traits remain unmultiplied.

The new profiles use existing low/high tier bounds. Weak baselines carry grade F, the stronger crocodile carries A, and the ordinary high-tier boar carries B. A species' ordinary/stronger classification is independent of its absolute tier. The crocodile's existing low/mid data and the other existing species are not globally strengthened.

This approval fixes roles, grades, kit semantics, social counts, and placement scope. Exact magnitudes, pool sizes, costs, and effect durations are maintained once in their executable declarations during implementation. No second design/bestiary approval-value table or per-species expected-value fixture is introduced. Author the full set before admitting any new variant to construction or placement; a missing field or unusable claimed kit is not a completed content delivery.

Use current construction, resource consumption, effect scaling, AI selection, and human-party calibration boundaries to observe the authored encounter. Check the claimed roles through real consumer behavior, not by reading a tier label. Balance edits may refine the single-source declaration while preserving the approved concept; changing grade, capability scope, social behavior, or placement permission requires an explicit design revision.

## 7. Placement and lifecycle

### 7.1 Sparse weak populations

Each weak species receives only bounded authored ecology placement appropriate to its habitat and a separately bound field-activity configuration. Use the first specification's density interval, automatic birth exclusions, delayed waves, and home-owned ceiling. Counts in this document describe one birth composition, not a population density or a promise to occupy every cell.

| Species | Birth composition | Movement | Contact policy |
| --- | --- | --- | --- |
| 泥膜史萊姆 | One to three | Independent solitary units after birth | Passive |
| 膠掌小鬼 | Two to four | Cohesive group in a bounded quarry/scrub activity area | Hostile in defended nest area; otherwise retreat-oriented |
| 蠟囊鼠 | Two to five | Cohesive family in a bounded margin/cache activity area | Hostile in defended cache area; otherwise retreat-oriented |

Habitat compatibility does not identify a wet bank, quarry, or granary by itself. Placement authors must choose real bounded sites whose published geography and scenario context support the dossier. Working canals, granaries, and settlement-adjacent conflicts use explicit manual or quest placement under the approved exceptions. Do not turn them into a new permanent capital hunting band.

### 7.2 Mixed manual encounter

Add `abandoned_transfer_station_encounter` as a manual encounter in an authored disused transport facility within `western_hills_valleys`. Its exact composition is two `hanging_nest_forager` individuals and one `wax_cache_forager` individual.

The goblins gather nest materials while the lone rat gathers grain from the same abandoned facility. This is co-location of independent animals. Keep the goblin pair cohesive and the rat independent. The explicit rat stray is a manual composition, distinct from the ordinary family birth range. Whole-cell engagement admits all three while effects retain their declared recipients.

Use a one-shot authored encounter for this initial composition. Future repeatable content must declare its lifecycle independently; quest acceptance or map observation never restores it.

### 7.3 Two high-tier manual bosses

Add distinct manual sites `reservoir_crocodile_boss_site` and `ember_bristle_boss_site`, with one `reservoir_warden` and one `warm_den_boar` respectively. The former belongs to a remote southeast tidal backwater; the latter to remote western rocky woodland or an abandoned charcoal worksite. Choose validated geography-backed positions and defended/activity bounds away from maintained settlements. Existing unrelated sites remain under their existing declarations.

Both sites are one-shot. Defeating the designated individual leaves the site cleared; a site owner does not recreate it because its original cell becomes empty. Movement, detachment, or escape preserves the living target identity and ownership. Its current resources survive re-entry and reload. The high-tier variants do not enter ordinary regional composition pools in this batch.

Boss field activity is bounded territorial activity, using the second specification's physical journeys and immediate contact admission. Either side can flee through a legal affordable route and may later fight again. No player-progress scaling, minimum-health lock, phase resurrection, forced completion, or exit-time resource reset is approved.

The batch does not add legendary equipment, automatic rare-material harvesting, new currencies, or a separate boss-reward system. Any authored commission uses the existing structured objectives, payment, and defeat-credit owners.

## 8. Codex, appearance, and editorial publication

During implementation, add the four current species sections and the crocodile's new variant to `docs/lore/bestiary.md`. Keep each bounded `bestiary` identity index truthful about its parent, default, complete variant ownership, public fields, and actual kit delivery state. Historical appendices remain behind the current-content boundary marker.

Add one dated editorial ledger entry for each new shipped species and update the crocodile's entry in `docs/development/bestiary-editorial-review.md`. Review ecology, ability scope, current/historical separation, and the user's affirmative-prose instruction. The ledger records a real read; its structural coverage check is not a semantic quality test.

Update `docs/lore/monster-creation-guidelines.md` with the affirmative-public-prose rule and this batch's separate high-tier approval scope. Preserve the earlier batch's historical approval. Keep any changed current implementation-status claims aligned with actual declared kits rather than copying older narrative-only appendices over the current registry.

New species use the existing pure species-to-visual adapter and canonical public appearance fields. The crocodile retains its species identity while its variant and individual description carry the approved distinguishing details. Never promote generic art-only examples to gameplay or pass author-private truth into image requests. Image delivery is a separate asset fact; a complete deterministic textual encounter remains usable with image and LLM services offline.

Public monster passages use Traditional Chinese. Technical comments, implementation documentation, and commit messages follow the repository's English conventions. Public lore describes bodies and observed behavior rather than command keys, UI elements, buff identifiers, or resource-field names.

## 9. Validation and failure handling

Validate keys, parent/default relationships, full profiles, tier/grade bounds, owned skill references, AI bindings, habitat compatibility, composition counts, and site lifecycle before publishing the registry. Reject a visual-only key used as a combat variant and an unregistered capability used to justify placement.

Use frozen authoring records and the existing deterministic construction boundary. A failed constructor, group registration, payment, effect application, quest binding, or later settlement restores the complete owning operation, including live caches. No half-filled profile, partial group, free skill effect, duplicate reward, or phantom occupied cell is an acceptable fallback.

Region hunts retain the first specification's undersupply acceptance and natural recovery model. Bound clear-outs bind actual persistent identities and preserve one-shot cleanup. The individual grade is an input to encounter authoring, not the commission's final grade; group size, simultaneous opponents, location, and task structure require their own reasoned assessment.

## 10. Verification and acceptance evidence

Use shared synthetic mechanics to establish calculations and transitions. Production integrity checks iterate current declarations and validate real references and bounds; they do not carry a fixed list of this batch's keys or duplicate its numeric values. Representative production smoke may resolve the explicit content it exercises under the repository's data-contract conventions.

| Boundary | Required evidence |
| --- | --- |
| Formal identity | All new variants construct through their declared parent; the crocodile keeps its existing species/default while its new stronger variant has an independent complete profile. |
| Literal construction | Constructed base traits and resources come from the selected profile, with no baked skill multiplier or generic tier-example fallback. |
| Slime guard | Real selection and payment apply a caster-only defense effect; an unrelated actor stays unchanged; spent SP and guard lifetime survive reload. |
| Goblin hit rider | A synthetic landed hit applies the agility penalty to its actual recipient; a miss preserves recipient agility; movement and flee availability remain governed by their ordinary gates. |
| Rat agility | A real cast pays once and applies the self effect independent of any target hit; repeated application refreshes an aged mount under the shared lifetime rules. |
| Crocodile composition | The new variant uses real existing MP drain with actual-loss transfer and independently paid self guard; insufficient current MP prevents guard selection without a fabricated payment. |
| Boar targets and resources | The single-target strike affects its chosen enemy; the sweep resolves all eligible enemies with separate hit/defense outcomes, one MP/SP payment, and untouched ally controls. |
| Failure | Fault injection after an actual payment, effect write, or placement write restores resources, recipients, identities, and caches, including the owning operation's earlier writes. |
| Mixed encounter | The goblin pair and rat construct as three independent IDs, engage in one ordinary session, retain distinct targets, and produce defeat credit once per actual individual. |
| One-shot bosses | Defeat, committed reload, revisit, map read, and quest acceptance keep the defeated site cleared. An escaped living boss remains the same target with its actual remaining resources. |
| Sparse placement | New weak creatures are restricted to their authored habitat patches; high variants stay outside ordinary pools; undefined examples never replace them. |
| Editorial publication | Structural identity indices and ledger coverage match the current registry; a human read verifies affirmative prose and ecology/capability consistency. |

For implementation smoke, build real individuals from this batch, observe AI selection and payment, execute the mixed encounter and each distinct consumer composition, complete or escape a boss encounter, re-engage, and reload committed state. Observe the claimed low/high combat roles through the existing calibration boundaries. A registry load or an assertion that a name exists is not sufficient proof.

Register every new test module/method in its required shard and trace substantive requirements using canonical IDs. Run focused tests plus observability lint whenever changed logging requires it, and `uv run --locked python -m tools.contract_gate` before handoff. Preserve deterministic offline operation; complete evidence and managed browser suites remain CI-owned.

## 11. Written review and planning gate

All seven content sections and the affirmative-prose instruction were approved in conversation. Commit this document, perform inline self-review for completeness and consistency, and ask the user to review the written specification. Resolve that review and the three-document approval state before entering `writing-plans`. Feature implementation requires the separate project workflow and is not authorized by content or plan approval.

## 12. Proposal set and implementation batches (2026-11-05)

Twelve OpenSpec changes implement this design under `openspec/changes/`. All twelve are in phase `proposed`, hold no branch or worktree, and pass `openspec validate --all --strict`. Every prerequisite from the two earlier designs is archived and merged on `master`: all nine regional-population changes and all eight field-behaviour changes, ending with `paid-party-retreat` (merge `1b1be7b8`). No change below waits on unlanded earlier work. This section records scope and order; it authorizes no implementation.

| Order | Change | Design sections | Scope | Depends on | Batch |
| --- | --- | --- | --- | --- | --- |
| 1 | `activity-group-formation` | 4.1, 7.1, 9 | Form movement groups from each binding's policy in zone births, manual sites and the forecast; a solitary binding may cover several members | none | 1 |
| 2 | `owned-kit-decision-coverage` | 5, 6, 9 | Report any shipped variant whose owned support active its effective legacy mode can never select, without blocking rollback | none | 1 |
| 3 | `affirmative-monster-prose-guidelines` | 2, 8 | Affirmative public-prose rule, third-batch approval scope and roster-free kit wording in the creation guide (docs only) | none | 1 |
| 4 | `site-member-activity-bindings` | 3, 7.2, 7.3 | Per-row activity bindings, optional site override with precedence, designated single-individual display label | 1 | 2 |
| 5 | `mudfilm-slime-species` | 3, 4.1, 5, 6, 8 | 泥膜史萊姆・濕岸型, self film guard, utility binding, bestiary and ledger, first support-only representative | 2, 3 | 2 |
| 6 | `wax-pouch-rat-species` | 3, 4.3, 5, 6, 8 | 蠟囊鼠・藏穀型, self agility slip, utility binding, bestiary and ledger | 5 | 3 |
| 7 | `sticky-palm-goblin-species` | 3, 4.2, 5, 6, 8 | 膠掌小鬼・懸巢型, elementless grab with landed-hit agility penalty, legacy binding, bestiary and ledger | 6 | 4 |
| 8 | `reservoir-warden-variant` | 3, 4.4, 5, 6, 8 | 吞潮鱷・蓄潮型 high A, existing drain plus MP-funded self guard, utility binding, affirmative crocodile rewrite, new representative | 7, 2 | 5 |
| 9 | `weak-species-habitats` | 7.1 | Five sparse bounded zones, compositions and activities for the three weak species | 1, 5, 6, 7 | 5 |
| 10 | `ember-bristle-boar-species` | 3, 4.5, 5, 6, 8 | 焙鬃野豬・焙窩型 high B, fire physical strike and sweep, legacy `pack_hunter`, new representative | 8 | 6 |
| 11 | `abandoned-transfer-station-encounter` | 7.2, 10 | One-shot mixed site (two cohesive goblins, one independent rat) and its production smoke | 4, 9, 6, 7 | 6 |
| 12 | `high-tier-boss-sites` | 3, 7.3, 10 | Two one-shot labelled territorial boss sites and their smoke | 8, 10, 11, 4 | 7 |

Changes 3 and 5–12 declare `skip_specs: true`: they are content data, documentation or production smoke executed by existing contracts. Changes 1, 2 and 4 carry delta specs for `monster-field-activity`, `monster-behaviour-profile` and `monster-site-placement`.

### 12.1 Batch structure

Batches run serially; the changes inside one batch run in parallel.

- **Batch 1: changes 1, 2, 3.** No prerequisite. Change 1 owns `world/lore/monster_activity.py`, `world/maps/regional_population.py`, `world/maps/monster_sites.py` and `world/maps/population_forecast.py`; change 2 owns `world/rules/monster_behaviour.py`; change 3 owns only `docs/lore/monster-creation-guidelines.md`.
- **Batch 2: changes 4 and 5.** Change 4 extends change 1's helper and writers; change 5 needs change 2's support-kit check and change 3's prose rule. Change 4 edits placement and map owners, change 5 edits species, skill, rulebook, narration, bestiary and AI-evidence files, so their files are disjoint.
- **Batches 3 and 4: changes 6 and 7, one each.** Every species or variant change appends to `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, the buff, modifier and status rulebooks, the bestiary, the editorial ledger and `docs/development/monster-content-expansion.md`. Every new buff, modifier rule or mode override also moves the AI tuning fingerprint that `docs/development/monster-ai-activation-evidence/activation.json` records, and the regenerated selector evidence cannot be merged textually. The content chain 5 → 6 → 7 → 8 → 10 is therefore strictly serial.
- **Batch 5: changes 8 and 9.** Change 9 needs the three weak species and change 1. It edits only placement and activity declarations and `docs/development/regional-monster-population.md`, which are disjoint from change 8's content files.
- **Batch 6: changes 10 and 11.** Change 11 needs changes 4 and 9 and both low-tier group species. Its declarations, smoke module and review subsection are disjoint from change 10's content files. Both add entries to `.github/evennia-shards.json` and `tools/test_data_freeze.json` at different positions, and a textual conflict there keeps both entries.
- **Batch 7: change 12.** It needs both high-tier contents (8, 10) and extends the declaration tuples, smoke module and review subsection that change 11 creates.

### 12.2 Shared-file rules

`content/map-reference-context.json` hashes every module under `world/lore` and `world/rules`, so it conflicts mechanically between any two parallel changes. Resolve it by rerunning `uv run --locked python -m tools.map_reference_context` after rebase, never by hand-merging. `.github/evennia-shards.json` and `tools/test_data_freeze.json` gain one entry per new data-contract module (changes 5, 8, 10, 11). No change edits command documentation or browser shards.

### 12.3 Requirement-level ordering

Change 1 modifies `monster-field-activity::activity-declarations-publish-complete-validated-bindings` and adds the group-formation requirement. Change 4 adds two `monster-site-placement` requirements that rely on change 1's formation rule, so change 4 archives after change 1. Change 2 adds one `monster-behaviour-profile` requirement that no other change touches.

### 12.4 Known deviations recorded for review

Slime, rat and the crocodile boss bind the utility decision mode because the legacy body never proposes a support skill. Under `monster-flee-policy` a utility monster never flees voluntarily, so §5's available innate flee, §7.1's retreat orientation and §7.3's "either side can flee" hold for these three only through passive or defended-area field aggression and the opposing party's paid retreat. The goblin and the boar stay legacy and keep their flee thresholds. The slime zones are bounded rectangles, not per-cell damp patches, because the zone model has no wetness predicate. Both deviations are recorded in the named review documents and do not block delivery.
