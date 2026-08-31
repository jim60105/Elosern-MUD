"""Tests for the local output-format conversion (art-output-format-pipeline).

Pure Pillow + piexif (``unittest.TestCase``, no database, no network). Every
metadata claim is checked with FORMAT-AWARE inspection — PNG ancillary chunks
parsed, JPEG APP-segments walked, WebP RIFF chunks enumerated, AVIF
``Image.info`` probed — never byte-marker scanning alone. Input fixtures
deliberately carry tEXt, iTXt, EXIF, and ICC payloads so both metadata modes
prove sanitization, not just omission.
"""

import base64
import io
import random
import struct
import unittest
import zlib

from django.test import override_settings

import piexif
from PIL import Image

from world.art.formats import build_parameters_text, encode
from world.art.sd_worker import SDError

from tools.spec_traceability import covers_requirement

# Distinctive marker embedded in every input fixture's metadata; its absence
# from an output is the "no server metadata survived" assertion.
SERVER_MARKER = "SERVER-EMBEDDED-MARKER-9f3c"

_PROMPT = "城門前的夜市，燈籠高掛"
_NEGATIVE = "低品質, 模糊"

_BASE_KWARGS = dict(
    prompt=_PROMPT,
    negative_prompt=_NEGATIVE,
    steps=30,
    cfg_scale=7.0,
    sampler=None,
    scheduler=None,
    width=64,
    height=48,
    seed=12345,
    checkpoint=None,
)

_EXT_BY_FORMAT = {"png": ".png", "webp": ".webp", "jpeg": ".jpg", "avif": ".avif"}


def _configured(output_format: str):
    """override_settings pairing the format knob with its derived extension."""
    return override_settings(
        ART_SD_OUTPUT_FORMAT=output_format,
        ART_SD_OUTPUT_EXTENSION=_EXT_BY_FORMAT[output_format],
    )


def _encode(png_bytes: bytes, output_format: str, **overrides):
    overrides = dict(overrides)
    quality = overrides.pop("quality", 80)
    preserve = overrides.pop("preserve_metadata", True)
    kwargs = {**_BASE_KWARGS, **overrides}
    with _configured(output_format):
        return encode(
            png_bytes,
            output_format=output_format,
            quality=quality,
            preserve_metadata=preserve,
            **kwargs,
        )


def _noise_png(size=(64, 48), mode="RGB", seed=42) -> bytes:
    buffer = io.BytesIO()
    rand = random.Random(seed)
    image = Image.frombytes(mode, size, rand.randbytes(size[0] * size[1] * len(mode)))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _server_exif_bytes() -> bytes:
    return piexif.dump(
        {
            "0th": {piexif.ImageIFD.Make: b"ServerMake"},
            "Exif": {piexif.ExifIFD.UserComment: b"ASCII\x00\x00\x00" + SERVER_MARKER.encode()},
        }
    )

def _insert_png_chunk(payload: bytes, chunk_type: bytes, data: bytes) -> bytes:
    """Insert a well-formed ancillary chunk just before the first IDAT."""
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    chunk = struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)
    offset = 8
    while offset + 8 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        if payload[offset + 4 : offset + 8] == b"IDAT":
            return payload[:offset] + chunk + payload[offset:]
        offset += 12 + length
    raise AssertionError("fixture PNG has no IDAT")


def _metadata_laden_png() -> bytes:
    """A PNG carrying tEXt, iTXt, EXIF (eXIf), and ICC (iCCP) server payloads."""
    from PIL.PngImagePlugin import PngInfo

    rand = random.Random(7)
    image = Image.frombytes("RGB", (16, 12), rand.randbytes(16 * 12 * 3))
    pnginfo = PngInfo()
    pnginfo.add_text("parameters", SERVER_MARKER)
    pnginfo.add_itxt("extra", SERVER_MARKER, lang="")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", pnginfo=pnginfo)
    payload = buffer.getvalue()
    payload = _insert_png_chunk(payload, b"eXIf", _server_exif_bytes())
    # iCCP: profile name, compression method byte, zlib-compressed profile.
    profile = bytes(range(128)) * 8
    return _insert_png_chunk(
        payload, b"iCCP", b"sRGB profile\x00\x00" + zlib.compress(profile)
    )


def _png_chunk_types(payload: bytes) -> list[str]:
    """Every ancillary chunk type in a PNG (signature-parsed, not scanned)."""
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    types = []
    offset = 8
    while offset + 8 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        types.append(payload[offset + 4 : offset + 8].decode("ascii"))
        offset += 12 + length
    return types


def _png_chunks(payload: bytes) -> dict[str, list[bytes]]:
    chunks: dict[str, list[bytes]] = {}
    offset = 8
    while offset + 8 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        ctype = payload[offset + 4 : offset + 8].decode("ascii")
        chunks.setdefault(ctype, []).append(payload[offset + 8 : offset + 8 + length])
        offset += 12 + length
    return chunks


def _jpeg_segment_markers(payload: bytes) -> list[int]:
    """Marker bytes of every JPEG segment (SOI through SOS)."""
    assert payload[:2] == b"\xff\xd8"
    markers = []
    offset = 2
    while offset + 1 < len(payload):
        if payload[offset] != 0xFF:
            break
        marker = payload[offset + 1]
        markers.append(marker)
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        if marker == 0xDA:  # start of scan: entropy-coded data follows
            break
        segment_length = struct.unpack(">H", payload[offset + 2 : offset + 4])[0]
        offset += 2 + segment_length
    return markers


def _jpeg_app_payloads(payload: bytes) -> list[bytes]:
    payloads = []
    offset = 2
    while offset + 3 < len(payload):
        if payload[offset] != 0xFF:
            break
        marker = payload[offset + 1]
        if 0xE0 <= marker <= 0xEF:
            segment_length = struct.unpack(">H", payload[offset + 2 : offset + 4])[0]
            payloads.append(payload[offset + 4 : offset + 2 + segment_length])
        if marker == 0xDA:
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        segment_length = struct.unpack(">H", payload[offset + 2 : offset + 4])[0]
        offset += 2 + segment_length
    return payloads


def _webp_chunk_fourccs(payload: bytes) -> list[str]:
    """Every RIFF fourcc in a WebP container."""
    assert payload[:4] == b"RIFF" and payload[8:12] == b"WEBP"
    fourccs = []
    offset = 12
    while offset + 8 <= len(payload):
        fourcc = payload[offset : offset + 4].decode("latin-1")
        size = struct.unpack("<I", payload[offset + 4 : offset + 8])[0]
        fourccs.append(fourcc)
        offset += 8 + size + (size % 2)
    return fourccs


def _webp_chunk_data(payload: bytes, fourcc: str) -> bytes | None:
    offset = 12
    while offset + 8 <= len(payload):
        cc = payload[offset : offset + 4].decode("latin-1")
        size = struct.unpack("<I", payload[offset + 4 : offset + 8])[0]
        if cc == fourcc:
            return payload[offset + 8 : offset + 8 + size]
        offset += 8 + size + (size % 2)
    return None


def _user_comment(payload: bytes) -> bytes:
    exif = piexif.load(payload)
    return exif["Exif"][piexif.ExifIFD.UserComment]


def _decode_user_comment(payload: bytes) -> str:
    comment = _user_comment(payload)
    if comment.startswith(b"ASCII\x00\x00\x00"):
        return comment[len(b"ASCII\x00\x00\x00") :].decode("ascii")
    if comment.startswith(b"UNICODE\x00"):
        return comment[len(b"UNICODE\x00") :].decode("utf-16-be")
    raise AssertionError(f"unknown UserComment charset prefix: {comment[:8]!r}")


LOSSY = ("webp", "jpeg", "avif")


class EncodeFormatTests(unittest.TestCase):
    """Container, dimensions, quality, and pixel-identity contracts."""

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_each_format_produces_its_container_extension_and_dimensions(self):
        source = _noise_png()
        for output_format, expected_magic in (
            ("png", b"\x89PNG"),
            ("webp", b"RIFF"),
            ("jpeg", b"\xff\xd8"),
            ("avif", b"ftyp"),
        ):
            with self.subTest(output_format=output_format):
                payload, extension = _encode(source, output_format)
                self.assertEqual(extension, _EXT_BY_FORMAT[output_format])
                if output_format == "avif":
                    self.assertIn(b"avif", payload[:16])  # ISOBMFF ftyp/brand
                    self.assertEqual(payload[4:8], b"ftyp")
                else:
                    self.assertTrue(payload.startswith(expected_magic))
                decoded = Image.open(io.BytesIO(payload))
                self.assertEqual(decoded.size, (64, 48))
                self.assertEqual(decoded.format, output_format.upper())

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_webp_quality_is_monotonic_on_noise(self):
        source = _noise_png()
        small, _ = _encode(source, "webp", quality=60)
        large, _ = _encode(source, "webp", quality=100)
        self.assertLess(len(small), len(large))

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_default_png_path_is_pixel_identical(self):
        source = _noise_png(mode="RGBA", seed=11)
        payload, extension = _encode(source, "png", preserve_metadata=False)
        self.assertEqual(extension, ".png")
        before = Image.open(io.BytesIO(source)).convert("RGBA")
        after = Image.open(io.BytesIO(payload)).convert("RGBA")
        self.assertEqual(list(before.getdata()), list(after.getdata()))

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_rgba_source_normalizes_for_jpeg(self):
        source = _noise_png(mode="RGBA")
        payload, _ = _encode(source, "jpeg")
        self.assertTrue(payload.startswith(b"\xff\xd8"))
        decoded = Image.open(io.BytesIO(payload))
        self.assertEqual(decoded.size, (64, 48))
        self.assertEqual(decoded.mode, "RGB")

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_corrupted_non_png_and_truncated_inputs_raise_sd_format_error(self):
        truncated = _noise_png()[:40]  # valid signature + partial IHDR
        valid_jpeg = io.BytesIO()
        Image.open(io.BytesIO(_noise_png())).save(valid_jpeg, format="JPEG")
        valid_webp = io.BytesIO()
        Image.open(io.BytesIO(_noise_png())).save(valid_webp, format="WEBP")
        valid_avif = io.BytesIO()
        Image.open(io.BytesIO(_noise_png())).save(valid_avif, format="AVIF")
        for label, payload in (
            ("garbage", b"this is not an image at all"),
            ("truncated", truncated),
            ("valid-jpeg", valid_jpeg.getvalue()),
            ("valid-webp", valid_webp.getvalue()),
            ("valid-avif", valid_avif.getvalue()),
        ):
            with self.subTest(payload=label):
                with self.assertRaises(SDError) as caught:
                    _encode(payload, "png")
                self.assertEqual(caught.exception.code, "sd_format_error")


class MetadataPolicyTests(unittest.TestCase):
    """ON embeds exactly our regenerated block; OFF is provably metadata-free."""

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_on_round_trips_the_parameters_text_per_format(self):
        expected = build_parameters_text(**_BASE_KWARGS)
        source = _metadata_laden_png()
        for output_format in ("png", *LOSSY):
            with self.subTest(output_format=output_format):
                payload, _ = _encode(source, output_format, preserve_metadata=True)
                decoded = Image.open(io.BytesIO(payload))
                if output_format == "png":
                    self.assertEqual(decoded.info.get("parameters"), expected)
                else:
                    self.assertIn("exif", decoded.info)
                    self.assertEqual(_decode_user_comment(decoded.info["exif"]), expected)

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_on_png_writes_only_its_own_text_chunk(self):
        source = _metadata_laden_png()
        payload, _ = _encode(source, "png", preserve_metadata=True)
        types = _png_chunk_types(payload)
        for forbidden in ("zTXt", "eXIf", "iCCP"):
            self.assertNotIn(forbidden, types)
        # Exactly one text-family chunk, carrying our regenerated block.
        text_chunks = [t for t in types if t in ("tEXt", "iTXt")]
        self.assertEqual(len(text_chunks), 1)
        keyword, _, value = _png_chunks(payload)[text_chunks[0]][0].partition(b"\x00")
        self.assertEqual(keyword, b"parameters")
        self.assertNotIn(SERVER_MARKER.encode(), value)
        self.assertIn(_PROMPT, value.decode("utf-8"))

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_png_text_chunk_family_follows_the_latin1_rule(self):
        # Container contract: Latin-1-safe text is written as tEXt, anything
        # else (the zh-tw prompts) as iTXt — both keyword-read by A1111.
        source = _noise_png()
        ascii_payload, _ = _encode(
            source, "png", prompt="a night market", negative_prompt="low quality"
        )
        self.assertIn("tEXt", _png_chunk_types(ascii_payload))
        unicode_payload, _ = _encode(source, "png")
        self.assertIn("iTXt", _png_chunk_types(unicode_payload))

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_on_lossy_carries_only_the_generated_user_comment(self):
        source = _metadata_laden_png()
        for output_format in LOSSY:
            with self.subTest(output_format=output_format):
                payload, _ = _encode(source, output_format, preserve_metadata=True)
                decoded = Image.open(io.BytesIO(payload))
                exif = piexif.load(decoded.info["exif"])
                self.assertEqual(
                    sorted(exif["Exif"]), [piexif.ExifIFD.UserComment],
                    msg="only our UserComment may ride along",
                )
                self.assertNotIn(b"ServerMake", payload)  # source Make tag gone
                self.assertNotIn(SERVER_MARKER.encode(), payload)  # source comment gone
                if output_format == "webp":
                    fourccs = _webp_chunk_fourccs(payload)
                    self.assertIn("EXIF", fourccs)
                    self.assertNotIn("ICCP", fourccs)
                elif output_format == "jpeg":
                    apps = _jpeg_app_payloads(payload)
                    self.assertTrue(any(app.startswith(b"Exif\x00\x00") for app in apps))
                    self.assertFalse(
                        any(app.startswith(b"ICC_PROFILE") for app in apps)
                    )
                else:  # avif
                    self.assertNotIn("xmp", decoded.info)

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_off_strips_every_metadata_payload(self):
        source = _metadata_laden_png()
        for output_format in ("png", *LOSSY):
            with self.subTest(output_format=output_format):
                payload, _ = _encode(source, output_format, preserve_metadata=False)
                self.assertNotIn(SERVER_MARKER.encode(), payload)
                decoded = Image.open(io.BytesIO(payload))
                if output_format == "png":
                    for forbidden in ("tEXt", "zTXt", "iTXt", "eXIf", "iCCP"):
                        self.assertNotIn(forbidden, _png_chunk_types(payload))
                elif output_format == "jpeg":
                    markers = _jpeg_segment_markers(payload)
                    app1 = [m for m in markers if m == 0xE1]
                    self.assertFalse(app1, msg="no APP1 (EXIF/XMP) segment")
                    self.assertFalse(
                        any(app.startswith(b"ICC_PROFILE") for app in _jpeg_app_payloads(payload))
                    )
                elif output_format == "webp":
                    fourccs = _webp_chunk_fourccs(payload)
                    self.assertNotIn("EXIF", fourccs)
                    self.assertNotIn("ICCP", fourccs)
                else:  # avif
                    for forbidden in ("exif", "xmp", "icc_profile"):
                        self.assertNotIn(forbidden, decoded.info)

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_user_comment_charset_prefixes_follow_the_text_family(self):
        source = _noise_png()
        with self.subTest(family="unicode"):
            payload, _ = _encode(source, "webp", preserve_metadata=True)
            comment = _user_comment(Image.open(io.BytesIO(payload)).info["exif"])
            self.assertTrue(comment.startswith(b"UNICODE\x00"))
        with self.subTest(family="ascii"):
            ascii_kwargs = dict(prompt="a night market", negative_prompt="low quality")
            payload, _ = _encode(source, "webp", preserve_metadata=True, **ascii_kwargs)
            comment = _user_comment(Image.open(io.BytesIO(payload)).info["exif"])
            self.assertTrue(comment.startswith(b"ASCII\x00\x00\x00"))

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_seedless_generation_omits_the_seed_entry(self):
        source = _noise_png()
        payload, _ = _encode(source, "png", seed=None, preserve_metadata=True)
        parameters = Image.open(io.BytesIO(payload)).info["parameters"]
        self.assertNotIn("Seed:", parameters)
        self.assertNotIn("None", parameters)

    @covers_requirement("art-output-format-pipeline::generation-metadata-is-embedded-when-preserved-and-provably-absent-when-not")
    def test_provenance_fields_render_into_the_text(self):
        source = _noise_png()
        payload, _ = _encode(
            source,
            "png",
            preserve_metadata=True,
            sampler="DPM++ 2M Karras",
            scheduler="karras",
            checkpoint="anima/animaika_v43.safetensors",
        )
        parameters = Image.open(io.BytesIO(payload)).info["parameters"]
        lines = parameters.splitlines()
        self.assertEqual(lines[0], _PROMPT)
        self.assertEqual(lines[1], f"Negative prompt: {_NEGATIVE}")
        self.assertIn("Steps: 30", lines[2])
        self.assertIn("Sampler name: DPM++ 2M Karras", lines[2])
        self.assertIn("Scheduler: karras", lines[2])
        self.assertIn("CFG scale: 7", lines[2])
        self.assertIn("Seed: 12345", lines[2])
        self.assertIn("Size: 64x48", lines[2])
        self.assertIn("Model: anima/animaika_v43.safetensors", lines[2])
