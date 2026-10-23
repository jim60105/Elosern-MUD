"use strict";

// Bounded atomic part assembly for on-demand map panels (OpenSpec change
// define-map-panel-protocol). Mirror of web/webclient/presentation/map_parts.py.
//
// A part frame is an ordinary ui_update whose panels hold exactly one map
// panel in the part wire variant
//   {schema_version: 1, available: true,
//    part: {transfer_id, index, count, byte_length, chunk}}
// where chunk is padded standard base64 of one fixed-size slice (1536 raw
// bytes, the last one shorter) of the canonical UTF-8 JSON logical body.
//
// The assembler keeps at most one live transfer per map panel. Nothing is
// visible until every part arrived, the exact byte count decoded, the bytes
// are strict UTF-8 JSON and the full logical schema validated. The logical
// byte bound is enforced on byte_length (and therefore on the decoded byte
// count): the browser never re-serializes the body to measure it, because its
// number formatting can differ from the server's canonical form.

var core = require("./core.js");
var mapPanels = require("./panels/map_panels.js");

var isPlainObject = core.isPlainObject;
var MAP_MAX_BYTES = mapPanels.MAP_MAX_BYTES;

var MAP_PART_SCHEMA_VERSION = 1;
var MAP_PART_RAW_BYTES = 1536;
var MAP_PART_CHUNK_CHARS = 2048;
var TRANSFER_ID_RE = /^[A-Za-z0-9_-]{22}$/;
var BASE64_RE = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
var BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
// Transfer IDs remembered per panel after completion or retirement, so a
// replayed frame can never reopen or disturb an assembly.
var MAX_FINISHED_TRANSFERS = 8;

function maxParts(panel) {
  return Math.ceil(MAP_MAX_BYTES[panel] / MAP_PART_RAW_BYTES);
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
function decodeBase64(text) {
  if (typeof text !== "string" || text.length === 0 || !BASE64_RE.test(text)) {
    throw new Error("chunk is not canonical base64");
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
    throw new Error("chunk is not canonical base64");
  }
  return bytes;
}

function partInt(value, name, minimum, maximum) {
  if (typeof value !== "number" || !Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(name + " must be an integer within " + minimum + ".." + maximum);
  }
  return value;
}

function isMapPart(value) {
  return isPlainObject(value) && Object.prototype.hasOwnProperty.call(value, "part");
}

// Validate one part wire value; return its normalized header and raw bytes.
function validateMapPart(panel, value) {
  if (!Object.prototype.hasOwnProperty.call(MAP_MAX_BYTES, panel)) {
    throw new Error(panel + " is not an on-demand map panel");
  }
  core.requireExactFields(value, "map part", ["schema_version", "available", "part"], []);
  if (value.schema_version !== MAP_PART_SCHEMA_VERSION) {
    throw new Error("unsupported map part schema_version");
  }
  if (value.available !== true) {
    throw new Error("a map part must be available");
  }
  var part = value.part;
  core.requireExactFields(part, "part", ["transfer_id", "index", "count", "byte_length", "chunk"], []);
  if (typeof part.transfer_id !== "string" || !TRANSFER_ID_RE.test(part.transfer_id)) {
    throw new Error("transfer_id must be 22 URL-safe ASCII characters");
  }
  var byteLength = partInt(part.byte_length, "byte_length", 1, MAP_MAX_BYTES[panel]);
  var count = partInt(part.count, "count", 1, maxParts(panel));
  if (count !== Math.ceil(byteLength / MAP_PART_RAW_BYTES)) {
    throw new Error("count must equal ceil(byte_length / part size)");
  }
  var index = partInt(part.index, "index", 0, count - 1);
  if (typeof part.chunk !== "string" || part.chunk.length < 4 || part.chunk.length > MAP_PART_CHUNK_CHARS) {
    throw new Error("chunk must be 4..2048 base64 characters");
  }
  var bytes = decodeBase64(part.chunk);
  var expected = index < count - 1 ? MAP_PART_RAW_BYTES : byteLength - MAP_PART_RAW_BYTES * (count - 1);
  if (bytes.length !== expected) {
    throw new Error("chunk size does not match its index");
  }
  return {
    header: { transfer_id: part.transfer_id, index: index, count: count, byte_length: byteLength },
    bytes: bytes,
  };
}

function sameBytes(a, b) {
  if (a.length !== b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

// Decode a complete byte sequence into the validated logical body.
function decodeLogical(panel, bytes) {
  var text;
  try {
    // ignoreBOM keeps a leading BOM so JSON.parse rejects it, as Python does.
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch (error) {
    throw new Error("reassembled body is not UTF-8");
  }
  var body;
  try {
    body = JSON.parse(text);
  } catch (error) {
    throw new Error("reassembled body is not JSON");
  }
  return mapPanels.validateMapPanel(panel, body);
}

// One bounded assembler per store. `metaKey` identifies the frame metadata
// (revision, mode, layout version and server time) every part must share.
function createMapAssembler() {
  var live = {};
  var finished = {};

  function finish(panel, transferId) {
    var list = finished[panel] || (finished[panel] = []);
    if (list.indexOf(transferId) === -1) {
      list.push(transferId);
      while (list.length > MAX_FINISHED_TRANSFERS) list.shift();
    }
  }

  function retire(panel) {
    var assembly = live[panel];
    if (assembly) {
      finish(panel, assembly.transferId);
      delete live[panel];
    }
  }

  return {
    // Offer one validated part. Returns {status: "partial" | "complete" |
    // "rejected", reason?, panel?, logical?, revision?}.
    offer: function (panel, header, bytes, revision, metaKey) {
      var list = finished[panel] || [];
      if (list.indexOf(header.transfer_id) !== -1) {
        return { status: "rejected", reason: "finished_transfer" };
      }
      var assembly = live[panel];
      if (assembly && assembly.transferId !== header.transfer_id) {
        if (revision <= assembly.revision) {
          // An older or same-revision stray transfer never disturbs the live one.
          return { status: "rejected", reason: "superseded_transfer" };
        }
        retire(panel);
        assembly = null;
      }
      if (!assembly) {
        assembly = live[panel] = {
          transferId: header.transfer_id,
          revision: revision,
          metaKey: metaKey,
          count: header.count,
          byteLength: header.byte_length,
          chunks: new Array(header.count),
          received: 0,
        };
      }
      if (
        assembly.metaKey !== metaKey ||
        assembly.count !== header.count ||
        assembly.byteLength !== header.byte_length
      ) {
        retire(panel);
        return { status: "rejected", reason: "conflicting_part" };
      }
      var existing = assembly.chunks[header.index];
      if (existing) {
        if (sameBytes(existing, bytes)) {
          return { status: "rejected", reason: "duplicate_part" };
        }
        retire(panel);
        return { status: "rejected", reason: "conflicting_part" };
      }
      assembly.chunks[header.index] = bytes;
      assembly.received += 1;
      if (assembly.received < assembly.count) {
        return { status: "partial" };
      }
      retire(panel);
      var whole = new Uint8Array(assembly.byteLength);
      var offset = 0;
      assembly.chunks.forEach(function (chunk) {
        whole.set(chunk, offset);
        offset += chunk.length;
      });
      if (offset !== assembly.byteLength) {
        return { status: "rejected", reason: "byte_length_mismatch" };
      }
      var logical;
      try {
        logical = decodeLogical(panel, whole);
      } catch (error) {
        return { status: "rejected", reason: "invalid_body", detail: error.message };
      }
      return { status: "complete", panel: panel, logical: logical, revision: assembly.revision };
    },

    // Retire every live assembly at or below a committed revision.
    pruneThrough: function (revision) {
      Object.keys(live).forEach(function (panel) {
        if (live[panel].revision <= revision) retire(panel);
      });
    },

    // A new epoch or transport discards everything.
    clear: function () {
      live = {};
      finished = {};
    },

    liveCount: function () {
      return Object.keys(live).length;
    },

    bufferedBytes: function () {
      return Object.keys(live).reduce(function (total, panel) {
        return (
          total +
          live[panel].chunks.reduce(function (sum, chunk) {
            return sum + (chunk ? chunk.length : 0);
          }, 0)
        );
      }, 0);
    },
  };
}

module.exports = {
  MAP_PART_SCHEMA_VERSION: MAP_PART_SCHEMA_VERSION,
  MAP_PART_RAW_BYTES: MAP_PART_RAW_BYTES,
  MAP_PART_CHUNK_CHARS: MAP_PART_CHUNK_CHARS,
  MAX_FINISHED_TRANSFERS: MAX_FINISHED_TRANSFERS,
  maxParts: maxParts,
  encodeBase64: encodeBase64,
  decodeBase64: decodeBase64,
  isMapPart: isMapPart,
  validateMapPart: validateMapPart,
  decodeLogical: decodeLogical,
  createMapAssembler: createMapAssembler,
};
