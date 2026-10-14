// adult-reference.js — the fixed adult-size ruler the stage editor draws
// behind the figure (change unified-gallery-original-editors).
//
// The ruler is a bundled, immutable asset: the same `/art/defaults/man.webp`
// the stage editor has always painted as a CSS mask. It is also a *resource*
// this editor observes through the shared ordered-attempt lifecycle, so its own
// decode — and its own failure — is a local fact the editor can report. It is
// deliberately its own subject: the ruler never enters the edited card's
// attempts or terminal, never supplies the original's dimensions and never
// authorizes saving.
//
// Only the facts the shared lifecycle reads are carried (the stable subject,
// the ordered attempts and the terminal), because none of the rest is a panel
// fact: this is not wire data and no backend selector produced it. The
// `version` mirrors the one digest the backend's descriptors use for an
// admitted immutable identity — `world/art/descriptors.py:identity_version(
// "defaults/man.webp")` — so the client's ruler resource names exactly the
// bytes the server's own bundled-artifact vocabulary names.

// The bundled ruler's canonical resource identity and served URL.
export const ADULT_REFERENCE_URL = "/art/defaults/man.webp";
// The stable subject of the observation (its own resolution epoch).
export const ADULT_REFERENCE_SUBJECT = "artwork-reference:adult-size";
// `identity_version("defaults/man.webp")`: sha256 over the canonical JSON of
// the admitted identity, hex-encoded.
const ADULT_REFERENCE_VERSION =
  "321804756f13c3a0cb3574f7a49f9cb52c1d0f78453a406eb1aa3b570466b725";

export const ADULT_REFERENCE_DESCRIPTOR = Object.freeze({
  subject_id: ADULT_REFERENCE_SUBJECT,
  attempts: Object.freeze([
    Object.freeze({
      type: "image",
      source_id: "reference.bundled:adult-size",
      rank: 10,
      resource: Object.freeze({
        resource_id: "defaults/man.webp",
        version: ADULT_REFERENCE_VERSION,
        url: ADULT_REFERENCE_URL,
        origin: "bundled_official",
        geometry: null,
      }),
    }),
  ]),
  terminal: null,
});
