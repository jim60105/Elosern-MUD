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
- All referenced locations strictly resolve against `places_ciaran.py` and `village_ciaran.py`:
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
