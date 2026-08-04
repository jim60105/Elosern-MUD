"""The adult portrait gate: canonical ages, checked immediately before enqueue.

Every ``portrait:character`` enqueue re-checks ``age >= 18`` and
``apparent_age >= 18`` from the character's canonical attributes, in addition
to the creation/import schema validation. A rejection is deterministic (a pure
function of the canonical age attributes), produces no queue record and no
prompt, and never reaches a worker fixture (design D3).
"""

ADULT_MINIMUM = 18


class PortraitRejected(ValueError):
    """Raised when a character portrait fails the adult age gate.

    ``field`` names the canonical attribute that failed; the message is the
    named diagnostic staff logs and the browser never sees.
    """

    def __init__(self, field: str, value, message: str):
        super().__init__(message)
        self.field = field
        self.value = value


def _read_age(entity, field: str) -> int:
    value = entity.attributes.get(field)
    if value is None:
        raise PortraitRejected(
            field, None, f"portrait rejected: {field} is missing"
        )
    if type(value) is not int:
        raise PortraitRejected(
            field, value, f"portrait rejected: {field} must be an integer"
        )
    if value < ADULT_MINIMUM:
        raise PortraitRejected(
            field,
            value,
            f"portrait rejected: {field} {value} is below the adult minimum",
        )
    return value


def portrait_eligibility(entity) -> tuple[int, int]:
    """Return the validated ``(age, apparent_age)`` or raise ``PortraitRejected``.

    The gate is a pure function of the character's canonical attributes: the
    same underage data rejects with the same named diagnostic on every attempt,
    so no persisted rejection marker is needed and no retry storm can occur.
    """
    age = _read_age(entity, "age")
    apparent_age = _read_age(entity, "apparent_age")
    return age, apparent_age
