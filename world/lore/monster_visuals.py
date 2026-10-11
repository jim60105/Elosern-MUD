"""Authoritative visual-species registry for monster art representations.

Design reference: fix-monster-species-portraits D1.

Separates art visual identity from combat mechanics. Baseline wilderness
monsters declare an authored visual key from a frozen table, while combat
species project their public appearance through a pure adapter.
"""

from dataclasses import dataclass
from typing import Mapping

from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MonsterSpecies,
)

# Reserved stable-key grammar: lowercase letters, numbers, underscores.
# Must start with letter. Threat-tier names and internal reserved tokens are rejected.
RESERVED_KEYS = frozenset({
    "low",
    "mid",
    "high",
    "calamity",
    "monster_anon",
    "character_anon",
    "anon",
    "default",
})


@dataclass(frozen=True)
class MonsterVisualDeclaration:
    """Public appearance projection of a monster visual species."""

    stable_key: str
    display_label: str
    published_appearance_zh: str
    is_baseline_art_only: bool = False


# The twelve authored baseline visual rows from design D1:
# Ordered visual keys mapping to existing example labels.
BASELINE_VISUAL_ROWS: tuple[MonsterVisualDeclaration, ...] = (
    # low
    MonsterVisualDeclaration(
        stable_key="slime",
        display_label="史萊姆",
        published_appearance_zh="膠狀半透明不定形生物，體內流動著微光核心。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="goblin",
        display_label="哥布林",
        published_appearance_zh="身形矮小瘦削的類人生物，膚色泛綠，長耳尖鼻，眼神狡黠。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="giant_rat",
        display_label="巨鼠",
        published_appearance_zh="體型如中型犬的兇暴齧齒動物，毛皮粗糙灰黑，長尾裸露。",
        is_baseline_art_only=True,
    ),
    # mid
    MonsterVisualDeclaration(
        stable_key="wolf_beast",
        display_label="魔狼",
        published_appearance_zh="四足狂暴魔獸，體型碩大，毛皮深邃如夜，眼瞳泛紅，獠牙外露。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="ogre",
        display_label="食人魔",
        published_appearance_zh="身形魁梧粗壯的巨大人形魔物，肌肉賁張，面容猙獰粗獷。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="earth_dragon",
        display_label="地龍",
        published_appearance_zh="覆蓋厚重岩石般暗褐色鱗片的重型爬行類魔獸，四肢粗短有力。",
        is_baseline_art_only=True,
    ),
    # high
    MonsterVisualDeclaration(
        stable_key="two_headed_dragon",
        display_label="雙頭龍",
        published_appearance_zh="生有兩顆巨首的雙足飛龍，翼展遮天，鱗片如鋼鐵般堅硬冰冷。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="magical_creature",
        display_label="魔精幻獸",
        published_appearance_zh="周身環繞扭曲魔力微光的奇異幻獸，形體如煙似霧，變幻莫測。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="troll",
        display_label="巨魔",
        published_appearance_zh="高大駝背的古老巨獸，粗糙如樹皮的厚皮上生著苔蘚，手臂長及膝蓋。",
        is_baseline_art_only=True,
    ),
    # calamity
    MonsterVisualDeclaration(
        stable_key="ancient_dragon",
        display_label="遠古巨龍",
        published_appearance_zh="沉睡千年的至高龍族，龐大軀體如山嶽隆起，鱗甲如黑曜石般泛著冷光。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="demon_god",
        display_label="魔神殘影",
        published_appearance_zh="自深淵溢出的神性殘骸，扭曲形體伴隨黑暗氣息，散發毀滅威壓。",
        is_baseline_art_only=True,
    ),
    MonsterVisualDeclaration(
        stable_key="calamity_beast",
        display_label="災厄魔獸",
        published_appearance_zh="引發天地災異的龐大異形凶獸，周身纏繞天災風暴，目力所及盡化廢墟。",
        is_baseline_art_only=True,
    ),
)


def adapt_combat_species(species: MonsterSpecies) -> MonsterVisualDeclaration:
    """Project a complete MonsterSpecies into its public art visual appearance."""
    return MonsterVisualDeclaration(
        stable_key=species.key,
        display_label=species.display_name_zh,
        published_appearance_zh=species.published_appearance_zh or species.display_name_zh,
        is_baseline_art_only=False,
    )


def build_monster_visual_registry(
    combat_species_registry: Mapping[str, MonsterSpecies] | None = None,
) -> dict[str, MonsterVisualDeclaration]:
    """Compose the visual species registry at consumer seams.

    Composes baseline art-only rows with the active combat species registry.
    Detects duplicate keys or collisions between baseline and combat species as
    authoring errors.
    """
    registry: dict[str, MonsterVisualDeclaration] = {}

    # 1. Author baseline visual rows
    for row in BASELINE_VISUAL_ROWS:
        key = row.stable_key
        if key in RESERVED_KEYS:
            raise ValueError(f"Baseline monster visual key '{key}' is reserved")
        if key in registry:
            raise ValueError(f"Duplicate baseline monster visual key '{key}'")
        registry[key] = row

    # 2. Project combat species
    active_combat = (
        combat_species_registry
        if combat_species_registry is not None
        else MONSTER_SPECIES_REGISTRY
    )

    for key, species in active_combat.items():
        if key in RESERVED_KEYS:
            raise ValueError(f"Combat species key '{key}' is reserved")
        if key in registry:
            raise ValueError(
                f"Collision between combat species and baseline visual key '{key}'"
            )
        registry[key] = adapt_combat_species(species)

    return registry


# Active registry getter (pure, dynamic to reflect test-scoped synthetic registries)
def get_monster_visual_registry() -> dict[str, MonsterVisualDeclaration]:
    """Return the merged visual registry reflecting current combat species state."""
    return build_monster_visual_registry()


def is_registered_monster_visual_key(key: str) -> bool:
    """Check if key is an admitted monster visual species key."""
    if not isinstance(key, str) or not key or key in RESERVED_KEYS:
        return False
    return key in get_monster_visual_registry()
