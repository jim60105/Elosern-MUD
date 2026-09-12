"""神之秘法線 (divine arts line): acts that deliberately break the balance
the other five lines rely on, plus one ownership-gated signature act.

The three `C7a` acts are hand-built directly as `(SkillDef, SexualActDef)`
pairs — not via `_act_family()` — because none of them wants the ordinary
pleasure/counter/event triad that `_act_family()`'s fixed row shape always
attaches (divine-sexual-arts-reuse design D-1):

- 絕頂律令 sets every target's pleasure to its ceiling through two chained
  ``_apply_pleasure_gain`` calls (design D-2);
- 時姦 stages three climax extensions in one cast (design D-3);
- 神域搾取 moves a target's pleasure into the caster's MP/SP/HP (design D-4).

The four `C7b` acts are hand-built for the same reason — each needs one
bespoke mutator call with no existing effect-string shape, delivered through
its own new general-purpose effect prefix
(divine-sexual-arts-mutators design D-1):

- 感度創世 saturates every resolvable body part via
  ``divine_saturate_sensitivity:`` → ``SexualState.saturate_sensitivity()``;
- 恥辱剝奪 pins shame at 成癮 via ``divine_clamp_shame:`` →
  ``SexualState.clamp_shame_to("成癮")``, eagerly rejecting a ``Monster``
  target (design D-3);
- 絕對從屬 plants a permanent auto-comply mark keyed by the caster's unique
  database id via ``divine_mark_submission:`` →
  ``SexualState.mark_submission(str(actor.id))`` (design D-5);
- 無垢回歸 restores the target's virgin flag via ``divine_restore_purity:``
  → ``SexualState.restore_purity()``, bypassing the one-way public setter
  without weakening its shipped guarantee (design D-4).

The eighth pair is ``divine_sexual_arts`` (神之秘法：性愛系統), the legacy
main-registry skill integrated into the catalogue by
``integrate-divine-sexual-arts-catalog``. It is hand-built for the same
structural reason (no pleasure/counter/event triad: its single effect is a
target-scoped ``sexual_event_target:stimulus_applied`` string) and carries
``ownership_gated=True`` on its ``SexualActDef``: unlike the seven counter-free
divine acts above, its unlock state is supplied only by actual base ownership
(a signature skill — shipped data names exactly one owner, the
``yuna_darknight`` preset), so neither the counter branch nor the mastery
blanket of ``unlocked_act_keys_for`` may derive it. It has no counters and no
``pleasure:`` effect of its own, which is why it could not ride the
``_act_family()`` row format even before the gating decision.

Every row declares `requires_divine_arts=True` (so the shipped
``_step1_divine_arts_gate`` and ``RaceProfile.can_use_divine_arts`` are the
line's containment), `unlock={}` (counter thresholds do not apply — design doc
§1.1), `target_part=None` (神之秘法 is one of `_builder.py`'s two
`_PARLESS_LINES`), `resistible=True` (ordinary hostile-act convention — design
D-6), and no counters (design doc §1.1: "Counter thresholds do not apply").
All eight are `TargetSpec.SINGLE` except 絕頂律令, which is `TargetSpec.AREA`.

The `SexualActDef` pleasure fields are populated with clearly-documented
placeholder values: none of the eight acts declares a `pleasure:` effect, so
no code path ever reads `base_pleasure`, `actor_part`, or
`actor_pleasure_ratio` for these rows.
"""

from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)
from world.skills.sexual_acts._builder import SexualActDef

DIVINE_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = (
    (
        SkillDef(
            key="divine_extreme_climax_command",
            label="絕頂律令",
            description="以神之律令，無視一切加乘，直接將目標的快感推至頂點。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.AREA,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_pleasure_max:絕頂律令"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_extreme_climax_command",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        SkillDef(
            key="divine_timed_copulation",
            label="時姦",
            description="以神之律令操弄時間，使目標的絕頂接連不斷地延續。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_climax_extension_stage:3"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_timed_copulation",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        SkillDef(
            key="divine_realm_drain",
            label="神域搾取",
            description="以神之律令，將目標累積的快感直接化為自身的魔力、體力與生命力。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_drain:神域搾取"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_realm_drain",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        SkillDef(
            key="divine_sensitivity_creation",
            label="感度創世",
            description="以神之律令重塑目標的感官，使每一處肌膚都達到敏感異常的境地。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_saturate_sensitivity:感度創世"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_sensitivity_creation",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        SkillDef(
            key="divine_shame_deprivation",
            label="恥辱剝奪",
            description="以神之律令奪走目標的羞恥之心，使其陷入永恆的沉淪。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_clamp_shame:恥辱剝奪"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_shame_deprivation",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        SkillDef(
            key="divine_absolute_submission",
            label="絕對從屬",
            description="以神之律令在目標心中烙下絕對服從的印記，此生無法違抗施術者的意圖。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_mark_submission:絕對從屬"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_absolute_submission",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        SkillDef(
            key="divine_purity_restoration",
            label="無垢回歸",
            description="以神之律令逆轉時光，使目標的身體回歸未受玷污的純淨狀態。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_restore_purity:無垢回歸"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_purity_restoration",
            unlock={},
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        ),
    ),
    (
        # The integrated legacy signature act (integrate-divine-sexual-arts-
        # catalog design D-1/D-6): hand-built like the other seven, but
        # ownership_gated so no derivation branch ever unlocks it — only a
        # kit that actually names the key (the yuna_darknight preset) owns it.
        SkillDef(
            key="divine_sexual_arts",
            label="神之秘法：性愛系統",
            description="以神之秘法引導的性愛技法，直接刺激目標的感官與慾望。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            # Target-scoped stimulus (D-9 semantics now carried by the prefix):
            # the acting entity is never a recipient of its own cast.
            effects=["sexual_event_target:stimulus_applied"],
            category=SkillCategory.SEXUAL_ACT,
            group="神之秘法",
            requires_divine_arts=True,
        ),
        SexualActDef(
            key="divine_sexual_arts",
            unlock={},
            # Placeholder (same discipline as the other seven rows): this act
            # declares no pleasure: effect, so no code path reads this field.
            base_pleasure=1,
            actor_part=None,
            target_part=None,
            actor_pleasure_ratio=0.0,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
            # Signature-skill gate: derivation branches skip this row.
            ownership_gated=True,
        ),
    ),
)
