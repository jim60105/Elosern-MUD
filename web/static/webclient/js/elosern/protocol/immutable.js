"use strict";

// Ownership helpers for the reducer's committed presentation state
// (webclient-immutable-adoption).
//
// The reducer owns exactly one authoritative state and publishes exactly one
// immutable committed record per publication. Validated transport input still
// belongs to the caller (`core.validatePanel` returns the payload object
// itself), so every adopted payload is copied once and frozen once before it
// becomes part of that state:
//
// - `copyOwned` detaches a validated payload from the caller's object graph,
//   so mutating the original transport envelope after `receive` returns cannot
//   reach a committed value.
// - `freezeOwned` recursively freezes the copy. It stops at any already frozen
//   node, so a value a previous commit adopted is reused by reference and is
//   never traversed or re-frozen again: that is what keeps an unchanged panel
//   in `===` identity across a delta.
// - `equalOwned` compares two JSON values structurally. The snapshot path uses
//   it to recognise an already committed panel with identical content and
//   reuse that value instead of replacing it, so an equal complete alignment
//   (a checkpoint) never hands consumers a new object for unchanged data. The
//   comparison is plain JSON-value equality: no serialization, no hashing, no
//   canonical text of any kind.
//
// These helpers are internal to the reducer; they are not part of the frozen
// `Protocol` facade.

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// A deep copy of one validated JSON value. Every object and array in the
// result is a fresh container; leaves are primitives or null.
//
// Own properties are defined, never assigned through the prototype chain: a
// validated JSON object may carry an own `"__proto__"` key, and a plain
// assignment would turn that key into the copy's prototype (losing the content
// and leaving an unfrozen graph reachable behind it).
function copyOwned(value) {
  if (Array.isArray(value)) {
    var list = [];
    for (var index = 0; index < value.length; index++) {
      list.push(copyOwned(value[index]));
    }
    return list;
  }
  if (isPlainObject(value)) {
    var copy = {};
    var keys = Object.keys(value);
    for (var k = 0; k < keys.length; k++) {
      Object.defineProperty(copy, keys[k], {
        value: copyOwned(value[keys[k]]),
        writable: true,
        enumerable: true,
        configurable: true,
      });
    }
    return copy;
  }
  return value;
}

// Recursively freeze one owned JSON value. A frozen node is returned as it is:
// it is already owned by an earlier commit.
function freezeOwned(value) {
  if (value === null || typeof value !== "object" || Object.isFrozen(value)) {
    return value;
  }
  if (Array.isArray(value)) {
    for (var index = 0; index < value.length; index++) {
      freezeOwned(value[index]);
    }
  } else {
    var keys = Object.keys(value);
    for (var k = 0; k < keys.length; k++) {
      freezeOwned(value[keys[k]]);
    }
  }
  return Object.freeze(value);
}

// Structural equality over JSON values: dictionaries are unordered, arrays
// keep their order, and `===` compares the JSON scalars (so `1` equals `1.0`
// while `true` never equals `1`).
function equalOwned(left, right) {
  if (left === right) {
    return true;
  }
  if (Array.isArray(left)) {
    if (!Array.isArray(right) || left.length !== right.length) {
      return false;
    }
    for (var index = 0; index < left.length; index++) {
      if (!equalOwned(left[index], right[index])) {
        return false;
      }
    }
    return true;
  }
  if (isPlainObject(left)) {
    if (!isPlainObject(right)) {
      return false;
    }
    var keys = Object.keys(left);
    if (keys.length !== Object.keys(right).length) {
      return false;
    }
    for (var k = 0; k < keys.length; k++) {
      if (!Object.prototype.hasOwnProperty.call(right, keys[k])) {
        return false;
      }
      if (!equalOwned(left[keys[k]], right[keys[k]])) {
        return false;
      }
    }
    return true;
  }
  return false;
}

module.exports = {
  copyOwned: copyOwned,
  freezeOwned: freezeOwned,
  equalOwned: equalOwned,
};
