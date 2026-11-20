# Ciaran-Commons Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-ciaran-commons` change (`ciaran_elenis`, `ciaran_teliel`).

### Profile and Place Bindings
- `ciaran_elenis_home` (place: `艾莉妮斯的家` off `長老古樹下`； host: `艾莉妮斯‧達恩斯特瑞德爾`； service_id: `ciaran_elenis`) -> `world/lore/dialogue/content/ciaran_elenis.yaml`
- `ciaran_teliel_home` (place: `泰莉爾的家` off `練刀場`； host: `泰莉爾‧菲溫德`； service_id: `ciaran_teliel`) -> `world/lore/dialogue/content/ciaran_teliel.yaml`

Canonical Sources:
- `tmp/story_settings/world_info.md` (authoritative setting: Ciaran elven standing and rarity, religion boundary, non-commercial life, lifespan, 15–16th-century-with-magic baseline).
- `world/lore/npc_profiles/ciaran_homes_a.py` and `ciaran_homes_b.py` (persona cards, voice lines, appearance, personality, habits).
- `world/lore/settlements/places_ciaran.py` (room definitions, coordinates, host titles, doorway keys).
- `docs/lore/settlement-locations.md` (settlement narrative, attendant host blueprint, non-commercial life).
- `.agents/skills/npc-dialogue-content/SKILL.md` and `references/scene-schema.md`.
- `skill://chinese-content-writing-guideline` and `skill://writing-style-guideline`.

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Culture
- Canon: Total world population of elves is approximately 300 (roughly 100 in the Ciaran tribe of Shadow Valley) compared to 21 million humans and 9 million beastfolk. All three nations regard elves as beings above royalty and extend the highest courtesy. Elves are indifferent to other races, neither curious nor deferential.
- Society and Culture: Elves are all-rounders with no fixed caste, profession division, or merchant institutions. There are no shops, no business hours, no bosses, and no apprenticeships. A villager makes what they love and shares or trades from home.
- Host handling:
  - `ciaran_elenis`: The elder of the village (age 980, apparent age 42) holds no governing authority, gives no orders, and assigns no tasks. She sits under the ancient tree, strips bark for village children to weave rope, and remembers centuries of daily life. She addresses all visitors as youngsters, exhibiting warmth and patience without subservience or curiosity toward human politics.
  - `ciaran_teliel`: The sword instructor (age 620, apparent age 28) rejects the title of teacher and holds no formal school or academy. She keeps the drill ground, leaves wooden training blades by the door for anyone to pick up and practice, and spars with no outsiders.

### Elven Religion and the Truth of the Three Gods
- Canon: Elves never proselytise. Outsiders know nothing of elven religion or the truth of the three ancestral goddesses (goddess of light for Fionnen, goddess of darkness for Ciaran, goddess of knowledge for Eolas). Divine mysteries (governance, lineage, veil) are strictly exclusive to elves possessing divinity.
- Host handling:
  - The hosts never explain divine mysteries or reveal the truth of the three goddesses.
  - No human church doctrine is borrowed into a Ciaran mouth.
  - When discussing bladecraft or memory, Elenis and Teliel speak purely of the village's lived traditions: bladecraft as protection and enduring memory rather than divine mandate or conquest.

---

## 3. Retained Non-Commercial Behaviour and Place Consistency

- Both `ciaran_elenis_home` and `ciaran_teliel_home` are registered as `PlaceKind.HOME` with `profession="attendant"`. They provide conversational dialogue only and sell no goods or services.
- Neither host charges coin, sells items, or grants free mechanical rewards (items, tuition, techniques, or attributes).
- All referenced locations strictly resolve against `places_ciaran.py` and `content/maps/settlements/elven_village_ciaran.yaml`:
  - `長老古樹下`
  - `村中廣場`
  - `共食棚`
  - `練刀場`
  - `溪畔小徑`
  - `暗影谷村`

---

## 4. Per-Topic Intent and Scene Structure Review

### A. ciaran_elenis_home (Elenis Darnstrider)
1. **Opening Greeting**: In-character welcome at the sitting stone under the ancient tree. She strips bark, addresses the actor as a youngster, and affirms that she has no tasks to assign or treasures to give, but has time to converse about village history and the woods.
2. `ciaran_elenis_home.topic_01` (keyword: `村子`； label: `村子`):
   - Actor asks how the village was founded underground on the western ridge and how villagers live. Host explains that centuries ago the village moved as trees matured and subterranean streams shifted; villagers follow their inclinations without governors or laws, sharing food at the communal shelter and solving concerns under the tree.
3. `ciaran_elenis_home.topic_02` (keyword: `基亞蘭`； label: `基亞蘭`):
   - **Pure chain declaration**: Declares `predecessors: [ciaran_elenis_home.topic_01]` and `disclosure: pure_chain`. No `requires` condition declared. Serves as natural conversational continuation after exploring the village's foundation.
   - Actor follows up on why the Ciaran line is dedicated to bladecraft. Host explains that outsiders see stubbornness, but the tribe simply possesses enduring memory. Sword hilts bear ancestral names; blades exist to protect loved ones and the valley, recalling how the twin child (Yuka) trained on the field under Teliel's watchful eye.
4. `ciaran_elenis_home.topic_03` (keyword: `森林`； label: `森林`):
   - Actor asks how to navigate safely in the dense mountain forests of the central range. Host remarks that the forest recognises footsteps; gathering follows natural seasons and rest cycles. As long as travelers take only what they need with respect, the forest leaves an open path back.
5. `ciaran_elenis_home.topic_04` (keyword: `往事`； label: `往事`):
   - Actor asks about memorable events from centuries of watching the valley. Host laughs softly and notes that real memory consists of small moments: children sliding across the frozen winter stream laughing all the way to the tree. She notes that treaties on stone crumble, advising troubled visitors to wash their faces by the stream and let disputes fade.

### B. ciaran_teliel_home (Teliel Feywind)
1. **Opening Greeting**: Host cools down after finishing forms at the edge of the drill field, observing the visitor's posture. She notes that the field is open, practice wooden blades stand by the door, and she offers no shortcuts or student status.
2. `ciaran_teliel_home.topic_01` (keyword: `刀術`； label: `刀術`):
   - **Variant `blade_practitioner`**:
     - Condition: `skill_owned` with `skill_key: basic_swordplay`, `min_proficiency: 1`.
     - Priority: 10 (explicit distinct priority).
     - Rationale: Recognises an actor who already trains with weapons by their calluses and stance. Host distinguishes between external swordsmanship (thrusts and parries) and Ciaran bladecraft (momentum, body flow, supple wrist). She rebuffs being called a teacher and advises taking a wooden blade into the field to let the body learn.
   - **Fallback `ciaran_teliel_home.topic_01_scene`**:
     - Unconditional base scene. Rebuffs being called a teacher; explains that Ciaran children learn the grip before the edge, using blades for protection with steady breath and stance. Points to generations of blade marks carved into boundary trees.
3. `ciaran_teliel_home.topic_02` (keyword: `練習`； label: `練習`):
   - Actor inquires about training rules and instruction. Host clarifies that there are no classes or hand-holding: one enters the field, plants feet, bends knees, drops shoulders, and practices until palms and footing memorize the flow. Misaligned postures are corrected by wind resistance and wrist strain.
4. `ciaran_teliel_home.topic_03` (keyword: `練刀場`； label: `練刀場`):
   - Actor asks about the history and users of the drill ground. Host describes the field as active day and night; wooden blades by the door require no borrowing permission. For real forged blades, she directs inquiries to blade-smith Hailiel across the clearing, whose newly quenched blades are brought to Teliel to test balance and grip.
5. `ciaran_teliel_home.topic_04` (keyword: `比劃`； label: `比劃`):
   - Actor asks for a sparring match. Host firmly refuses: villagers do not duel outsiders, and she does not spar for demonstration. Blades are for defense, not traveler amusement. She directs anyone testing their cutting angle to practice against dead tree trunks at the forest edge.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No mechanics, attribute numbers, UI buttons, command syntax (`rest`, `talk`, `buy`), or OOC explanations.
- **Punctuation and Script**: Clean formatting with full Traditional Chinese rules observed in dialogue files.
- **Prohibited Patterns**:
  - No honorific pronouns.
  - No trailing particles before punctuation.
  - No Chinese wuxia tokens.
  - No calques.
- **Scene Shapes and Lines**:
  - Every scene consists of 4 to 5 lines (within the mandatory 3–8 range).
  - Every fallback and variant scene begins with an actor utterance.
  - Every scene includes host dialogue and stage narration.
- **Revision Tracking**: All authored scenes declare `revision: r2`.
- **Offline / Playback Verification Note**:
  - Fully verified offline via static dialogue compilation, schema validation, NPC content linter, and Chinese language linter.
  - Direct live browser manual playback was not executed in this headless worktree environment; offline contracts and command doc tests provide regression verification.

---

## Rewrite (2026-11-20)

This pass records the final prose of the two commons hosts, `ciaran_elenis` and `ciaran_teliel`. Both greetings were rewritten. Every topic ID, scene ID, keyword and label is retained, and no topic declares `requires`, `unavailable`, or a formal `refusal` scene; the only conditional structure is Teliel's `blade_practitioner` variant. Both hosts are adults — Elenis apparent age 42, Teliel apparent age 28 — and the prose keeps them in the canon's frank but unrushed domestic register without drifting into explicitness. Elenis's `ciaran_elenis_home.topic_02` keeps its `predecessors: [ciaran_elenis_home.topic_01]` and `disclosure: pure_chain`, with no `requires`.

### ciaran_elenis (艾莉妮斯‧達恩斯特瑞德爾)

**Greeting (rewritten).** She sits barefoot among the old tree's roots, a strip of bark in her lap, and in her measured, unhurried voice invites the "小傢伙" to sit, stating plainly she has no errand to assign and no treasure to hand out — only the village's history, the forest's rules, and the half-remembered old things.

1. `ciaran_elenis_home.topic_01` (keyword `村子`, label `村子`, fallback `…_scene`, **r3**). **Intent:** explain how the village came to settle in the valley bottom and how its people live without rulers. **Bridge:** the actor's opening question about how the village settled is answered at once — the tribe followed the mountain stream when its course shifted and simply lives by inclination; the follow-up "who decides when there's a dispute?" is motivated by the host's "no officials, no one rules" answer and is answered by the council under the old tree, leaving Elenis the one who only remembers.

2. `ciaran_elenis_home.topic_02` (keyword `基亞蘭`, label `基亞蘭`, **r3**, `pure_chain`). **Intent:** ground the Ciaran line's devotion to the blade in enduring memory rather than stubbornness. **Bridge:** the actor reopens the prior topic ("你方才提起村子的來歷…") and asks why the Ciaran are sworn to the blade; the host answers with hilt-carved names and the remembered warmth of a held grip, and the follow-up about the younger generation is answered with 悠花 learning on the field under 泰莉爾's watch.

3. `ciaran_elenis_home.topic_03` (keyword `森林`, label `森林`, **r3**). **Intent:** teach how a stranger walks the western ridge's dense forest without losing the way. **Bridge:** the actor asks how to avoid getting lost; the host answers that the forest recognises footsteps and that the way is kept in feet and back rather than eyes, which motivates the actor's "so respect is enough?" and the host's closing that the woods leave a way back for the ungrasping.

4. `ciaran_elenis_home.topic_04` (keyword `往事`, label `往事`, **r3**). **Intent:** show that a long memory treasures small moments — children sliding on the frozen stream — over carved treaties. **Bridge:** the actor asks what she still remembers; she answers with the children laughing down the winter ice, and when the actor observes that small moments are what last, she closes with the stream-side advice to those who come to her burdened.

### ciaran_teliel (泰莉爾‧菲溫德)

**Greeting (rewritten).** She has just finished a set of forms at the field's edge, sweaty and barefoot, and scans the visitor's stance before stating the field is open day and night, the wooden blades stand by the door, and she takes no students and offers no shortcut.

1. `ciaran_teliel_home.topic_01` (keyword `刀術`, label `刀術`). **Intent:** separate Ciaran bladecraft's momentum-and-flow doctrine from outside swordsmanship. **Bridge:** the opening question about the difference in paths is answered at once by the host's contrast of outside thrust-and-parry against whole-body turning, which motivates the follow-up about arm-versus-body coordination and its answer. **Variant `blade_practitioner`** (`when: kind: skill_owned`, `skill_key: basic_swordplay`, `min_proficiency: 1`, `priority: 10`, scene `ciaran_teliel_home.topic_01_swordsman_scene`, **r3**) recognises the callus-and-relaxed-shoulder tell before the same doctrine and closes that the body learns faster than the ear. **Fallback** (`ciaran_teliel_home.topic_01_scene`, **r3**) delivers the same doctrine to the unweaponed visitor and points at the generations of blade-marks on the boundary trees.

2. `ciaran_teliel_home.topic_02` (keyword `練習`, label `練習`, **r3**). **Intent:** describe self-directed training with no classes and no hand-holding. **Bridge:** the actor asks about the rules for training; the host answers there are none beyond planting the feet, bending the knees and dropping the shoulders, which motivates the "do you correct nothing?" follow-up, answered by the body's own correction through wind resistance and wrist strain.

3. `ciaran_teliel_home.topic_03` (keyword `練刀場`, label `練刀場`, **r3**). **Intent:** describe the drill ground's all-hours openness and where a real blade is found. **Bridge:** the actor asks who uses the field; the host answers day and night, wooden blades borrowed without leave and returned, which motivates the follow-up about the smith and its answer naming Hailiel across the field, whose freshly quenched blades Teliel tests for balance and grip.

4. `ciaran_teliel_home.topic_04` (keyword `比劃`, label `比劃`, **r3**). **Intent (refusal carried in-scene):** refuse a spar outright and turn the asker to the dead trunks at the forest edge. **Bridge:** the actor asks for a demonstration match; the host declines in the same answer — no villager spars outsiders, and blades are not traveller amusement — which motivates the actor's apology and the host's redirection to the practice trunks. The refusal lives inside the fallback body, not a formal `refusal` scene.

### Adult-voice pass (2026-11-20)

This pass added an adult register to three scenes. IDs, conditions, variant priorities, `pure_chain`, buy-back boundaries and service semantics are all unchanged; the two hosts remain adults (Elenis apparent 42, Teliel apparent 28), and neither scene touches a host below 18. `ciaran_valwyn` and every Eolas host received no sexual content.

- `ciaran_elenis_home.topic_04` → **r4**. The host's remembered-lover answer now runs to an explicit memory: a blade-forging woman who undressed her to a belt by the stream, her palm down Elenis's back and thigh, and the line "那晚我喘著要她慢些" — a remembered lover and frank desire in her own unhurried voice, closed by the advice to hold whoever you want before the warmth leaves.
- `ciaran_teliel_home.topic_02` → **r4**. The answer now adds direct sexual talk in her own voice — "我大半是在床上教會別人這個道理，身子貼著身子，誰使力、誰發緊，一點都瞞不住" — folding the body's stiffening into the lesson on the blade.
- `ciaran_teliel_home.topic_04` → **r4**. The spar refusal now carries body framing — "刀貼著刀，身子就貼著身子，我不拿這個招呼生人" — before the unchanged redirection to the dead trunks.
