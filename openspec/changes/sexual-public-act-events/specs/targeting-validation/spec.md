# targeting-validation Delta Specification

## ADDED Requirements

### Requirement: RoomActionContext exposes the room through event_context
`world/rules/targeting.py`'s `RoomActionContext.__init__` SHALL copy the caller-supplied
`event_context` and SHALL inject `event_context["room"]` bound to the constructed context's room,
so effect handlers and presenters that read `event_context` can deterministically discover the
out-of-combat location without a new handler surface. The injection SHALL be unconditional and
SHALL NOT alter any other key the caller supplied.

#### Scenario: A constructed RoomActionContext carries the room key
- **WHEN** `RoomActionContext(room, {"disguise": {}})` is constructed
- **THEN** its `event_context` equals `{"disguise": {}, "room": room}`

#### Scenario: A caller-supplied room key is replaced, never duplicated
- **WHEN** `RoomActionContext(room, {"room": other_room})` is constructed
- **THEN** its `event_context["room"]` is the constructed context's own `room`, not the
  caller-supplied value
