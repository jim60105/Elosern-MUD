"""Hand-written quest template pool for offline ScenarioDirector degradation (design §7.5/D6).

Every template is a pre-validated ``QuestBlueprint`` value referencing only
permanent world content: known monster tiers, placed anchors, grid
coordinates, and known item keys. Templates are written as proposal values, not
runtime definitions, so they flow through the exact same compile boundary as
LLM output. The first entry is an instance-layer bound-target scene so a
disabled-profile ``guild request`` resolves to a quest whose scene change 21's
SceneBuilder can materialize (design D9); the later entries use only permanent
rooms.

The pool is indexed for context matching (rank, quest type, issuer branch,
anchor) so ``generate_quest_blueprint``'s degraded draw honors the request
context. Import direction is pinned one-way: this module imports the proposal
model from ``scenario_director``, and the director reads the pool through a
lazy accessor so no module-level import cycle forms at startup.
"""

from world.ai.scenario_director import (
    BlueprintFailure,
    BlueprintItemQuantity,
    BlueprintLocation,
    BlueprintNpcReq,
    BlueprintObjective,
    BlueprintPersona,
    BlueprintPortrait,
    BlueprintReward,
    BlueprintStage,
    QuestBlueprint,
)

QUEST_TEMPLATE_POOL: tuple[QuestBlueprint, ...] = (
    QuestBlueprint(
        name="討伐林間盜匪",
        quest_type="討伐",
        rank="F",
        issuer="guild_branch_altoria",
        stages=(
            BlueprintStage(
                index=0,
                objective=BlueprintObjective(
                    kind="defeat",
                    quantity=1,
                    monster_tier=None,
                ),
                location=BlueprintLocation(
                    layer="instance",
                    archetype="forest_path",
                    anchor_key=None,
                    anchor_near="capital_altoria",
                    xyz=None,
                    scene_sentence="王都近郊的林間小徑樹影搖曳，一名盜匪的身影在樹叢間若隱若現。",
                ),
                npc_reqs=(
                    BlueprintNpcReq(
                        role="bandit",
                        tier="bandit",
                        disposition=None,
                        display_name="黑鬍",
                        title="林間盜匪首領",
                        age=35,
                        apparent_age=35,
                        portrait=BlueprintPortrait(stable_key="forest_bandit_chief"),
                        persona=BlueprintPersona(
                            identity_public="盤踞王都近郊林間小徑的盜匪首領，三十五歲，手下聚著十來名走投無路的亡命之徒。",
                            identity_hidden="曾是王都城門的守備兵，十年前替同袍頂下失職之罪而遭逐出軍中。",
                            appearance="身材粗壯的人類男子，滿臉濃密的黑色鬍鬚，左眉有一道舊刀疤；披著沾滿泥漬的皮甲與深綠斗篷，腰間掛著一把磨得發亮的短斧。",
                            personality="粗豪而多疑，講究手下的規矩與分贓公平；不屑對手無寸鐵的弱者動手，對背叛者卻絕不留情。",
                            speech_style="嗓音粗啞，句子短而直接，常帶著軍中發號施令般的口吻；習慣稱陌生人為「小子」，談判時愛先冷笑一聲再開價。",
                            life_story="出身王都外城的貧民巷，年少從軍、駐守城門。被逐出軍中後流落林間，憑著昔日的戰技收攏一批落魄者，在通往王都的林間小徑劫掠商旅，成了公會懸賞名單上的人物。",
                            habit="每晚清點完戰利品，總會獨自坐在營火旁，用磨刀石慢慢打磨那把短斧。",
                            social_connection="與一名仍在城門當差的老守備兵私下往來，偶爾從他口中探得巡邏的路線與時辰。",
                        ),
                    ),
                ),
            ),
        ),
        reward=BlueprintReward(
            copper=50,
            items=(BlueprintItemQuantity("healing_potion", 1),),
            merit=25,
        ),
        failure=BlueprintFailure(deadline_hours=None, conditions=()),
    ),
    QuestBlueprint(
        name="討伐低階魔物",
        quest_type="討伐",
        rank="F",
        issuer="guild_branch_altoria",
        stages=(
            BlueprintStage(
                index=0,
                objective=BlueprintObjective(
                    kind="defeat",
                    quantity=1,
                    monster_tier="low",
                ),
                location=BlueprintLocation(
                    layer="anchor",
                    archetype="forest_path",
                    anchor_key="capital_altoria",
                    scene_sentence="王都近郊的林間小徑，樹影搖曳，魔物的蹤跡若隱若現。",
                ),
            ),
        ),
        reward=BlueprintReward(
            copper=50,
            items=(BlueprintItemQuantity("healing_potion", 1),),
            merit=25,
        ),
        failure=BlueprintFailure(deadline_hours=None, conditions=()),
    ),
    QuestBlueprint(
        name="探查王都廣場",
        quest_type="探索",
        rank="F",
        issuer="guild_branch_altoria",
        stages=(
            BlueprintStage(
                index=0,
                objective=BlueprintObjective(
                    kind="reach_location",
                    quantity=1,
                ),
                location=BlueprintLocation(
                    layer="anchor",
                    archetype="city_street",
                    anchor_key="capital_altoria",
                    scene_sentence="聖潔王都的中央廣場，人聲鼎沸，攤販與旅人來來往往。",
                ),
            ),
        ),
        reward=BlueprintReward(
            copper=50,
            items=(),
            merit=25,
        ),
        failure=BlueprintFailure(deadline_hours=72, conditions=()),
    ),
)
