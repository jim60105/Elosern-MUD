# Upper-Civic Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-upper-civic` change (`altoria_noble_watch_captain`, `altoria_drill_instructor`, `altoria_academy_dean`).

### Profile and Place Bindings
- `altoria_noble_watch` (place: 聖潔王都貴族區衛所, host: 古利安‧鷹守) -> `world/lore/dialogue/content/altoria_noble_watch_captain.yaml`
- `altoria_drill_yard` (place: 聖潔王都校場, host: 伊沃‧高丘) -> `world/lore/dialogue/content/altoria_drill_instructor.yaml`
- `altoria_academy` (place: 聖潔王都王立魔法學院, host: 奧德溫‧薩契) -> `world/lore/dialogue/content/altoria_academy_dean.yaml`

Canonical Sources:
- `tmp/story_settings/world_info.md` (authoritative setting: elven standing/rarity, religion, magic system, academy structure, guild grades, currency and politics).
- `world/lore/npc_profiles/altoria_upper.py` (persona cards, voice lines, appearance, personality, habits).
- `world/lore/settlements/places_altoria_upper.py` (room names, host details, place kind, descriptions, exterior coordinates).
- `docs/lore/settlement-locations.md` (§治理與防衛 貴族區/統治機構、衛兵駐所與城門、訓練場/競技場；§知識與交通 魔法學院與圖書館).
- `skill://npc-dialogue-content`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Culture
- Canon: Total population ~300 elves across three branches (斐歐恩, 基亞蘭, 伊歐拉斯) compared to 30M humans and orcs. Elves are regarded as a rank above royalty (皇族之上的高級存在).
- Society & Culture: No fixed professions or class divisions; all elves are all-rounders (全能者). Physical attributes range 70–95. Elves have open relationships with no marriage system or concept of shame concerning nudity/sexuality.
- Host handling:
  - `altoria_noble_watch_captain`: Treats `social_identity_is: noble` strictly as declared social standing, never conflating elves with nobles or inventing heraldic document checks.
  - `altoria_drill_instructor`: Does not lecture elves on mortal martial arts; acknowledges that true combat competence is forged through sweat and practice.
  - `altoria_academy_dean`: Explicitly notes in `altoria_academy.topic_03` that elves possess natural inborn magic affinity and learning tempo that mortal races cannot simply replicate through academy instruction, upholding elven canon without condescension.

### Religion (光明教會) and the Noble Quarter's Open Gate
- Canon: The noble quarter in 聖潔王都 has no gate or checkpoint; anyone can enter. The watch post handles patrolling, fire safety, and neighborly complaints, posting no commissions. The royal palace approach is host-less and empty.
- Host handling:
  - `altoria_noble_watch_captain`: Emphasizes repeatedly that the quarter sets no checkpoint, requires no entry registry, and that streets belong to everyone. The palace gate is open, quiet, and cold, with no audience scheduled and no documents collected.

### Guild Rank System and Training/Academy Boundaries
- Canon: Adventurers' guild grades (F..S) are examined and awarded exclusively by the guild at the guild hall counter. The drill yard provides open ground and practice posts, but offers no exams, certificates, or sparring partners, with no fixed business schedule. The academy teaches knowledge and explains theory (spell tiers: 學徒／術師／大師／賢者／主宰／神格; eight elements: 火／水／風／土／雷／冰／光／暗), without selling shortcuts, apprenticeships, or enrollment ranks.
- Host handling:
  - `altoria_drill_instructor`: Explains that grading belongs to the guild examiners, directing candidates to the guild hall in the central square, while noting the yard is open to anyone who comes to train.
  - `altoria_academy_dean`: Clarifies that rank assessment belongs to the guild, while the academy explains spell MP tiers and elements rather than awarding diplomas or taking personal disciples.

---

## 3. Retained Service Behaviours and Bound Semantics

- Services Retained Unchanged:
  - `altoria_noble_watch`: Patrols street, inspects firefighting water tanks, notes minor household complaints. Grants no palace access exceptions, appointments, or escorts; posts no commissions.
  - `altoria_drill_yard`: Lends field space and practice posts with open access for all. Grants no combat bonuses, issues no certificates, arranges no sparring partners, and does not conduct guild examinations.
  - `altoria_academy`: Imparts magic knowledge and books. Sells no shortcuts, collects no tuition, awards no ranks, and conducts no apprentice initiation.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. altoria_noble_watch (古利安‧鷹守)
Formal, polite, meticulous register. Speaks with complete sentences, self-refers as 「我」 and 「本衛所」, addresses visitor as 「訪客」 (or 「閣下」 when noble), uses spoken zh-TW particles rather than classical archaic particles, and closes with 「請自便」.
1. **Opening Greeting**: Captain looks up from turning a ledger page, pushes thin-framed glasses, and states that the noble quarter has no checkpoint and requires no registry for walking the streets.
2. `altoria_noble_watch.topic_01` (keyword: 貴族區):
   - Variant `noble_visitor` (`SocialIdentityIs`: `noble`, priority 10): Actor asks if entering the quarter requires the watch to verify identity or record titles. Captain straightens up with courteous respect, confirming the streets are open to everyone without pedigree checks and that mansions inspect invitations at their own gates. Closes with 「請自便」.
   - Fallback `altoria_noble_watch.topic_01_scene`: Actor asks if ordinary travelers can enter without pass/registry. Captain explains the watch patrols streets and water lines without interrogating backgrounds; mansion gates belong to families, while streets are free for all. Closes with 「請自便」.
3. `altoria_noble_watch.topic_02` (keyword: 謁見):
   - Actor inquires about presenting petitions or seeking audience with the royal court. Captain smiles wryly with self-deprecation, stating the watch has no dispatch authority, points down the avenue to the open palace forecourt, and describes the palace as quiet and cold.
4. `altoria_noble_watch.topic_03` (keyword: 衛所):
   - Actor asks about the watch post's duties. Captain details the three responsibilities (hourly patrols, fire water checks, recording household complaints), mentions coordinating with South Gate captain 托瓦德‧鄧堡, and offers local information.
5. `altoria_noble_watch.topic_04` (keyword: 委託):
   - Actor asks if the watch issues beast-clearing or guard commissions. Captain confirms the watch posts no bounties, redirecting adventurers to the guild hall's daily notice board in the central square, and distances the watch from private mansion arrangements.

### B. altoria_drill_yard (伊沃‧高丘)
Colloquial, earthy, seasoned veteran register. Uses rustic sentence-ending particles 「啦」「哪」, blunt and practical advice, avoids mechanics terminology and fixed schedules, and emphasizes sweaty honest effort.
1. **Opening Greeting**: Instructor shakes mud off his sleeves, asking if visitor is there to watch or train, warning upfront that there are no shortcuts.
2. `altoria_drill_yard.topic_01` (keyword: 修煉):
   - Actor asks about yard rules and hours. Host explains the ground and posts are open for anyone who comes to train without time restrictions, tells visitor to hit posts freely without fear of noise, and recommends resting on the bench when tired.
3. `altoria_drill_yard.topic_02` (keyword: 考核):
   - Actor asks if the yard conducts guild rank advancement exams. Host bluntly redirects to the guild hall counter on the east side of the central square, warning against failing the exam without solid basics before surviving a few exchanges.
4. `altoria_drill_yard.topic_03` (keyword: 切磋):
   - Actor asks about arranging sparring partners. Host refuses to provide or recruit sparring opponents, warns about dangerous beasts outside the city walls, and notes the only benefit of the yard's soft dirt is avoiding cracked skulls on stone streets.
5. `altoria_drill_yard.topic_04` (keyword: 教頭):
   - Actor addresses host directly as drill instructor, asking if he teaches specific steps or power techniques. Host defers, claiming his job is just keeping the yard and weeding, rejects fancy tricks and certificates, and emphasizes honest sweat over envying marks on wooden posts.

### C. altoria_academy (奧德溫‧薩契)
Scholarly, structured, patient, pedantic register. Opens with "welcome", analyzes questions in two layers, praises insightful inquiries with 「問得好」, speaks in natural spoken zh-TW cadence, and refuses shortcuts.
1. **Opening Greeting**: Dean erases chalk formula, turns around, welcomes visitor, and invites questions on spell tiers, elements, and affinity, affirming that knowledge is taught while shortcuts do not exist.
2. `altoria_academy.topic_01` (keyword: 魔法等級):
   - Variant `magic_scholar` (`SkillOwned`: `magic_circle_comprehension` >= 1, priority 10): Actor asks in natural spoken cadence how mana consumption differs across tiers given basic knowledge of magic circles. Dean is delighted, praises the question, explains that spell formulas are built upon MP consumption tiers (學徒／術師／大師／賢者／主宰／雙路匯流神格), and points to library books arranged by tier.
   - Fallback `altoria_academy.topic_01_scene`: Actor asks how spell tiers in ancient books are categorized. Dean explains the two layers of the question: spell tiers based on MP consumption (學徒／術師／大師／賢者／主宰／神格) with concrete examples (火焰箭, 水箭術, 風刃術, 火焰風暴, 飛行術, 暴風雪, 高階治癒), opening the library to study.
3. `altoria_academy.topic_02` (keyword: 元素):
   - Actor asks about the nature and roles of the elements. Dean manifests a soft white light in his palm and presents the eight canonical elements and their operational roles: 火 (burst/burn), 水 (mana tides), 風 (swiftness/movement), 土 (terrain/ward), 雷 (initiative/stuns), 冰 (stillness/freezing), 光 (healing/purification), 暗 (weakening/erosion), emphasizing that true comprehension comes from channeling mana resonance.
4. `altoria_academy.topic_03` (keyword: 親和):
   - Actor asks how magic affinity differences arise across beings. Dean analyzes in two layers: species inborn affinity (elves have innate attunement and fast learning tempo, whereas orcs have strong bodies but limited affinity) and personal element inclination, explaining that academy cannot grant affinity but helps clarify paths.
5. `altoria_academy.topic_04` (keyword: 求學; renamed from the wuxia keyword 拜師):
   - Renamed from `拜師` to `求學` (label `求學`) to comply with the JRPG fantasy anti-wuxia rules while keeping `topic_id: altoria_academy.topic_04` unchanged. The master-and-disciple framing went with it: the actor asks how the academy's lessons are run and whether a tutor can take one student alone, not whether a master will accept a disciple.
   - Dean answers that the academy hands no student to a single tutor and offers no private instruction; the lectures are open to whoever walks in. Spells and battlefield craft alike come from reading and drilling day after day, and the academy lays out knowledge but cannot do the work for anyone. Anyone wanting their level assessed goes to the adventurers' guild hall east of the central plaza, which holds the authority to grade it.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No backticks, command names (`rest`, `buy`, `talk`), or UI mentions. No combat mechanic units (such as 回合).
- **Punctuation & Script**: Full-width Traditional Chinese punctuation (，。、「」『』？！). Space between CJK and ASCII alphanumeric characters.
- **Prohibited Patterns**: Zero instances of 「您」, sentence-final 「的，」/「的。」, or calques (折入, 回填, 落地, 賦能). Minimized classical archaisms (亦／皆／乃 replaced by spoken equivalents).
- **Wuxia Banned Tokens**: All wuxia terms (過招, 劍招, 招式, 祕技, 拜師, 功夫, 江湖, 客官, 掌門) eliminated. Keyword `拜師` in `altoria_academy.topic_04` renamed to `求學`, and the training-yard examination line no longer counts combat turns.
- **Scene Shapes**: All formal scenes start with complete actor `speech` line, followed by host responses and stage narration, within 3–8 lines.
- **Revision Tracking**: All authored scenes across all three hosts declare `revision: r2`.
- **Offline / Browser Smoke Note**: In accordance with slice constraints, local browser manual login is non-operational and content slices add no test modules; offline data integrity is verified via `DIALOGUE_SNAPSHOT` and focused Evennia logic test execution.

---

## Rewrite (2026-11-20)

This section records the prose rewrite of all three hosts under `authored-dialogue-content-upper-civic`. Every `topic_id`, `scene_id`, `keyword`, `label`, variant `when` condition, variant priority, and service semantics was preserved byte-for-byte; only the prose was replaced. No `refusal` scenes exist in any of the three files. The `altoria_academy.topic_04` keyword remains `求學` as established in the prior change. All authored scenes moved from `revision: r2` to `revision: r3`.

### A. altoria_noble_watch (古利安‧鷹守)

**Greeting rewrite**: The new greeting sets down the quill, adjusts the glasses, and states up front that the quarter sets no checkpoint, needs no registry, and that the watch handles patrol, fire safety, and household reports.

1. `altoria_noble_watch.topic_01` (keyword: 貴族區, label: 貴族區):
   - Variant `noble_visitor` (`social_identity_is: noble`, priority 10), `revision: r3`:
     - Intent: a noble visitor asks whether the watch must verify identity or record titles at entry, and the host offers courteous reassurance that no pedigree check exists.
     - Causal bridge: the host rises and answers the verification question directly (no title registry, no roadside checks), then hands mansion-gate procedure to each household and closes with 請自便. No heraldic document test is invented.
   - Fallback `altoria_noble_watch.topic_01_scene`, `revision: r3`:
     - Intent: an ordinary traveller asks whether a stranger may walk the quarter without reporting identity, and the host confirms open streets.
     - Causal bridge: the host answers directly (open to all, patrol and fire tanks only, no origin checks), then separates mansion gates (household rules) from the streets (free to all), closing with 請自便.
2. `altoria_noble_watch.topic_02` (keyword: 謁見, label: 謁見), fallback `revision: r3`:
   - Intent: a visitor asks whether petitions and audiences pass through the post, and the host disclaims authority while describing the quiet, open palace forecourt.
   - Causal bridge: the host answers with a wry self-deprecation that the watch forwards no letters and schedules no audience, then directs the guest down the avenue to the open forecourt and describes its stillness—answering the question while refusing the implied service, not as a separate refusal scene.
3. `altoria_noble_watch.topic_03` (keyword: 衛所, label: 衛所), fallback `revision: r3`:
   - Intent: a visitor asks what duties the post performs, and the host enumerates the three responsibilities and the boundary with the South Gate captain.
   - Causal bridge: the host answers with the three duties (patrol, fire-tank checks, household reporting), then names the coordination with 托瓦德‧鄧堡 to delimit the watch's scope, closing with an offer of local information.
4. `altoria_noble_watch.topic_04` (keyword: 委託, label: 委託), fallback `revision: r3`:
   - Intent: a visitor asks where to find beast-clearing or guard work, and the host confirms the watch posts no bounties.
   - Causal bridge: the host answers by stating no bounty board and no commissions, redirects to the guild hall notice board east of the central square, and distances the watch from private mansion arrangements.

### B. altoria_drill_yard (伊沃‧高丘)

**Greeting rewrite**: The new greeting shakes mud from the sleeves, asks whether the visitor came to watch or train, and warns up front that there are no shortcuts—only the dirt, the posts, and honest talk.

1. `altoria_drill_yard.topic_01` (keyword: 修煉, label: 修煉), fallback `revision: r3`:
   - Intent: a visitor asks about yard rules and hours, and the host confirms the ground and posts are open to anyone at any time.
   - Causal bridge: the host answers the rules question directly (no schedule, no restrictions), offers free use of the posts, and closes with the bench for rest, keeping the turn on the question asked.
2. `altoria_drill_yard.topic_02` (keyword: 考核, label: 考核), fallback `revision: r3`:
   - Intent: a visitor asks whether the yard conducts rank-evaluation, and the host redirects grading to the guild.
   - Causal bridge: the host answers that grading is the guild's matter and sends the visitor to the guild-hall counter east of the square, then warns to build basics first so the exam does not end in an early fall.
3. `altoria_drill_yard.topic_03` (keyword: 切磋, label: 切磋), fallback `revision: r3`:
   - Intent: a visitor asks whether opponents can be arranged for sparring, and the host refuses to recruit or provide partners.
   - Causal bridge: the host declines outright (no partners, no recruiting), names the danger of live blades on dirt, and closes on the yard's one real virtue—the soft dirt sparing cracked skulls.
4. `altoria_drill_yard.topic_04` (keyword: 教頭, label: 教頭), fallback `revision: r3`:
   - Intent: a visitor asks whether the instructor teaches steps or power technique, and the host defers to honest sweat.
   - Causal bridge: the host answers by defining the post as keeping the yard and weeding, disclaims fancy tricks and certificates, and turns the guest's attention to the marks they themselves earn on the wood.

### C. altoria_academy (奧德溫‧薩契)

**Greeting rewrite**: The new greeting erases a formula on the blackboard, turns to welcome the visitor, and invites a question on spell tiers, elements or affinity, affirming that the academy teaches knowledge and sells no shortcut.

1. `altoria_academy.topic_01` (keyword: 魔法等級, label: 魔法等級):
   - Variant `magic_scholar` (`skill_owned: magic_circle_comprehension >= 1`, priority 10), `revision: r3`:
     - Intent: a scholar who knows magic circles asks how mana cost differs across tiers, and the host praises the question and answers from that shared ground.
     - Causal bridge: the host opens with 問得好, ties the tiers to mana cost, lists the six tiers, and closes by pointing to the library's tier-ordered shelves—answering at the scholar's level without condescension.
   - Fallback `altoria_academy.topic_01_scene`, `revision: r3`:
     - Intent: a newcomer asks how the tiers in old books are categorized, and the host explains the tier system with concrete spell examples.
     - Causal bridge: the host frames the question in two layers, lists the six tiers by mana cost, then walks from apprentice-rank spells (火焰箭, 水箭術, 風刃術, 治癒術) upward through 術師 and 大師 to the unpayable 主宰 and 神格, closing with the open, tier-ordered library.
2. `altoria_academy.topic_02` (keyword: 元素, label: 元素), fallback `revision: r3`:
   - Intent: a visitor asks how many elements exist and how each differs in use, and the host presents all eight with their operational roles.
   - Causal bridge: the host manifests a soft light, states the eight elements as the first lesson, then gives each element's role (火 burn, 水 drain and return, 風 speed, 土 terrain and ward, 雷 initiative and stun, 冰 freeze, 光 heal and purify, 暗 weaken), closing on mana resonance over rote memorization.
3. `altoria_academy.topic_03` (keyword: 親和, label: 親和), fallback `revision: r3`:
   - Intent: a visitor asks where affinity differences come from, and the host explains the two layers of inborn and personal affinity without granting what the academy cannot give.
   - Causal bridge: the host separates racial endowment (elves innate and fast, orcs strong but shallow of affinity) from personal elemental inclination, then states plainly that the academy cannot bestow affinity, only clarify a path.
4. `altoria_academy.topic_04` (keyword: 求學, label: 求學), fallback `revision: r3`:
   - Intent: a visitor asks how classes run and whether one tutor can take a single student, and the host explains open lectures while refusing private instruction.
   - Causal bridge: the host denies single-tutor and private instruction, states lectures are open to all, grounds progress in daily reading and drilling, and closes by sending level assessment to the guild hall rather than the academy.
