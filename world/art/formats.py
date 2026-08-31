"""Local output-format conversion for generated art (art-output-format-pipeline).

The sd-webui wire format stays PNG; this module converts the transport PNG
bytes of a ``GeneratedImage`` to the configured store format (``png``,
``webp``, ``jpeg``, or ``avif``) before the worker writes the artifact. The
engine never asks the server for another format, so the request behavior and
the bounded transport checks of ``sd_worker`` stay untouched.

Two invariants shape every path here:

- **Sanitized by construction.** Pillow's JPEG/WebP/AVIF savers pass
  ``im.info["exif"]`` / ``im.info["icc_profile"]`` through when the argument
  is merely omitted, so omission is NOT stripping. Every encode works from a
  freshly allocated pixel copy whose ``.info`` is empty, and PNG saves receive
  only a newly created ``PngInfo`` — server-embedded text/EXIF/ICC can never
  propagate in either metadata mode.
- **Provenance is regenerated, never copied.** The A1111-shaped parameters
  text is assembled from the engine-known values the caller passes (the exact
  request the client sent), never from server-supplied chunks.
"""

import io

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from PIL.PngImagePlugin import PngInfo

import piexif

from world.art.sd_worker import SDError

# The four supported output formats and the single store-extension map live in
# server/conf/settings.py (ART_SD_OUTPUT_FORMAT / ART_SD_OUTPUT_EXTENSION);
# consumers must not re-derive it. The Pillow save format for each knob value.
_PILLOW_SAVE_FORMAT = {"png": "PNG", "webp": "WEBP", "jpeg": "JPEG", "avif": "AVIF"}

# The CLOSED set of every store extension any supported format can produce.
# A store mid-way through a format switch legitimately holds mixed
# extensions, so the presenter and the media route accept this whole set —
# never the currently configured extension alone. This is a set of extensions,
# not a format-to-extension map; the map itself lives in settings.
STORE_EXTENSIONS = frozenset({".png", ".webp", ".jpg", ".avif"})

# EXIF UserComment charset prefixes, mirroring the reference plugin's
# two-family rule: pure-ASCII text carries `ASCII\0\0\0` + the ASCII bytes;
# anything else (zh-tw prompts are non-ASCII) carries `UNICODE\0` + UTF-16 BE,
# the EXIF-spec representation ExifTool and A1111 decode correctly.
_CHARSET_ASCII_PREFIX = b"ASCII\x00\x00\x00"
_CHARSET_UNICODE_PREFIX = b"UNICODE\x00"


def build_parameters_text(
    *,
    prompt: str,
    negative_prompt: str,
    steps: int,
    cfg_scale: float,
    sampler: str | None,
    scheduler: str | None,
    width: int,
    height: int,
    seed: int | None,
    checkpoint: str | None,
) -> str:
    """Assemble the A1111-shaped generation-parameters text.

    Layout: the prompt on its own line, then ``Negative prompt: ...``, then a
    comma-separated single line of generation fields. A field with no known
    value is OMITTED entirely (never a ``None``/sentinel token): the ``Seed:``
    entry disappears when the server reported no seed, the optional
    sampler/scheduler entries only when configured, and the ``Model:`` entry
    only when a checkpoint is configured.
    """
    fields = [f"Steps: {steps}"]
    if sampler:
        fields.append(f"Sampler name: {sampler}")
    if scheduler:
        fields.append(f"Scheduler: {scheduler}")
    fields.append(f"CFG scale: {cfg_scale:g}")
    if seed is not None:
        fields.append(f"Seed: {seed}")
    fields.append(f"Size: {width}x{height}")
    if checkpoint:
        fields.append(f"Model: {checkpoint}")
    return f"{prompt}\nNegative prompt: {negative_prompt}\n{', '.join(fields)}"


def _user_comment_bytes(text: str) -> bytes:
    """Charset-prefixed EXIF UserComment payload (reference two-family rule)."""
    try:
        body = text.encode("ascii")
    except UnicodeEncodeError:
        return _CHARSET_UNICODE_PREFIX + text.encode("utf-16-be")
    return _CHARSET_ASCII_PREFIX + body


def _exif_bytes(parameters: str) -> bytes:
    """Freshly generated piexif payload carrying only our UserComment."""
    return piexif.dump({"Exif": {piexif.ExifIFD.UserComment: _user_comment_bytes(parameters)}})


def _decode_transport_png(png_bytes: bytes) -> Image.Image:
    """Decode the transport bytes and return a sanitized pixel copy.

    The copy is freshly allocated with an empty ``.info``; the decoded
    container must be PNG — bytes that decode as a valid JPEG/WebP are
    rejected exactly like garbage (the transport contract is PNG), and a
    truncated file fails at ``load()`` before any output is produced.
    """
    try:
        with Image.open(io.BytesIO(png_bytes)) as opened:
            source_format = opened.format
            opened.load()
            # convert(same mode) is documented to return a freshly allocated
            # copy of the pixels; emptying .info completes the sanitization.
            image = opened.convert(opened.mode)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise SDError(
            "sd_format_error", f"transport bytes are not a decodable PNG: {exc}"
        ) from exc
    if source_format != "PNG":
        raise SDError(
            "sd_format_error",
            f"transport bytes decoded as {source_format or 'unknown'}, expected PNG",
        )
    # Fresh pixel copy with no source metadata (the convert above allocated
    # it; Pillow's decoded .info is dropped here).
    image.info = {}
    return image


def encode(
    png_bytes: bytes,
    *,
    prompt: str,
    negative_prompt: str,
    steps: int,
    cfg_scale: float,
    sampler: str | None,
    scheduler: str | None,
    width: int,
    height: int,
    seed: int | None,
    checkpoint: str | None,
    output_format: str,
    quality: int,
    preserve_metadata: bool,
) -> tuple[bytes, str]:
    """Convert transport PNG bytes to the configured output format.

    Returns ``(encoded_bytes, store_extension)`` where the extension is the
    derived ``settings.ART_SD_OUTPUT_EXTENSION`` (the single closed
    format-to-extension map lives in settings; consumers never re-derive it).
    ``quality`` affects the lossy formats only; the ``png`` path is a lossless
    re-save (pixel-identical) that ignores it. Any transport-decode failure,
    non-PNG container, or encoder failure raises ``SDError`` with the bounded
    code ``sd_format_error`` before any output is produced.
    """
    try:
        save_format = _PILLOW_SAVE_FORMAT[output_format]
    except KeyError as exc:
        raise SDError(
            "sd_format_error", f"unsupported output format: {output_format!r}"
        ) from exc

    image = _decode_transport_png(png_bytes)

    parameters: str | None = None
    if preserve_metadata:
        parameters = build_parameters_text(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler=sampler,
            scheduler=scheduler,
            width=width,
            height=height,
            seed=seed,
            checkpoint=checkpoint,
        )

    buffer = io.BytesIO()
    try:
        if save_format == "PNG":
            # Lossless re-save; a fresh PngInfo (empty when OFF) means no
            # source text chunk can ride along. Pillow picks tEXt for
            # latin-1-safe text and iTXt otherwise — both carry the
            # `parameters` keyword that A1111 readers extract.
            pnginfo = PngInfo()
            if parameters is not None:
                pnginfo.add_text("parameters", parameters)
            image.save(buffer, format="PNG", pnginfo=pnginfo)
        else:
            save_image = image
            if save_format == "JPEG":
                # JPEG accepts no alpha; Pillow raises OSError on RGBA.
                save_image = image.convert("RGB")
                save_image.info = {}
            save_kwargs: dict[str, object] = {"quality": quality}
            if parameters is not None:
                save_kwargs["exif"] = _exif_bytes(parameters)
            save_image.save(buffer, format=save_format, **save_kwargs)
    except SDError:
        raise
    except (OSError, ValueError) as exc:
        raise SDError(
            "sd_format_error", f"local {output_format} encoding failed: {exc}"
        ) from exc
    return buffer.getvalue(), settings.ART_SD_OUTPUT_EXTENSION
