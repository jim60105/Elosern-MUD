import copy
import json
from pathlib import Path

EXAMPLE_PATH = (
    Path(__file__).parents[1] / "examples" / "example_character.json"
)


def example_record():
    return copy.deepcopy(json.loads(EXAMPLE_PATH.read_text(encoding="utf-8")))
