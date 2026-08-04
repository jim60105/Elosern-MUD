"""Hand-written quest template pool for offline ScenarioDirector degradation (design §7.5/D6).

Every template is a pre-validated ``QuestBlueprint`` value referencing only
permanent world content: known monster tiers, placed anchors, grid
coordinates, and known item keys. Templates are written as proposal values, not
runtime definitions, so they flow through the exact same compile boundary as
LLM output; instance-layer stages are deliberately absent because an instance
scene cannot be completed until change 21's SceneBuilder binds a room.

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
    BlueprintObjective,
    BlueprintReward,
    BlueprintStage,
    QuestBlueprint,
)

QUEST_TEMPLATE_POOL: tuple[QuestBlueprint, ...] = (
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
