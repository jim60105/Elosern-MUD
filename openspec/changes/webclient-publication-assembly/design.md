# Atomic bounded publication receiver

## Context

C owns the exact `ui_publication_part` shape/constants and server sender. Browser protocol/store.js already stores complete eager panels plus separately retained maps, using map_parts.js for the specialized map protocol. The app transport.js currently registers four OOB message names. D's pending result is distinct from a committed accepted presentation.

## Goals / Non-Goals

Implement one complete general-publication assembly owner under the existing reducer, with no intermediate view or metadata adoption. Preserve specialized map schema/resource ownership. No retransmission protocol, ACK or historical delta queue.

## Decisions

Add `protocol/publication_parts.js::createPublicationAssembler({now,setTimer,clearTimer,onFailure})`. now defaults to monotonic performance.now where available; tests inject a deterministic clock. Public methods are `accept(header,chunks)`, `clear()`, `pruneThrough(revision)` and `stats()`. Return `{status:"pending"}` or `{status:"complete",kind,logical}` or `{status:"failed",reason}`. The reducer owns one instance for each current transport and exposes bounded stats for deterministic diagnostics, never raw data.

Validate generic part frame safety and C's exact header/chunk shape before allocating a buffer. Check transport generation, retired epoch and active epoch before buffering. During initial state, snapshot parts may provisionally assemble one candidate E without establishing activeEpoch; delta parts cannot establish initial state. Initial E is established only after complete logical snapshot validation. On an active E reject different E even for snapshots, preserving existing puppet transition rules through transport lifecycle. Target <=committed R is discarded without starting recovery.

Only part_index0 starts an assembly. Require exact next index, identical headers and derived sizes/count. Duplicate/out-of-order/missing predecessor, contradictory transfer fields, invalid base64/padding, excessive N/C/chunks or byte count fails and discards that transfer. A duplicate older fully committed publication is an ordinary stale discard. Delta B must equal current committed revision at start and again at final adoption. A later delta cannot skip an incomplete predecessor: abandon the incomplete transfer and signal recovery, never buffer both or commit the later delta. A newer snapshot transfer may supersede an incomplete lower-target transfer only at index0 and in the live epoch; discard old buffers/timer and start a new fixed deadline. An intact valid newer complete snapshot also supersedes obsolete assembly. A stale or malformed snapshot never destroys the last complete presentation.

Allocate bounded raw chunks after header checks and enforce total byte budget while appending. One live general assembly <=16MiB, <=683 parts. Deadline is first accepted part time+30000ms, never refreshed by traffic. Schedule one expiry callback at that deadline, so a missing final part triggers failure without further traffic. Decode concatenated bytes once using fatal UTF-8; parse JSON and validate logical snapshot/delta/schema limits from root without applying the generic 65536 byte envelope cap. Logical E/R/B/K must match the headers. Never lower panel-local string/list/object/depth limits or byte bounds. Commit staged logical presentation via D's same commit path exactly once and return `{accepted:true,revision:R}` only then. Pending returns `{accepted:false,pending:true}` and does not notify subscribers, release mutation gates or clear recovery failure signals.

Register ui_publication_part in protocol/constants.js MESSAGE_NAMES, protocol.js public exports, app/lib/protocol.js exports as needed and app/transport.js OOB_MESSAGES. Extend protocol/store.js::receive to route general parts independently from `panels.area_map.part`. Keep `protocol/map_parts.js` unchanged except lifecycle calls needed to clear both owners. General and map buffers use separate explicit bounds/stats. Disconnect (`setConnected(false)`), beginTransport, detach/no_puppet, epoch retirement, expiry and supersession release buffers and cancel timers. Old timer callbacks check captured generation/transfer identity before acting. For a valid completed general snapshot prune obsolete map assemblies but retain same-epoch complete maps.

Failure returns an explicit recovery-needed result and records reducer recovery state; R connects it to the single request sender. Tests cover both general and specialized map assembly live together, disconnect with both buffered and no remaining timers, first-ever multipart snapshot, later full repair, stale old-generation callbacks and all header/body contradictions. No general part uses a world-map allowance.

## Exact targets

Own protocol/publication_parts.js (new), protocol/store.js, protocol/{constants,envelope}.js logical-validation exports, protocol.js/app lib facade, app/transport.js routing, `js/tests/protocol_publication_parts.test.js` (new), existing protocol_transport.test.js/protocol_map_panels.test.js/protocol_world_map_transport.test.js and app/tests/transport.test.js. Use C's Python encoder output in a cross-language fixture test under presentation/tests/test_publication_parts.py so identical bytes exercise the real browser reducer. Update existing protocol delivery documentation alongside behavior.

## Risks / Trade-offs

One fixed deadline is transport recovery, not periodic alignment. Supersession must validate the candidate header before releasing the old buffer. Invalid completed publications retain the prior committed state and mutations stay locked through R. This slice never reports a partial frame as an adopted revision.
