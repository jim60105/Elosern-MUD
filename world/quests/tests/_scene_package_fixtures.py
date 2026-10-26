"""Synthetic scene-package payload builders shared by the package tests.

Every builder resolves its identifiers through the live registries rather than
naming shipped keys, and the prose is generic synthetic text, so the package
tests stay data-echo free.
"""

from world.quests.tests._card_fixtures import occupant_card_record
from world.quests.tests._compile_helpers import (
    _anchor_key,
    _archetype_key,
    _issuer_key,
    _tier_key,
)

LONG_PROSE = "南門的相遇，旅人在此停下腳步，等著一個承諾被實現。"


def topic_scene(topic_id: str, host_line: str, *, actor_line: str = LONG_PROSE) -> dict:
    """One complete actor-first synthetic scene for a generated topic."""
    return {
        "scene_id": f"{topic_id}_scene",
        "revision": "r1",
        "lines": [
            {"kind": "speech", "speaker": "actor", "text": actor_line},
            {"kind": "speech", "speaker": "host", "text": host_line},
        ],
    }


def topic(topic_id: str, keyword: str, text: str, **overrides) -> dict:
    """One complete synthetic generated topic declaration."""
    entry = {
        "topic_id": topic_id,
        "keyword": keyword,
        "label": keyword,
        "fallback": topic_scene(topic_id, text),
    }
    entry.update(overrides)
    return entry


def characterization(tag: str) -> dict:
    return {
        "display_name": f"測試住民{tag}",
        "age": 30,
        "apparent_age": 30,
        "portrait": {"stable_key": f"test_portrait_{tag}"},
        "persona": occupant_card_record(tag),
    }


def anchor_locator(**overrides) -> dict:
    locator = {
        "layer": "anchor",
        "anchor_key": _anchor_key(),
        "archetype": _archetype_key(),
        "anchor_near": None,
        "xyz": None,
        "scene_sentence": LONG_PROSE,
    }
    locator.update(overrides)
    return locator


def issuer_capabilities(content_key: str) -> list[dict]:
    """The direct capability declaration a commission role must author.

    A generated commission role declares exactly one person-bound quest_issuer
    whose issuer_key is its commission content key; the scoped service_id is
    supplied by the deterministic boundary, so the fixture never authors it.
    """
    return [
        {
            "type": "quest_issuer",
            "kwargs": {"issuer_key": content_key},
            "binding": {"kind": "person"},
        }
    ]


def issuer_plan(content_key: str, service_id: str = "t_generated_issuer"):
    """The validated plan ``provision_scoped_issuer`` now requires."""
    from world.rules.npc_capabilities import (
        capability,
        person_bound,
        validate_capabilities,
    )

    return validate_capabilities(
        [
            capability(
                "quest_issuer",
                binding=person_bound(),
                service_id=service_id,
                issuer_key=content_key,
            )
        ]
    )


def role(role_id: str, **overrides) -> dict:
    entry = {
        "role_id": role_id,
        "tier": _tier_key(),
        "disposition": None,
        "characterization": characterization(role_id),
        "conversable": True,
        "retention": anchor_locator(archetype=None, scene_sentence=None),
    }
    entry.update(overrides)
    return entry


def phase(phase_id, conditions, *, topics=()) -> dict:
    return {
        "phase_id": phase_id,
        "conditions": list(conditions),
        "greeting": f"{LONG_PROSE}{phase_id}",
        "topics": list(topics),
        "freeform_situation": LONG_PROSE,
        "freeform_goals": LONG_PROSE,
        "offline_response": LONG_PROSE,
    }


def dialogue(role_id: str, **overrides) -> dict:
    entry = {
        "role_id": role_id,
        "initial_phase": "searching",
        "phases": [
            phase("searching", [{"default": True}]),
            # The reunion acknowledgment phase: selected once the exclusive
            # result is committed and before the closure interaction advances
            # to everyday content (escort-rendezvous §7).
            phase(
                "acknowledgment",
                [{"reunion": True}, {"closure": False}],
                topics=[topic("reunion", "重逢", LONG_PROSE)],
            ),
            phase(
                "everyday",
                [{"closure": True}],
                topics=[topic("status", "近況", LONG_PROSE)],
            ),
        ],
    }
    entry.update(overrides)
    return entry


def quest_payload(*, issuer: str, merit: int = 0, npc_req=None) -> dict:
    return {
        "name": "尋找母親",
        "quest_type": "探索",
        "rank": "F",
        "issuer": issuer,
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "reach_location", "quantity": 1},
                "location_req": anchor_locator(),
                "npc_req": list(npc_req or []),
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": merit},
        "failure": {"deadline_hours": None, "conditions": []},
    }


def package(**overrides) -> dict:
    payload = {
        "display_name": "南門的相遇",
        "source_id": "synthetic-package-source",
        "quest": quest_payload(issuer="mother"),
        "roles": [
            role("mother", capabilities=issuer_capabilities("story_mother")),
            role("daughter"),
        ],
        "relationships": [
            {"from_role": "mother", "to_role": "daughter", "kind": "parent_child"}
        ],
        "knowledge": [
            {
                "role_id": "mother",
                "claim_id": "separation",
                "text": LONG_PROSE,
                "provenance": {"kind": "role_owner", "ref": "mother"},
            },
            {
                "role_id": "daughter",
                "claim_id": "seeking",
                "text": LONG_PROSE,
                "provenance": {"kind": "role_owner", "ref": "daughter"},
            },
        ],
        "encounters": [
            {
                "scene_id": "south_gate",
                "role_ids": ["daughter"],
                "locator": anchor_locator(),
                "prerequisites": [],
            },
            {
                "scene_id": "market",
                "role_ids": ["mother"],
                "locator": anchor_locator(),
                "prerequisites": [],
            },
        ],
        "dialogue": [dialogue("mother"), dialogue("daughter")],
        "commissions": [{"role_id": "mother", "issuer_content_key": "story_mother"}],
    }
    payload.update(overrides)
    return payload


def guild_package(**overrides) -> dict:
    # A guild-branch package issues no commission, so no role declares a
    # capability: the commission role's declaration belongs to the symbolic
    # path only.
    return package(
        quest=quest_payload(issuer=_issuer_key()),
        commissions=[],
        roles=[role("mother"), role("daughter")],
        **overrides,
    )
