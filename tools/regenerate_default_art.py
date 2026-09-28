"""One-shot maintenance script whose generated default portraits are committed.

The call-site model pin uses permissively licensed isnet-anime rather than the
runtime's non-commercial BRIA weights. Run from the repository with uv run
--locked python tools/regenerate_default_art.py. Missing weights require both
--allow-download and ART_REMBG_DOWNLOAD_ENABLED=true. --allow-bria deliberately
uses the configured model instead and must not be used for committed defaults.
"""

import argparse
import io
import os
from pathlib import Path
import sys
import tempfile


DESCRIPTIONS = {
    "man": ("character", "An adult human man with short hair, wearing a travel-worn floor-length coat closed over a tunic and boots, standing with feet together and arms at his sides."),
    "woman": ("character", "An adult human woman with long hair, wearing a modest ankle-length traveling dress and boots, standing with arms at her sides."),
    "boy": ("character", "A young human boy with short hair, fully clothed in a floor-length coat, tunic, trousers and boots, standing with feet together and arms at his sides."),
    "girl": ("character", "A young human girl with braided hair, fully clothed in a modest ankle-length dress and boots, standing with arms at her sides."),
    "elder": ("character", "An elderly human with a lined face, wearing ankle-length layered robes and boots, standing with arms at their sides."),
    "monster_anon": ("monster", "An anonymous humanoid monster with a mysterious face beneath a hood, wearing a closed ankle-length cloak, standing with arms beneath the cloak."),
}


def main() -> None:
    """Generate selected defaults through the runtime seams, then publish them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", choices=tuple(DESCRIPTIONS))
    parser.add_argument("--allow-bria", action="store_true", help="Use the ambient model instead of the permissive pin; not for committed defaults")
    parser.add_argument("--allow-download", action="store_true", help="Consent to missing model downloads when enabled in settings")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()
    from django.conf import settings
    from django.test import override_settings
    from PIL import Image

    from world.art import cutout, formats
    from world.art.fallback_keys import FALLBACK_KEYS, FALLBACK_MAX_FILE_BYTES
    from world.art.sd_worker import resolve_sd_client
    from world.art.subjects import ArtSubject, ArtSubjectKind
    from world.observability import log_info

    if set(DESCRIPTIONS) != set(FALLBACK_KEYS):
        parser.error("authored descriptions do not match the closed fallback vocabulary")
    model = str(settings.ART_REMBG_MODEL) if args.allow_bria else "isnet-anime"
    download = args.allow_download and bool(settings.ART_REMBG_DOWNLOAD_ENABLED)
    model_dir = Path(settings.ART_REMBG_MODEL_DIR)
    if not download and not any(path.is_file() for path in (
        model_dir / f"{model}.onnx",
        model_dir / "models" / model / f"{model}.onnx",
    )):
        parser.error(f"missing {model} weights under {model_dir}; pre-place them or enable downloads and pass --allow-download")
    destination = root / "web/static/art/defaults"
    with override_settings(ART_REMBG_MODEL=model, ART_REMBG_DOWNLOAD_ENABLED=download):
        client = resolve_sd_client()
        for key in ([args.key] if args.key else DESCRIPTIONS):
            kind, description = DESCRIPTIONS[key]
            subject = ArtSubject(ArtSubjectKind[kind.upper()], key)
            log_info("default_art_generation_started", context={"key": key, "model": model})
            print(f"Generating {key} with {model}", flush=True)
            image = client.generate(subject, description)
            png = cutout.remove_background(image.data)
            encoded, _extension = formats.encode(
                png, prompt=image.prompt, negative_prompt=image.negative_prompt,
                steps=image.steps, cfg_scale=image.cfg_scale, sampler=image.sampler,
                scheduler=image.scheduler, width=image.width, height=image.height,
                seed=image.seed, checkpoint=image.checkpoint, output_format="webp",
                quality=int(settings.ART_SD_OUTPUT_QUALITY),
                preserve_metadata=bool(settings.ART_SD_PRESERVE_GENERATION_METADATA),
            )
            with Image.open(io.BytesIO(encoded)) as decoded:
                decoded.load()
                if decoded.mode != "RGBA":
                    raise ValueError(f"{key}: encoded default has no RGBA alpha channel")
            if len(encoded) >= FALLBACK_MAX_FILE_BYTES:
                raise ValueError(f"{key}: {len(encoded)} bytes reaches the {FALLBACK_MAX_FILE_BYTES} byte bound; lower ART_SD_OUTPUT_QUALITY")
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=destination, delete=False) as output:
                    temporary = Path(output.name)
                    output.write(encoded)
                temporary.replace(destination / f"{key}.webp")
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            log_info("default_art_generation_done", context={"key": key, "model": model, "seed": image.seed, "bytes": len(encoded)})
            print(f"Wrote {key}: seed={image.seed}, bytes={len(encoded)}", flush=True)


if __name__ == "__main__":
    main()
