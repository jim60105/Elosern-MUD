"""Element registry from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Element:
    key: str
    display_name_zh: str
    description: str


ELEMENT_REGISTRY: dict[str, Element] = {
    "fire": Element("fire", "火", "The strongest offensive element."),
    "water": Element("water", "水", "Healing and defense."),
    "wind": Element("wind", "風", "Speed and area attacks."),
    "earth": Element("earth", "土", "Defense and control."),
    "lightning": Element("lightning", "雷", "High-speed attacks."),
    "ice": Element("ice", "冰", "Control and offense."),
    "light": Element("light", "光", "Healing and purification."),
    "dark": Element("dark", "暗", "Curses and weakening effects."),
}
