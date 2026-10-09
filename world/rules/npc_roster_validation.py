"""Full-roster validation gate for shipped NPC sources and persona profiles.

Validates the complete shipped NPC roster before world synchronization at server
start: derives shipped sources from live registries and files, checks bidirectional
inventory equality, verifies compact cards and voice lines for place hosts, guild
examiners, companion partner presets, quest template occupants, and import
examples, and flags orphan profiles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Mapping

if TYPE_CHECKING:
    from typeclasses.npcs import NPC
    from world.lore.guild import GuildRank
    from world.lore.npc_profiles.inventory import NpcSource
    from world.lore.npc_profiles.shape import NpcProfile
    from world.lore.player_presets import PlayerPreset
    from world.lore.settlements.places import PlaceDefinition


class NpcRosterError(Exception):
    """Raised when the shipped NPC roster fails validation, listing all violations."""

    def __init__(self, violations: list[str]) -> None:
        self.violations: tuple[str, ...] = tuple(violations)
        super().__init__(
            f"Shipped NPC roster validation failed with {len(violations)} violation(s):\n"
            + "\n".join(f"- {v}" for v in violations)
        )


def derive_shipped_sources(
    *,
    places: Mapping[str, PlaceDefinition] | None = None,
    dialogue_rows: Mapping[str, Any] | None = None,
    guild_ranks: Mapping[str, GuildRank] | None = None,
    player_presets: Mapping[str, PlayerPreset] | None = None,
    quest_templates: Iterable[Any] | None = None,
    examples_dir: Path | None = None,
    adventurers: Mapping | None = None,
) -> frozenset[tuple[str, str]]:
    """Derive the complete set of shipped NPC source (kind, key) pairs.

    Returns a frozenset of ``(kind, key)`` tuples corresponding to the sources
    defined across the places registry, dialogue tables, guild rank examiners,
    starting companion declarations, quest template occupants, and shipped import
    examples.
    """
    if places is None:
        from world.lore.settlements.places import PLACE_REGISTRY

        places = PLACE_REGISTRY
    if adventurers is None:
        from world.lore.guild_adventurers import ADVENTURER_REGISTRY

        adventurers = ADVENTURER_REGISTRY
    if dialogue_rows is None:
        from world.lore.dialogue import DIALOGUE_ROWS

        dialogue_rows = DIALOGUE_ROWS
    if guild_ranks is None:
        from world.lore.guild import GUILD_RANK_REGISTRY

        guild_ranks = GUILD_RANK_REGISTRY
    if player_presets is None:
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        player_presets = PLAYER_PRESET_REGISTRY
    if quest_templates is None:
        raise ValueError("quest_templates must be supplied by the composition root or caller")
    elif not isinstance(quest_templates, tuple):
        quest_templates = tuple(quest_templates)
    if examples_dir is None:
        import world.imports.examples as _examples_pkg

        examples_dir = Path(_examples_pkg.__file__).resolve().parent

    sources: set[tuple[str, str]] = set()

    for place in places.values():
        if place.service_id is not None:
            sources.add(("place_host", place.service_id))

    for key in dialogue_rows:
        sources.add(("dialogue_table", key))

    for key in guild_ranks:
        sources.add(("guild_examiner", key))
    for key in adventurers:
        sources.add(("persistent_adventurer", key))

    for preset in player_presets.values():
        for companion in preset.starting_companions:
            sources.add(("starting_companion", f"{preset.key}:{companion.preset_key}"))

    for template in quest_templates:
        for stage in template.stages:
            for pos in range(len(stage.npc_reqs)):
                sources.add(
                    ("quest_template_occupant", f"{template.name}:{stage.index}:{pos}")
                )

    for path in examples_dir.glob("*.json"):
        sources.add(("import_example", path.stem))

    return frozenset(sources)


def validate_npc_roster(
    *,
    places: Mapping[str, PlaceDefinition] | None = None,
    dialogue_rows: Mapping[str, Any] | None = None,
    guild_ranks: Mapping[str, GuildRank] | None = None,
    player_presets: Mapping[str, PlayerPreset] | None = None,
    quest_templates: Iterable[Any] | None = None,
    examples_dir: Path | None = None,
    profile_registry: Mapping[str, NpcProfile] | None = None,
    inventory: Iterable[NpcSource] | None = None,
    adventurers: Mapping | None = None,
) -> None:
    """Validate the complete shipped NPC roster and raise NpcRosterError on failure.

    All checks are performed and all violations are collected together:
    1. Bidirectional inventory equality between derived sources and inventory rows.
    2. Place hosts resolve to profiles with valid compact cards.
    3. Guild examiners resolve to profiles with valid compact cards and no voice lines.
    4. Dialogue tables are answered by exactly one hosted place; scripted hosts author
       a misunderstanding reply and no profile greeting.
    5. Starting companion partner presets provide speech_style, greeting, and a valid
       derived card with maximum-length synthetic owner.
    6. Quest template occupants carry personas with valid compact cards and pass characterization.
    7. Shipped import examples validate cleanly as NPC character records.
    8. Every profile in profile_registry is referenced by a hosted place or examiner rank.
    """
    if places is None:
        from world.lore.settlements.places import PLACE_REGISTRY

        places = PLACE_REGISTRY
    if adventurers is None:
        from world.lore.guild_adventurers import ADVENTURER_REGISTRY

        adventurers = ADVENTURER_REGISTRY
    if dialogue_rows is None:
        from world.lore.dialogue import DIALOGUE_ROWS

        dialogue_rows = DIALOGUE_ROWS
    if guild_ranks is None:
        from world.lore.guild import GUILD_RANK_REGISTRY

        guild_ranks = GUILD_RANK_REGISTRY
    if player_presets is None:
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        player_presets = PLAYER_PRESET_REGISTRY
    if quest_templates is None:
        raise ValueError("quest_templates must be supplied by the composition root or caller")
    elif not isinstance(quest_templates, tuple):
        quest_templates = tuple(quest_templates)
    if examples_dir is None:
        import world.imports.examples as _examples_pkg

        examples_dir = Path(_examples_pkg.__file__).resolve().parent
    if profile_registry is None:
        from world.lore.npc_profiles import NPC_PROFILE_REGISTRY

        profile_registry = NPC_PROFILE_REGISTRY
    if inventory is None:
        from world.lore.npc_profiles.inventory import NPC_SOURCE_INVENTORY

        inventory = NPC_SOURCE_INVENTORY

    from typeclasses.npcs import NPC
    from world.imports.validate import validate_character
    from world.lore.npc_card import NpcCardError, normalize_card
    from world.lore.npc_card import normalize_offline_greeting
    from world.lore.player_presets import derive_companion_card
    from world.quests.characterization import (
        characterize_errors,
        race_lifespan_upper_bound,
    )
    from world.rules.creation_wizard import NAME_MAX_LENGTH

    violations: list[str] = []
    referenced_profiles: set[str] = set()
    inventory = tuple(inventory)

    # 1. Inventory equality check (both directions)
    actual_sources = derive_shipped_sources(
        places=places,
        dialogue_rows=dialogue_rows,
        guild_ranks=guild_ranks,
        player_presets=player_presets,
        quest_templates=quest_templates,
        examples_dir=examples_dir,
        adventurers=adventurers,
    )
    inventory_sources = {(row.kind, row.key) for row in inventory}
    if len(inventory_sources) != len(inventory):
        violations.append("NPC source inventory contains duplicate source assignments")

    missing_from_inventory = sorted(actual_sources - inventory_sources)
    for kind, key in missing_from_inventory:
        violations.append(
            f"source kind={kind!r} key={key!r} is present in registries but missing from inventory"
        )

    stale_in_inventory = sorted(inventory_sources - actual_sources)
    for kind, key in stale_in_inventory:
        violations.append(
            f"source kind={kind!r} key={key!r} is present in inventory but missing from registries"
        )

    # Persistent people have distinct profiles and both offline reply paths.
    person_profiles: set[str] = set()
    other_profiles = {
        place.host_profile_key for place in places.values() if place.service_id is not None
    } | {rank.examiner_profile_key for rank in guild_ranks.values()}
    for person_key, person in adventurers.items():
        profile_key = person.profile_key
        referenced_profiles.add(profile_key)
        label = f"source kind='persistent_adventurer' key={person_key!r} profile {profile_key!r}"
        if profile_key in person_profiles or profile_key in other_profiles:
            violations.append(f"{label} must have a distinct normal-person profile")
        person_profiles.add(profile_key)
        profile = profile_registry.get(profile_key)
        if profile is None:
            violations.append(f"{label} references missing profile")
            continue
        assignments = [row for row in inventory
                       if row.kind == "persistent_adventurer" and row.key == person_key]
        if len(assignments) != 1 or (
            assignments[0].profile_key, assignments[0].age, assignments[0].apparent_age
        ) != (profile_key, profile.age, profile.apparent_age):
            violations.append(f"{label} has missing or stale profile/age inventory assignment")
        try:
            normalize_card(profile.card.to_record())
        except (NpcCardError, ValueError) as err:
            violations.append(f"{label} has invalid card: {err}")
        for field in ("age", "apparent_age"):
            value = getattr(profile, field)
            if type(value) is not int or not 0 <= value <= 10000:
                violations.append(f"{label} has invalid {field}")
        for field in ("greeting", "misunderstood"):
            value = getattr(profile.voice, field)
            if not isinstance(value, str) or not value.strip():
                violations.append(f"{label} missing {field}")
                continue
            try:
                normalize_offline_greeting(value)
            except (NpcCardError, ValueError) as err:
                violations.append(f"{label} invalid {field}: {err}")

    # 2. Place hosts: must resolve to a valid profile with a valid compact card
    for place in places.values():
        if place.service_id is None:
            continue
        profile_key = place.host_profile_key
        if not profile_key:
            violations.append(
                f"source kind='place_host' key={place.service_id!r} has no host_profile_key"
            )
            continue
        referenced_profiles.add(profile_key)
        profile = profile_registry.get(profile_key)
        if profile is None:
            violations.append(
                f"source kind='place_host' key={place.service_id!r} references missing profile {profile_key!r}"
            )
            continue
        try:
            normalize_card(profile.card.to_record())
        except (NpcCardError, ValueError) as err:
            violations.append(
                f"source kind='place_host' key={place.service_id!r} profile {profile_key!r} has invalid card: {err}"
            )

    # 3. Guild examiners: must resolve to a valid profile with a valid compact card and no voice lines
    for rank_key, rank in guild_ranks.items():
        profile_key = rank.examiner_profile_key
        if not profile_key:
            violations.append(
                f"source kind='guild_examiner' key={rank_key!r} has no examiner_profile_key"
            )
            continue
        referenced_profiles.add(profile_key)
        profile = profile_registry.get(profile_key)
        if profile is None:
            violations.append(
                f"source kind='guild_examiner' key={rank_key!r} references missing profile {profile_key!r}"
            )
            continue
        try:
            normalize_card(profile.card.to_record())
        except (NpcCardError, ValueError) as err:
            violations.append(
                f"source kind='guild_examiner' key={rank_key!r} profile {profile_key!r} has invalid card: {err}"
            )
        if profile.voice.greeting is not None or profile.voice.misunderstood is not None:
            violations.append(
                f"source kind='guild_examiner' key={rank_key!r} profile {profile_key!r} "
                "authors voice lines; examiners do not speak"
            )

    # 4. Dialogue tables & scripted hosts
    # Map dialogue keys to hosted places
    table_hosts: dict[str, list[PlaceDefinition]] = {tk: [] for tk in dialogue_rows}
    scripted_hosts: list[PlaceDefinition] = []

    for place in places.values():
        if place.service_id is None:
            continue
        for k, v in place.authored_kwargs:
            if k == "dialogue_key":
                scripted_hosts.append(place)
                if v in table_hosts:
                    table_hosts[v].append(place)
                else:
                    violations.append(
                        f"source kind='place_host' key={place.service_id!r} "
                        f"references unknown dialogue table {v!r}"
                    )

    # Check cardinality for each dialogue table
    for table_key in sorted(dialogue_rows):
        hosts = table_hosts[table_key]
        if len(hosts) == 0:
            violations.append(
                f"source kind='dialogue_table' key={table_key!r} is answered by 0 hosted places"
            )
        elif len(hosts) > 1:
            host_ids = [h.service_id for h in hosts]
            violations.append(
                f"source kind='dialogue_table' key={table_key!r} is answered by {len(hosts)} "
                f"hosted places: {host_ids!r}"
            )

    # Validate voice lines independently for EVERY scripted host
    for host in scripted_hosts:
        profile_key = host.host_profile_key
        if not profile_key:
            continue
        profile = profile_registry.get(profile_key)
        if profile is None:
            continue
        if not profile.voice.misunderstood or not profile.voice.misunderstood.strip():
            violations.append(
                f"source kind='place_host' key={host.service_id!r} profile {profile_key!r} "
                "missing misunderstood reply"
            )
        if profile.voice.greeting is not None:
            violations.append(
                f"source kind='place_host' key={host.service_id!r} profile {profile_key!r} "
                "authors a greeting; table greeting is the single source for hosts"
            )

    # 5. Starting companions: partner preset resolution, speech_style/greeting, derived card
    for preset_key, preset in player_presets.items():
        for companion in preset.starting_companions:
            source_key = f"{preset_key}:{companion.preset_key}"
            partner = player_presets.get(companion.preset_key)
            if partner is None:
                violations.append(
                    f"source kind='starting_companion' key={source_key!r} "
                    f"partner preset {companion.preset_key!r} is not registered"
                )
                continue

            if (
                not partner.persona.speech_style
                or not partner.persona.speech_style.strip()
            ):
                violations.append(
                    f"source kind='starting_companion' key={source_key!r} "
                    f"partner preset {companion.preset_key!r} missing speech_style"
                )
            if not partner.persona.greeting or not partner.persona.greeting.strip():
                violations.append(
                    f"source kind='starting_companion' key={source_key!r} "
                    f"partner preset {companion.preset_key!r} missing greeting"
                )

            synthetic_owner = "測" * NAME_MAX_LENGTH
            try:
                card_dict = derive_companion_card(
                    partner, synthetic_owner, companion.relationship
                )
                normalize_card(card_dict)
            except (NpcCardError, ValueError) as err:
                violations.append(
                    f"source kind='starting_companion' key={source_key!r} "
                    f"partner preset {companion.preset_key!r} derived card violates contract: {err}"
                )

    # 6. Quest template occupants
    for template in quest_templates:
        try:
            payload = template.to_payload()
            stages_payload = payload.get("stages", [])
        except Exception as err:
            violations.append(
                f"source kind='quest_template_occupant' template={template.name!r} "
                f"failed converting to payload: {err}"
            )
            stages_payload = []

        for stage in template.stages:
            stage_payload = (
                stages_payload[stage.index]
                if stage.index < len(stages_payload)
                else {}
            )
            npc_req_payloads = stage_payload.get("npc_req", [])

            for pos, req in enumerate(stage.npc_reqs):
                source_key = f"{template.name}:{stage.index}:{pos}"
                if req.persona is None:
                    violations.append(
                        f"source kind='quest_template_occupant' key={source_key!r} occupant has no persona"
                    )
                else:
                    try:
                        normalize_card(req.persona.to_record())
                    except (NpcCardError, ValueError) as err:
                        violations.append(
                            f"source kind='quest_template_occupant' key={source_key!r} invalid compact card: {err}"
                        )

                if pos < len(npc_req_payloads):
                    entry = npc_req_payloads[pos]
                    try:
                        lifespan = race_lifespan_upper_bound(req.tier)
                    except Exception as err:
                        violations.append(
                            f"source kind='quest_template_occupant' key={source_key!r} "
                            f"failed resolving lifespan for tier {req.tier!r}: {err}"
                        )
                        lifespan = None

                    if lifespan is not None:
                        char_errs = characterize_errors(
                            entry, lifespan_upper_bound=lifespan
                        )
                        for cerr in char_errs:
                            violations.append(
                                f"source kind='quest_template_occupant' key={source_key!r} "
                                f"characterization error: {cerr}"
                            )

    # 7. Shipped import examples
    for json_path in sorted(examples_dir.glob("*.json")):
        source_key = json_path.stem
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                record = json.load(f)
        except Exception as err:
            violations.append(
                f"source kind='import_example' key={source_key!r} failed to load JSON: {err}"
            )
            continue

        if not isinstance(record, dict):
            violations.append(
                f"source kind='import_example' key={source_key!r} JSON content is not an object"
            )
            continue

        try:
            report = validate_character(record, NPC)
        except Exception as err:
            violations.append(
                f"source kind='import_example' key={source_key!r} validation raised exception: {err}"
            )
            continue

        if not report.is_valid:
            rejections = "; ".join(f"{r.field}: {r.message}" for r in report.rejections)
            violations.append(
                f"source kind='import_example' key={source_key!r} validation failed: {rejections}"
            )

    # 8. Orphan profiles
    orphan_keys = sorted(set(profile_registry) - referenced_profiles)
    for prof_key in orphan_keys:
        violations.append(
            f"orphan profile {prof_key!r} in profile registry is referenced by no hosted place, examiner rank or persistent adventurer"
        )

    if violations:
        raise NpcRosterError(violations)
