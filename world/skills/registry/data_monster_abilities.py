"""Registry data slice: authored monster resource abilities.

Declared separately from character skill trees (design §3.1, §5.1).
The crocodile contact-drain ability is assembled into SKILL_REGISTRY
with monster identity eligibility and water physical damage with
hit-dependent fixed MP drain. The sparrow contact ability is assembled the
same way with wind physical damage plus a hit-dependent accuracy debuff.
The crab contact ability is assembled the same way with light physical damage
plus a self-mounted defense guard granted by every resolved attempt.
The slime body action is assembled the same way with a self-only defense guard
and no damage occurrence at all.
The rat body action is assembled the same way with a self-only agility
improvement and no damage occurrence at all.
The goblin contact grab is assembled the same way with elementless physical
damage plus a hit-dependent agility debuff on the struck enemy.
The reservoir warden body action is assembled the same way with a self-only
water defense guard paid from the actor's own MP and no damage occurrence.
The boar's two fire strikes are assembled the same way with physical-school
damage that reads the actor's physical attack: one single-target charge and one
area sweep, each paid in both MP and SP, and the area cast resolves every
recipient's own hit and defense while the action pays once.
The spore-cap mushroom's cap bump is assembled the same way with dark physical
damage plus a hit-dependent accuracy debuff on the struck enemy.
The moss-quill porcupine's back ram is assembled the same way with earth
physical damage plus a self-mounted defense guard granted by every resolved
attempt.
The hollow-tree bat's bite is assembled the same way with dark physical damage
plus a hit-dependent fixed HP drain.
The hush-wing owl's swoop is assembled the same way with wind physical damage
plus a self-mounted agility lift granted by every resolved attempt.
The vine-net spider's thread cast is assembled the same way with elementless
physical damage plus a hit-dependent agility debuff on the struck enemy.
The moss-crown stag's two earth strikes are assembled the same way with
physical-school damage that reads the actor's physical attack: one
single-target charge and one area sweep, each paid in both MP and SP.
The mist-spring frog's tongue sip is assembled the same way with water
physical damage plus a hit-dependent fixed MP drain.
The warm-rock salamander's ember-skin bite is assembled the same way with fire
physical damage plus a self-mounted physical attack rise granted by every
resolved attempt.
The bone-breaker vulture's grit-wing strike is assembled the same way with wind
physical damage plus a hit-dependent accuracy debuff on the struck enemy.
The mist-lamp moth's veil-scale flutter is assembled the same way with dark
physical damage plus a hit-dependent agility debuff on the struck enemy.
The rime-scale serpent's two ice strikes are assembled the same way with
physical-school damage that reads the actor's physical attack: one single-target
fang strike and one area tail lash, each paid in both MP and SP, and the area
cast resolves every recipient's own hit and defense while the action pays once.
The drum-wing grouse's wing burst is assembled the same way with wind physical
damage plus a self-mounted agility lift granted by every resolved attempt.
The mud-dam beaver's pelt slap is assembled the same way with earth physical
damage plus a self-mounted defense guard granted by every resolved attempt.
The ore-vein mole's grit claw scrape is assembled the same way with earth
physical damage plus a hit-dependent accuracy debuff on the struck enemy.
The cache-raider wolverine's jaw lock bite is assembled the same way with
elementless physical damage plus a hit-dependent defense debuff on the struck
enemy.
The ore-nest griffin's two wind strikes are assembled the same way with
physical-school damage that reads the actor's physical attack: one single-target
dive and one area wing gale, each paid in both MP and SP, and the area cast
resolves every recipient's own hit and defense while the action pays once.
The clod-ball beetle's head shove is assembled the same way with earth physical
damage plus a hit-dependent agility debuff on the struck enemy.
The dust-mane horse's gallop kick is assembled the same way with wind physical
damage plus a self-mounted agility lift granted by every resolved attempt.
The sluice-spear heron's beak jab is assembled the same way with elementless
physical damage plus a hit-dependent accuracy debuff on the struck enemy.
The lake-mound turtle's two earth strikes are assembled the same way with
physical-school damage that reads the actor's physical attack: one single-target
bite and one area shell slam, each paid in both MP and SP, and the area cast
resolves every recipient's own hit and defense while the action pays once.
The flat-leap goby's tail flick is assembled the same way with elementless
physical damage plus a hit-dependent accuracy debuff on the struck enemy.
The mast-wind gull's snatch dive is assembled the same way with wind physical
damage plus a self-mounted agility lift granted by every resolved attempt.
"""

from world.skills.effects import (
    EffectAudience,
    EffectPolicy,
    GaugeTransferPolicy,
)
from world.skills.registry.builders import _skill
from world.skills.registry.vocab import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillEligibility,
    SkillKind,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
    _skill(
        "tide_devouring_bite",
        "吞潮咬擊",
        "以水屬性力量纏繞咬合，對單一敵方目標造成物理傷害，並在命中時吸取其現有魔力轉入自身。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        usable_out_of_combat=True,
        element="water",
        effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:10"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("tide_devouring_crocodile",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
            ),
            EffectPolicy(
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
                transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
            ),
        ),
    ),
    _skill(
        "grain_shaking_peck",
        "震穗啄擊",
        "以短促氣流啄擊單一敵方目標，造成物理傷害；命中後使對手短暫分心，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # True for both monster abilities: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile declares).
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "buff_apply:grain_rattle"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("sway_whistle_sparrow",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=0.8,
                audience=EffectAudience.ENEMIES,
            ),
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
    _skill(
        "lamp_carapace_claw",
        "燈甲螯擊",
        "以螯足夾擊單一敵方目標，造成物理傷害；出擊時收緊甲殼，短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # True for every monster ability: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile and sparrow declare).
        usable_out_of_combat=True,
        element="light",
        effects=["damage:light:physical", "self_buff_apply:lamp_carapace_guard"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="light",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("tide_lamp_crab",),
        ),
        prerequisites=(),
        effect_policies=(
            # Occurrence 0 is the ordinary enemy strike.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
            ),
            # Occurrence 1 binds the caster with no hit dependency: the guard is
            # part of an affordable, target-resolved attempt, including a miss.
            # A source-enemy-hit dependency would intersect the SELF audience
            # away from the actor (see world/rules/action/routing.py), so this
            # self mount deliberately declares none.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELF,
            ),
        ),
    ),
    _skill(
        "ridge_bracing_kick",
        "固埂蹬擊",
        "以土屬性力量穩住身形後奮力蹬擊單一敵方目標，造成物理傷害；出招時短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # True for every monster ability: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile, sparrow and crab declare).
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "self_buff_apply:ridge_brace"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ridge_burrow_hare",),
        ),
        prerequisites=(),
        effect_policies=(
            # Occurrence 0 is the ordinary enemy strike.
            EffectPolicy(
                coefficient=0.8,
                audience=EffectAudience.ENEMIES,
            ),
            # Occurrence 1 binds the caster with no hit dependency: the guard is
            # part of an affordable, target-resolved attempt, including a miss.
            # A source-enemy-hit dependency would intersect the SELF audience
            # away from the actor (see world/rules/action/routing.py), so this
            # self mount deliberately declares none.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELF,
            ),
        ),
    ),
    _skill(
        "rock_echo_ram",
        "岩響角撞",
        "以土屬性力量結合角撞衝擊單一敵方目標，造成物理傷害；命中後使對手短暫步伐不穩，降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # True for every monster ability: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile, sparrow, crab and hare declare).
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "buff_apply:rock_echo_stagger"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("rock_echo_goat",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.2,
                audience=EffectAudience.ENEMIES,
            ),
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
    _skill(
        "mane_crosswind_pounce",
        "鬃風佯撲",
        "以風屬性力量發動佯撲，造成物理傷害；命中後使對手短暫誤判動作，降低其命中率。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # True for every monster ability: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile, sparrow, crab, hare and goat declare).
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "buff_apply:mane_misdirection"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("fog_mane_lynx",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
            ),
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
    _skill(
        "mudfilm_guard",
        "泥膜收束",
        "收緊體表附著的泥膜，短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SELF,
        cost={"sp": 5},
        # A body action with no damage occurrence: this support shape has no
        # field use, so it stays combat-only (the damage-carrying monster
        # abilities above remain selectable outside combat).
        usable_out_of_combat=False,
        effects=["self_buff_apply:mudfilm_shell"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.SELF_ONLY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mudfilm_slime",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELF,
            ),
        ),
    ),
    _skill(
        "wax_pouch_slip",
        "滑蠟翻身",
        "把腹側薄蠟抹勻後靈巧翻身，短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SELF,
        cost={"sp": 6},
        # A body action with no damage occurrence: this support shape has no
        # field use, so it stays combat-only (the damage-carrying monster
        # abilities above remain selectable outside combat).
        usable_out_of_combat=False,
        effects=["self_buff_apply:wax_slip"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.SELF_ONLY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("wax_pouch_rat",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELF,
            ),
        ),
    ),
    _skill(
        "sticky_palm_grab",
        "黏掌抓扯",
        "以黏亮寬掌抓扯單一敵方目標，造成物理傷害；命中後使對手短暫失去動作節奏，降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 5},
        # True for every damage-carrying monster ability: the one written
        # ``usable_out_of_combat`` policy makes every damage-carrying ability
        # selectable outside combat, and "combat-only" names the action shape
        # and targeting, never this flag (settled 2026-10-10; same value the
        # delivered crocodile, sparrow, crab, hare, goat and lynx declare).
        usable_out_of_combat=True,
        # A body action, not magic: no element, so no magic tier and no
        # freeform eligibility. The school stays physical.
        effects=["damage:none:physical", "buff_apply:sticky_palm_drag"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("sticky_palm_goblin",),
        ),
        prerequisites=(),
        effect_policies=(
            # Occurrence 0 is the ordinary enemy strike.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
            ),
            # Occurrence 1 is the hit-dependent rider: the link is only
            # granted by a landed hit of occurrence 0, so a miss leaves the
            # struck enemy's agility untouched.
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
    _skill(
        "reservoir_guard",
        "蓄潮護膜",
        "以自身魔力讓頸側與背脊的薄水膜貼合鱗甲，短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SELF,
        cost={"mp": 12},
        # A body action with no damage occurrence: this support shape has no
        # field use, so it stays combat-only (the damage-carrying monster
        # abilities above remain selectable outside combat).
        usable_out_of_combat=False,
        element="water",
        effects=["self_buff_apply:reservoir_film"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.SELF_ONLY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("tide_devouring_crocodile",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.SELF,
            ),
        ),
    ),
    _skill(
        "ember_tusk_charge",
        "熱鬃衝撞",
        "以發熱的肩背鬃毛帶動身體衝撞單一敵方目標，造成火屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="fire",
        # The school stays physical and reads the actor's own physical attack;
        # the fire element follows the ordinary elemental rules and never
        # substitutes for the attack axis.
        effects=["damage:fire:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="fire",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ember_bristle_boar",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(
                coefficient=1.2,
                audience=EffectAudience.ENEMIES,
            ),
        ),
    ),
    _skill(
        "ember_bristle_sweep",
        "熱鬃橫掃",
        "甩動發熱的粗鬃橫掃周圍所有敵方目標，對每個目標造成火屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="fire",
        # Physical school on the actor's own attack axis, fire element. The
        # settlement rolls each routed recipient's own hit and mitigates with
        # that recipient's own defense, while the action pays both costs once.
        effects=["damage:fire:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="fire",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ember_bristle_boar",),
        ),
        prerequisites=(),
        effect_policies=(
            # Below the charge's coefficient: one wide motion is weaker per
            # recipient than a committed single-target impact.
            EffectPolicy(
                coefficient=0.8,
                audience=EffectAudience.ENEMIES,
            ),
        ),
    ),
    _skill(
        "spore_puff_bump",
        "孢粉頂撞",
        "以菌傘頂撞單一敵方目標，造成物理傷害；命中後揚起暗屬性孢粉，使對手短暫視線昏沉，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="dark",
        effects=["damage:dark:physical", "buff_apply:spore_haze"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("spore_cap_mushroom",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
    _skill(
        "quill_brace_ram",
        "固棘倒撞",
        "以土屬性力量硬化棘根後轉身以背倒撞單一敵方目標，造成物理傷害；出招時短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "self_buff_apply:quill_brace"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("moss_quill_porcupine",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
    _skill(
        "hollow_bat_bite",
        "空木吸咬",
        "以帶著暗屬性的門牙咬向單一敵方目標，造成物理傷害；命中時從咬口吸取少量血氣，轉為自身的生命。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="dark",
        effects=["damage:dark:physical", "gauge_transfer:hp:drain:fixed:4"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("hollow_tree_bat",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
                transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
            ),
        ),
    ),
    _skill(
        "hush_wing_swoop",
        "靜羽掠爪",
        "以風屬性力量收斂拍翼聲後掠爪攻擊單一敵方目標，造成物理傷害；出擊後藉風抬升，短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:hush_lift"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("hush_wing_owl",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
    _skill(
        "vine_thread_cast",
        "藤絲纏擲",
        "以前腳擲出摻著藤皮纖維的黏絲纏向單一敵方目標，造成物理傷害；命中後纏住腿腳，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:vine_snare"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("vine_net_spider",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "moss_crown_charge",
        "苔冠衝撞",
        "以土屬性力量硬化鹿角上的苔冠，衝撞單一敵方目標，造成土屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("moss_crown_stag",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "moss_crown_sweep",
        "苔冠橫掃",
        "甩動硬化的苔冠橫掃周圍所有敵方目標，對每個目標造成土屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("moss_crown_stag",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "mist_tongue_sip",
        "霧舌汲取",
        "以帶著水屬性力量的長舌拍擊單一敵方目標，造成物理傷害；命中時從對方身上汲走少量魔力，轉為自身的魔力。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="water",
        effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:4"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mist_spring_frog",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
                transfer=GaugeTransferPolicy(caster_recovery_share=1.0),
            ),
        ),
    ),
    _skill(
        "ember_skin_bite",
        "燃斑咬擊",
        "以火屬性力量讓皮膚斑點驟然發熱後咬向單一敵方目標，造成物理傷害；出招時短暫提高自身攻擊。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="fire",
        effects=["damage:fire:physical", "self_buff_apply:ember_skin"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="fire",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("warm_rock_salamander",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
    _skill(
        "grit_wing_strike",
        "揚礫撲擊",
        "藉風屬性力量俯衝撲擊單一敵方目標，造成物理傷害；命中後振翅掀起碎石與雪粒，使對手短暫看不準目標，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "buff_apply:grit_gust"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("bone_breaker_vulture",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "veil_scale_flutter",
        "鱗粉撲翅",
        "以帶著暗屬性鱗粉的翅膀撲打單一敵方目標，造成物理傷害；命中後抖落鱗粉，使對手手腳短暫發沉，降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 4},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="dark",
        effects=["damage:dark:physical", "buff_apply:veil_scale"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mist_lamp_moth",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "rime_fang_strike",
        "霜牙噬擊",
        "以冰屬性力量讓獠牙結霜，噬咬單一敵方目標，造成冰屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="ice",
        effects=["damage:ice:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="ice",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("rime_scale_serpent",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "rime_tail_lash",
        "霜尾橫掃",
        "甩動結霜的長尾橫掃周圍所有敵方目標，對每個目標造成冰屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="ice",
        effects=["damage:ice:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="ice",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("rime_scale_serpent",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "drum_wing_burst",
        "鼓翼驚飛",
        "以風屬性力量鼓起翼下氣流後撲擊單一敵方目標，造成物理傷害；出擊後順勢驚飛，短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:drum_burst"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("drum_wing_grouse",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
    _skill(
        "mud_pelt_slap",
        "泥甲尾擊",
        "以土屬性力量讓毛皮泥層緊實後，以寬尾拍擊單一敵方目標，造成物理傷害；出招時短暫提高自身防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "self_buff_apply:mud_pelt"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mud_dam_beaver",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
    _skill(
        "grit_claw_scrape",
        "揚砂爪刨",
        "以土屬性力量鬆動爪前土石後刨擊單一敵方目標，造成物理傷害；命中後揚起礦砂打在對手臉上，使對手短暫看不準目標，降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 2},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "buff_apply:ore_grit"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ore_vein_mole",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(
                coefficient=1.0,
                audience=EffectAudience.ENEMIES,
                requires_hit_from=0,
            ),
        ),
    ),
    _skill(
        "jaw_lock_bite",
        "鉗顎扳咬",
        "以顎部鉗住單一敵方目標猛力扳扭，造成物理傷害；命中後讓對手的護身架勢短暫鬆開，降低其防禦。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:jaw_wrench"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("cache_raider_wolverine",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "ore_crest_dive",
        "俯衝裂爪",
        "以風屬性力量把氣流聚到翼下，俯衝以鷹爪擊打單一敵方目標，造成風屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ore_nest_griffin",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "ore_crest_gale",
        "振翼風壓",
        "在低空猛振雙翼，以翼下風壓撞擊周圍所有敵方目標，對每個目標造成風屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("ore_nest_griffin",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "clod_ball_shove",
        "鏟頭滾球",
        "以土屬性力量壓實土球後，以鏟狀頭板頂撞單一敵方目標，造成物理傷害；命中後讓土球絆住對手腳步，短暫降低其敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical", "buff_apply:clod_stumble"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("clod_ball_beetle",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "dust_gallop_kick",
        "疾蹄踢擊",
        "以風屬性力量把氣流聚在四蹄周圍，人立而起以前蹄踢擊單一敵方目標，造成物理傷害；出招時短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 5},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:gale_hooves"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("dust_mane_horse",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
    _skill(
        "spear_beak_jab",
        "矛喙疾刺",
        "以彈直的長頸驅使長喙疾刺單一敵方目標，造成物理傷害；命中後甩起水花撲向對手臉上，短暫降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:canal_splash"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("sluice_spear_heron",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "lake_mound_bite",
        "碎顎咬合",
        "以土屬性力量讓四足陷進泥地撐住身軀，探出粗大的頭部以厚鈍如石的巨顎咬住單一敵方目標，造成土屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 12, "sp": 6},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("lake_mound_turtle",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "lake_mound_quake",
        "背甲震地",
        "撐起身軀把背甲猛力砸向地面，以土屬性力量讓泥地翻湧，對周圍每個敵方目標造成土屬性物理傷害。",
        SkillKind.ACTIVE,
        TargetSpec.AREA,
        cost={"mp": 16, "sp": 8},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="earth",
        effects=["damage:earth:physical"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="earth",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("lake_mound_turtle",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
        ),
    ),
    _skill(
        "mud_tail_flick",
        "甩尾濺泥",
        "撲向單一敵方目標以尾巴拍擊，造成物理傷害；命中後甩起濕泥糊在對手臉上，短暫降低其命中。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        effects=["damage:none:physical", "buff_apply:mud_fleck"],
        category=SkillCategory.MARTIAL_ARTS,
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("flat_leap_goby",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.9, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
        ),
    ),
    _skill(
        "wind_snatch_dive",
        "掠風啄擊",
        "以風屬性力量在翼下聚起側風，橫掠而下啄擊單一敵方目標，造成物理傷害；出招時短暫提高自身敏捷。",
        SkillKind.ACTIVE,
        TargetSpec.SINGLE,
        cost={"mp": 10, "sp": 3},
        # A damage-carrying ability: its field use is opening a fight, so it
        # stays selectable outside combat like the other monster strikes.
        usable_out_of_combat=True,
        element="wind",
        effects=["damage:wind:physical", "self_buff_apply:gull_updraft"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="wind",
        faction_constraint=FactionConstraint.ANY,
        eligibility=SkillEligibility(
            allowed_actor_kinds=("monster",),
            allowed_species=("mast_wind_gull",),
        ),
        prerequisites=(),
        effect_policies=(
            EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES),
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),
        ),
    ),
)
