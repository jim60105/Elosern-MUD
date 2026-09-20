"""Combat fixture grant sets and the combat-menu journey roles.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every payload ships verbatim."""

from __future__ import annotations

from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled
from web.browser_support.browser_fixtures_data.shipped_seed import (
    SHIPPED_COMBAT_LADDER_SKILL,
    SHIPPED_COMBAT_MONSTERS,
)
from web.browser_support.browser_fixtures_data.grafting import (
    SYNTH_INNATE_ATTACK_KEY,
)

#: Kit combat grant set: actives, passives, and the freeform ladder. The
#: ladder rides ``t_glowmire_bloom`` (its own element's mastery passive
#: ``t_glowmire_mastery`` is granted alongside), mirroring the shipped
#: wind-blade/mastery pairing without naming shipped skills. Ownership order
#: is the panel's intra-group row order: the borrowed-element group carries
#: the deep canopy cast ``t_ember_comet`` first (``grant_lineage`` closes its
#: prereq ``t_ember_burst`` in BEHIND it, the shipped fire tree's exact
#: two-row shape), the utility group carries the race-gate-disabled row
#: (a ``confer_skill_partial`` carrier requiring divine arts, which the kit's
#: only race lacks) BEFORE the NONE-shape cast carrier so the
#: disabled row is the frame's first focus in both modes.
SYNTH_COMBAT_ACTIVE_SKILLS = (
    "t_ember_comet",
    "t_glowmire_bloom",
    "t_cinder_cleave",
    "t_moss_veil",
    "t_rock_quietus",
    "t_cinder_breath",
)
SYNTH_COMBAT_PASSIVE_SKILLS = ("t_steady_stride", "t_glowmire_mastery")
SYNTH_COMBAT_LADDER_SKILL = "t_glowmire_bloom"
SYNTH_COMBAT_LADDER_LEVEL = 10
#: Kit debuff with a deterministic applied-modifier row (status panel).
SYNTH_COMBAT_DEBUFF_KEY = "t_ash_burn"
#: (object key, hp) pairs for the two living synth combat monsters.
SYNTH_COMBAT_MONSTERS = (("燼殼工蟲", 200), ("燼殼兵蟲", 200))


def combat_journey_values() -> dict:
    """The combat-menu journeys' skill roles for the current boot mode.

    Every role is a skill KEY plus the owned-order position that puts it at
    the start of its group/category frame:

    - ``attack_key``: the innate universal-attack seam row (identical key in
      both modes — the production seam, grafted under the synthetic install).
    - ``spell_key``: the first owned elemental spell, first skill of the
      first element sub-group (SINGLE target, borrows the first registered
      element so its sub-group shares the shipped first element's label).
    - ``prereq_key``: the prereq row ``grant_lineage`` closes in behind the
      spell, second in the same sub-group's ownership order.
    - ``ladder_key``: the mastery-entitled second element sub-group's active
      (the scale-step/AREA journey's cast target).
    - ``none_key``: the owned NONE-shape active the NONE-payload journey
      submits (enhancement in shipped mode; utility under the kit install).
    - ``none_category``: the ``SkillCategory`` value ``none_key`` lives in.
    - ``self_disabled_key``: the active the race gate disables for the
      fixture character (a divine-arts row the fixture race cannot cast), so
      the menu exposes it disabled with its reason.
    - ``self_disabled_category``: the ``SkillCategory`` value
      ``self_disabled_key`` lives in (the utility group under the kit
      install; the divine-mystery category in shipped mode).
    - ``spell_element`` / ``ladder_element``: the ELEMENT_REGISTRY keys the
      sub-groups of the elemental category are named after (the spell borrows
      the shipped first element in both modes; the ladder's element differs).
    - ``element_group_order``: the elemental sub-group keys in the live
      ELEMENT_REGISTRY declaration order the panel sorts by (the borrowed
      shipped element is grafted after the kit's own rows under the synthetic
      install, so the pair is reversed relative to shipped mode).
    - ``spell_group_index`` / ``ladder_group_index``: the positions of those
      sub-groups inside the elemental category frame under that order.
    - ``spell_element_label``: the display label the spell's sub-group renders.
    - ``ladder_mp_cost``: the ladder's base MP cost (the detail pane's 威力
      scale rows render the ascending multiples of this value).
    - ``enhancement_key``: the owned active of the enhancement category's
      null-keyed sub-group (NONE-shape in shipped mode).
    - ``engage_target``: the first living combat monster in the start room
      (the journeys' ``engage`` argument).
    """
    if synth_mode_enabled():
        return {
            "attack_key": SYNTH_INNATE_ATTACK_KEY,
            "spell_key": "t_ember_comet",
            "prereq_key": "t_ember_burst",
            "ladder_key": "t_glowmire_bloom",
            "none_key": "t_cinder_breath",
            "none_category": "utility",
            "self_disabled_key": "t_rock_quietus",
            "self_disabled_category": "utility",
            "spell_element": "fire",
            "ladder_element": "t_glowmire",
            # The kit install registers t_glowmire first; the borrowed shipped
            # ``fire`` row is grafted in afterwards, so the registry order is
            # reversed relative to shipped mode.
            "element_group_order": ("t_glowmire", "fire"),
            "spell_group_index": 1,
            "ladder_group_index": 0,
            "spell_element_label": "火",
            "ladder_mp_cost": 14,
            "enhancement_key": "t_moss_veil",
            "engage_target": SYNTH_COMBAT_MONSTERS[0][0],
        }
    return {
        "attack_key": SHIPPED_INNATE_ATTACK_KEY,
        "spell_key": SHIPPED_COMBAT_SPELL_KEY,
        "prereq_key": SHIPPED_COMBAT_SPELL_PREREQ_KEY,
        "ladder_key": SHIPPED_COMBAT_LADDER_SKILL,
        "none_key": SHIPPED_COMBAT_NONE_SKILL,
        "none_category": "enhancement",
        "self_disabled_key": SHIPPED_COMBAT_DISABLED_SKILL,
        "self_disabled_category": "divine_mystery",
        "spell_element": "fire",
        "ladder_element": "wind",
        "element_group_order": ("fire", "wind"),
        "spell_group_index": 0,
        "ladder_group_index": 1,
        "spell_element_label": "火",
        "ladder_mp_cost": 14,
        "enhancement_key": SHIPPED_COMBAT_NONE_SKILL,
        "engage_target": SHIPPED_COMBAT_MONSTERS[0][0],
    }


#: Combat-menu shipped-mode roles (read only when the synthetic flag is OFF).
SHIPPED_INNATE_ATTACK_KEY = "basic_attack"
SHIPPED_COMBAT_SPELL_KEY = "fire_ball"
SHIPPED_COMBAT_SPELL_PREREQ_KEY = "fire_arrow"
SHIPPED_COMBAT_NONE_SKILL = "concentration"
SHIPPED_COMBAT_DISABLED_SKILL = "status_disguise"
