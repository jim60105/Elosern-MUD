"use strict";

// Bounded atomic assembly for general publications (OpenSpec change
// webclient-publication-assembly). Mirror of the receiver side of
// web/webclient/presentation/publication_parts.py.
//
// A logical ui_snapshot/ui_update whose canonical UTF-8 JSON does not fit its
// intact frame allowance travels as one ordered transfer of
// `ui_publication_part` frames:
//
//   {protocol_version: 1, presentation_epoch, revision, publication_kind,
//    transfer_id, part_index, part_count, total_bytes, chunks}
//   (plus base_revision for a delta, forbidden for a snapshot)
//
// Each part is exactly one object of those fields; `chunks` holds 1..16
// canonical padded RFC 4648 base64 strings, every non-final chunk decoding to
// exactly 1536 raw bytes and the final one to the exact remainder. Nothing is
// visible until every ordered part arrived, the declared byte count decoded,
// the bytes are strict UTF-8 JSON and the store validated the logical
// document. The generic 65,536-byte frame ceiling is enforced on each part
// frame and never reapplied to the reassembled logical document.
//
// One live general assembly exists per transport (<=16 MiB, <=683 parts) with
// a fixed 30,000ms deadline from its first accepted part. Later traffic never
// extends it; expiry fails it once without requiring another frame. The store
// owns the sibling specialized map assembler (`map_parts.js`); the two keep
// separate buffers, bounds and teardown.

var C = require("./constants.js");
var core = require("./core.js");

var PUBLICATION_MAX_BYTES = C.PUBLICATION_MAX_BYTES;
var PUBLICATION_PART_BYTES = C.PUBLICATION_PART_BYTES;
var PUBLICATION_CHUNK_BYTES = C.PUBLICATION_CHUNK_BYTES;
var PUBLICATION_MAX_CHUNKS = C.PUBLICATION_MAX_CHUNKS;
var PUBLICATION_MAX_PARTS = C.PUBLICATION_MAX_PARTS;
var PUBLICATION_ASSEMBLY_TIMEOUT_MS = C.PUBLICATION_ASSEMBLY_TIMEOUT_MS;

// The closed publication-kind vocabulary.
var PUBLICATION_KINDS = ["snapshot", "delta"];
var TRANSFER_ID_RE = /^[0-9a-f]{32}$/;
var BASE64_RE = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
var BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
// Transfer identities remembered after completion, so a replayed frame can
// never reopen a finished assembly. Bounded like the map assembler's list.
var MAX_FINISHED_TRANSFERS = 8;

var PART_FIELDS = [
  "protocol_version",
  "presentation_epoch",
  "revision",
  "publication_kind",
  "transfer_id",
  "part_index",
  "part_count",
  "total_bytes",
  "chunks",
];

function partInt(value, name, minimum, maximum) {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new Error(name + " must be an integer");
  }
  if (value < minimum || value > maximum) {
    throw new Error(name + " must be within " + minimum + ".." + maximum);
  }
  return value;
}

function partBytes(index, count, totalBytes) {
  if (index < count - 1) {
    return PUBLICATION_PART_BYTES;
  }
  return totalBytes - PUBLICATION_PART_BYTES * (count - 1);
}

function chunkBytes(index, count, byteLength) {
  if (index < count - 1) {
    return PUBLICATION_CHUNK_BYTES;
  }
  return byteLength - PUBLICATION_CHUNK_BYTES * (count - 1);
}

function encodeBase64(bytes) {
  var out = "";
  for (var i = 0; i < bytes.length; i += 3) {
    var a = bytes[i];
    var b = i + 1 < bytes.length ? bytes[i + 1] : 0;
    var c = i + 2 < bytes.length ? bytes[i + 2] : 0;
    var triple = (a << 16) | (b << 8) | c;
    out += BASE64_ALPHABET[(triple >> 18) & 63] + BASE64_ALPHABET[(triple >> 12) & 63];
    out += i + 1 < bytes.length ? BASE64_ALPHABET[(triple >> 6) & 63] : "=";
    out += i + 2 < bytes.length ? BASE64_ALPHABET[triple & 63] : "=";
  }
  return out;
}

// Strict canonical base64: the alphabet, padding and zero pad bits.
function decodeChunk(text, name) {
  if (typeof text !== "string" || text.length === 0 || !BASE64_RE.test(text)) {
    throw new Error(name + " is not canonical base64");
  }
  var padding = text.endsWith("==") ? 2 : text.endsWith("=") ? 1 : 0;
  var bytes = new Uint8Array((text.length / 4) * 3 - padding);
  var position = 0;
  for (var i = 0; i < text.length; i += 4) {
    var n = 0;
    for (var j = 0; j < 4; j++) {
      var ch = text[i + j];
      n = (n << 6) | (ch === "=" ? 0 : BASE64_ALPHABET.indexOf(ch));
    }
    if (position < bytes.length) bytes[position++] = (n >> 16) & 255;
    if (position < bytes.length) bytes[position++] = (n >> 8) & 255;
    if (position < bytes.length) bytes[position++] = n & 255;
  }
  if (encodeBase64(bytes) !== text) {
    throw new Error(name + " is not canonical base64");
  }
  return bytes;
}

// Validate one part frame's exact field set, generic frame safety and header
// derivation WITHOUT decoding its chunks. The store uses this bounded first
// pass to reject obsolete epochs before any chunk buffer is allocated.
function inspectPublicationPart(value) {
  core.requireExactFields(value, "publication part", PART_FIELDS, ["base_revision"]);
  // The generic frame ceiling and global JSON-safety limits are unchanged for
  // a part frame; only the reassembled logical document gets its own bounds.
  core.checkEnvelope(value);
  if (value.protocol_version !== 1) {
    throw new Error("unsupported protocol_version");
  }
  var epoch = core.validateEpoch(value.presentation_epoch);
  var revision = partInt(value.revision, "revision", 1, core.MAX_SAFE_INTEGER);
  var kind = value.publication_kind;
  if (PUBLICATION_KINDS.indexOf(kind) === -1) {
    throw new Error("publication_kind must be one of " + PUBLICATION_KINDS.join(","));
  }
  if (typeof value.transfer_id !== "string" || !TRANSFER_ID_RE.test(value.transfer_id)) {
    throw new Error("transfer_id must be 32 lowercase hexadecimal characters");
  }
  var baseRevision = null;
  if (kind === "delta") {
    if (!Object.prototype.hasOwnProperty.call(value, "base_revision")) {
      throw new Error("a delta part requires base_revision");
    }
    baseRevision = partInt(value.base_revision, "base_revision", 1, core.MAX_SAFE_INTEGER);
    if (baseRevision >= revision) {
      throw new Error("base_revision must be older than revision");
    }
  } else if (Object.prototype.hasOwnProperty.call(value, "base_revision")) {
    throw new Error("a snapshot part forbids base_revision");
  }
  var totalBytes = partInt(value.total_bytes, "total_bytes", 1, PUBLICATION_MAX_BYTES);
  var partCount = partInt(value.part_count, "part_count", 1, PUBLICATION_MAX_PARTS);
  if (partCount !== Math.ceil(totalBytes / PUBLICATION_PART_BYTES)) {
    throw new Error("part_count must equal ceil(total_bytes / part size)");
  }
  var partIndex = partInt(value.part_index, "part_index", 0, partCount - 1);
  var chunks = value.chunks;
  if (!Array.isArray(chunks)) {
    throw new Error("chunks must be a JSON array");
  }
  var byteLength = partBytes(partIndex, partCount, totalBytes);
  var expectedChunks = Math.ceil(byteLength / PUBLICATION_CHUNK_BYTES);
  if (chunks.length !== expectedChunks) {
    throw new Error("chunks must equal ceil(part bytes / chunk size)");
  }
  if (chunks.length < 1 || chunks.length > PUBLICATION_MAX_CHUNKS) {
    throw new Error("chunks must hold 1.." + PUBLICATION_MAX_CHUNKS + " strings");
  }
  for (var index = 0; index < chunks.length; index++) {
    if (typeof chunks[index] !== "string") {
      throw new Error("chunk " + index + " must be a string");
    }
    if (chunks[index].length < 4 || chunks[index].length > (PUBLICATION_CHUNK_BYTES * 4) / 3) {
      throw new Error(
        "chunk " + index + " must be 4.." + (PUBLICATION_CHUNK_BYTES * 4) / 3 + " base64 characters"
      );
    }
  }
  return {
    header: {
      protocolVersion: 1,
      epoch: epoch,
      revision: revision,
      kind: kind,
      transferId: value.transfer_id,
      partIndex: partIndex,
      partCount: partCount,
      totalBytes: totalBytes,
      baseRevision: baseRevision,
    },
    chunks: chunks.slice(),
  };
}

// Decode one inspected part's chunk strings, enforcing their exact derived
// sizes. Allocation stays bounded by the derived part length (<=24,576).
function decodePublicationPartChunks(header, chunks) {
  var byteLength = partBytes(header.partIndex, header.partCount, header.totalBytes);
  var expectedChunks = Math.ceil(byteLength / PUBLICATION_CHUNK_BYTES);
  if (chunks.length !== expectedChunks) {
    throw new Error("chunks must equal ceil(part bytes / chunk size)");
  }
  var decoded = [];
  var total = 0;
  for (var index = 0; index < chunks.length; index++) {
    var expected = chunkBytes(index, chunks.length, byteLength);
    var bytes = decodeChunk(chunks[index], "chunk " + index);
    if (bytes.length !== expected) {
      throw new Error("chunk " + index + " size does not match its index");
    }
    decoded.push(bytes);
    total += bytes.length;
  }
  if (total !== byteLength) {
    throw new Error("part bytes do not match their declared length");
  }
  return decoded;
}

// Validate one part frame end to end; return its normalized header and the
// decoded per-chunk byte arrays.
function validatePublicationPart(value) {
  var inspected = inspectPublicationPart(value);
  var chunks = decodePublicationPartChunks(inspected.header, inspected.chunks);
  return { header: inspected.header, chunks: chunks };
}

function defaultNow() {
  if (typeof performance !== "undefined" && performance && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

// One bounded assembler per store. `accept` offers one part; the store owns
// epoch/base admission context and the final logical validation.
// Returns {status:"pending"} | {status:"failed", reason, recover, detail?} |
// {status:"complete", kind, epoch, revision, baseRevision, transferId,
// logical}. A failure with `recover` true has already invoked `onFailure`
// once; the buffers are gone either way.
function createPublicationAssembler(options) {
  options = options || {};
  var now = typeof options.now === "function" ? options.now : defaultNow;
  var setTimer =
    typeof options.setTimer === "function"
      ? options.setTimer
      : function (callback, delay) {
          return setTimeout(callback, delay);
        };
  var clearTimer =
    typeof options.clearTimer === "function"
      ? options.clearTimer
      : function (handle) {
          clearTimeout(handle);
        };
  var onFailure = typeof options.onFailure === "function" ? options.onFailure : function () {};

  var live = null;
  var timer = null;
  var buffered = 0;
  var finished = [];

  function remember(transferId) {
    if (finished.indexOf(transferId) === -1) {
      finished.push(transferId);
    }
    while (finished.length > MAX_FINISHED_TRANSFERS) {
      finished.shift();
    }
  }

  function releaseLive() {
    if (timer !== null) {
      clearTimer(timer);
      timer = null;
    }
    live = null;
    buffered = 0;
  }

  // A destructive failure: the live transfer (if any) is discarded and, when
  // `recover` is set, the store records one recovery-needed signal.
  function fail(reason, recover, detail) {
    var current = live;
    releaseLive();
    var result = { status: "failed", reason: reason, recover: !!recover };
    if (detail) {
      result.detail = detail;
    }
    if (current !== null) {
      result.transferId = current.transferId;
      result.revision = current.revision;
      result.kind = current.kind;
    }
    if (recover) {
      onFailure(result);
    }
    return result;
  }

  // A non-destructive rejection: the frame is discarded, the live transfer
  // stays untouched, and no recovery is signaled.
  function reject(reason) {
    return { status: "failed", reason: reason, recover: false };
  }

  function start(header) {
    live = {
      transferId: header.transferId,
      kind: header.kind,
      epoch: header.epoch,
      revision: header.revision,
      baseRevision: header.baseRevision,
      count: header.partCount,
      totalBytes: header.totalBytes,
      parts: new Array(header.partCount),
      received: 0,
      bytes: 0,
      deadline: now() + PUBLICATION_ASSEMBLY_TIMEOUT_MS,
    };
    var captured = live;
    // One expiry callback at the fixed first-part deadline; later parts never
    // reschedule it. A callback from a cleared/superseded assembly is inert.
    timer = setTimer(function () {
      // A callback from a cleared/superseded assembly is inert and must not
      // relinquish ownership of the replacement's timer handle.
      if (live !== captured) {
        return;
      }
      timer = null;
      fail("timeout", true);
    }, PUBLICATION_ASSEMBLY_TIMEOUT_MS);
  }

  function sameTransfer(header) {
    return (
      live.kind === header.kind &&
      live.epoch === header.epoch &&
      live.revision === header.revision &&
      live.baseRevision === header.baseRevision &&
      live.count === header.partCount &&
      live.totalBytes === header.totalBytes
    );
  }

  function finish() {
    var assembly = live;
    var whole = new Uint8Array(assembly.totalBytes);
    var offset = 0;
    for (var index = 0; index < assembly.parts.length; index++) {
      var part = assembly.parts[index];
      whole.set(part, offset);
      offset += part.length;
    }
    if (offset !== assembly.totalBytes) {
      return fail("byte_length_mismatch", true);
    }
    var text;
    try {
      // ignoreBOM keeps a leading BOM so JSON.parse rejects it, as Python does.
      text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(whole);
    } catch (error) {
      return fail("invalid_body", true, "reassembled body is not UTF-8");
    }
    var logical;
    try {
      logical = JSON.parse(text);
    } catch (error) {
      return fail("invalid_body", true, "reassembled body is not JSON");
    }
    var completed = {
      status: "complete",
      kind: assembly.kind,
      epoch: assembly.epoch,
      revision: assembly.revision,
      baseRevision: assembly.baseRevision,
      transferId: assembly.transferId,
      logical: logical,
    };
    remember(assembly.transferId);
    releaseLive();
    return completed;
  }

  return {
    // `context` is {phase, committedRevision} from the store. `chunks` holds
    // the inspected frame's decoded chunk byte arrays (<=16, each exactly the
    // derived size); the store decodes them once the frame's epoch is
    // admitted, so the assembler only re-derives and appends.
    accept: function (header, chunks, context) {
      context = context || {};
      var active = context.phase === "active";
      var committed =
        typeof context.committedRevision === "number" ? context.committedRevision : null;

      if (live !== null && now() >= live.deadline) {
        return fail("timeout", true);
      }
      if (finished.indexOf(header.transferId) !== -1) {
        return reject("finished_transfer");
      }
      // An obsolete target is an ordinary stale discard, never a recovery
      // signal. This runs before any live-transfer conflict handling so a
      // replayed part can never disturb newer in-flight work.
      if (active && committed !== null && header.revision <= committed) {
        if (live !== null && live.revision <= committed) {
          releaseLive();
        }
        return reject("not_newer");
      }

      if (live === null) {
        if (
          active &&
          committed !== null &&
          header.kind === "delta" &&
          header.baseRevision !== committed
        ) {
          // A delta without its exact baseline starts recovery; nothing is
          // buffered for it.
          return fail("base_mismatch", true);
        }
        if (header.partIndex !== 0) {
          return reject("no_assembly");
        }
        start(header);
      } else if (live.transferId === header.transferId) {
        if (!sameTransfer(header)) {
          return fail("conflicting_part", true);
        }
        if (header.partIndex !== live.received) {
          return fail(
            header.partIndex < live.received ? "duplicate_part" : "out_of_order",
            true
          );
        }
      } else {
        if (header.epoch !== live.epoch) {
          return reject("different_epoch");
        }
        if (header.kind === "delta") {
          // A later delta may never skip an incomplete predecessor: abandon
          // the incomplete transfer and request one complete sync.
          return fail("preceding_transfer", true);
        }
        if (header.partIndex !== 0) {
          return reject("no_assembly");
        }
        if (header.revision <= live.revision) {
          // An older or same-target snapshot never disturbs the live one.
          return reject("superseded_transfer");
        }
        releaseLive();
        start(header);
      }

      var byteLength = partBytes(header.partIndex, header.partCount, header.totalBytes);
      var expectedChunks = Math.ceil(byteLength / PUBLICATION_CHUNK_BYTES);
      var total = 0;
      if (!Array.isArray(chunks) || chunks.length !== expectedChunks) {
        return fail("invalid_chunk", true, "chunks do not match the derived part size");
      }
      for (var index = 0; index < chunks.length; index++) {
        var expected = chunkBytes(index, expectedChunks, byteLength);
        if (!(chunks[index] instanceof Uint8Array) || chunks[index].length !== expected) {
          return fail("invalid_chunk", true, "chunk " + index + " size does not match its index");
        }
        total += chunks[index].length;
      }
      if (total !== byteLength) {
        return fail("invalid_chunk", true, "part bytes do not match their declared length");
      }
      if (
        live.bytes + byteLength > live.totalBytes ||
        live.bytes + byteLength > PUBLICATION_MAX_BYTES
      ) {
        return fail("byte_overflow", true);
      }
      var value = new Uint8Array(byteLength);
      var position = 0;
      for (index = 0; index < chunks.length; index++) {
        value.set(chunks[index], position);
        position += chunks[index].length;
      }
      live.parts[header.partIndex] = value;
      live.bytes += byteLength;
      buffered += byteLength;
      live.received += 1;
      if (live.received < live.count) {
        return { status: "pending" };
      }
      return finish();
    },

    // Drop a live assembly at or below a committed revision (finished
    // publication; never a recovery signal).
    pruneThrough: function (revision) {
      if (live !== null && live.revision <= revision) {
        releaseLive();
      }
    },

    // A disconnect, new transport generation, detach or explicit reset:
    // release buffers/timers without signaling recovery.
    clear: function () {
      releaseLive();
      finished = [];
    },

    hasLive: function () {
      return live !== null;
    },

    liveCount: function () {
      return live === null ? 0 : 1;
    },

    bufferedBytes: function () {
      return buffered;
    },

    // Bounded diagnostics only (no buffered bytes or logical data).
    stats: function () {
      return {
        live: live !== null,
        transferId: live === null ? null : live.transferId,
        kind: live === null ? null : live.kind,
        revision: live === null ? null : live.revision,
        received: live === null ? 0 : live.received,
        partCount: live === null ? 0 : live.count,
        bytes: buffered,
        finished: finished.length,
      };
    },
  };
}

module.exports = {
  PUBLICATION_KINDS: PUBLICATION_KINDS,
  inspectPublicationPart: inspectPublicationPart,
  decodePublicationPartChunks: decodePublicationPartChunks,
  validatePublicationPart: validatePublicationPart,
  createPublicationAssembler: createPublicationAssembler,
};
