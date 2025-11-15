#!/usr/bin/env python
"""
Non-destructive proof-of-concept pipeline for image upscaling.

This script:
  - Scans `data/images/fighters` using the existing validate_image helper.
  - Selects low-quality candidates based on data-driven thresholds.
  - Copies originals into an isolated experiment folder.
  - Generates upscaled variants (Pillow/Lanczos as a stand-in for AI upscaling).
  - Builds a simple side-by-side HTML gallery for visual review.

Original images are never modified; all outputs are written under:
  data/processed/upscale_experiment/
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

from PIL import Image

# Ensure the repository root is on sys.path so we can import the existing
# validation helper regardless of how this script is invoked.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_fighter_images import validate_image


BASE_IMAGES_DIR = Path("data/images/fighters")
EXPERIMENT_ROOT = Path("data/processed/upscale_experiment")
ORIGINALS_DIR = EXPERIMENT_ROOT / "originals"
UPSCALED_DIR = EXPERIMENT_ROOT / "upscaled"
METADATA_PATH = EXPERIMENT_ROOT / "metadata.json"
GALLERY_PATH = EXPERIMENT_ROOT / "gallery.html"
PLACEHOLDER_IDS_PATH = Path("data/placeholder_fighter_ids.txt")


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}


@dataclass
class ImageMetrics:
    fighter_id: str
    filename: str
    width: int | None
    height: int | None
    entropy: float | None
    dominant_color_pct: float | None
    file_size_bytes: int | None
    file_size_kb: float | None
    is_placeholder: bool
    selected_for_experiment: bool
    reason: str
    upscaled_width: int | None
    upscaled_height: int | None


def load_placeholder_ids() -> set[str]:
    if not PLACEHOLDER_IDS_PATH.exists():
        return set()
    ids: set[str] = set()
    for line in PLACEHOLDER_IDS_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            ids.add(line)
    return ids


def iter_image_files(images_dir: Path) -> Iterable[Path]:
    for path in sorted(images_dir.iterdir()):
        if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file():
            yield path


def should_select_for_experiment(
    *,
    height: int | None,
    entropy: float | None,
    file_kb: float | None,
) -> tuple[bool, str]:
    """
    Decide whether an image should be included in the experiment.

    Thresholds are based on analysis of the current dataset and tuned to focus
    on genuinely weak photos rather than large, clean artwork:

      - "small" if:
          * height <= 340  (typical legacy photos are 200x300), OR
          * file_kb <= 30  (high compression / low-res)
      - "low entropy" if:
          * entropy < 6.5  (bottom tail of non-placeholder images)

    We require both small AND low-entropy so that very large but low-entropy
    graphics (banners, simple logos, etc.) are excluded from the experiment.
    """
    reasons: list[str] = []

    is_small = False
    if height is not None and height <= 340:
        is_small = True
        reasons.append("height<=340")
    if file_kb is not None and file_kb <= 30:
        is_small = True
        reasons.append("file_kb<=30")

    is_low_entropy = False
    if entropy is not None and entropy < 6.5:
        is_low_entropy = True
        reasons.append("entropy<6.5")

    if not (is_small and is_low_entropy):
        return False, ""

    return True, ",".join(reasons)


def ensure_experiment_dirs() -> None:
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    UPSCALED_DIR.mkdir(parents=True, exist_ok=True)


def upscale_image(
    src_path: Path,
    dest_path: Path,
    *,
    target_height: int = 600,
) -> tuple[int, int]:
    """
    Simple non-AI upscaling using Pillow's Lanczos resampling.

    This is intentionally lightweight and non-destructive; swapping in an
    AI model later should be straightforward while keeping the same I/O
    contract.
    """
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        width, height = img.size

        if height <= 0:
            # Fallback: do not attempt to upscale invalid dimensions.
            new_width, new_height = width, height
        else:
            scale = target_height / float(height)
            # Clamp scale to a reasonable range so we do not explode sizes.
            scale = max(1.0, min(scale, 4.0))
            new_width = int(width * scale)
            new_height = int(height * scale)

        upscaled = img.resize((new_width, new_height), Image.LANCZOS)
        # Preserve extension semantics but force JPEG settings when appropriate.
        dest_suffix = dest_path.suffix.lower()
        if dest_suffix in {".jpg", ".jpeg"}:
            upscaled.save(dest_path, format="JPEG", quality=92, optimize=True)
        else:
            upscaled.save(dest_path)

        return new_width, new_height


def build_gallery_html(metrics: List[ImageMetrics]) -> str:
    rows = []
    rows.append(
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        "<title>Upscale Experiment</title>"
        "<style>"
        "body{font-family:system-ui,Segoe UI,Roboto,sans-serif;background:#0b0b0b;color:#eee;}"
        "table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #333;padding:8px;font-size:14px;vertical-align:top;}"
        "img{max-height:260px;display:block;margin:0 auto;}"
        "th{background:#111;}"
        "tr:nth-child(even){background:#151515;}"
        ".meta{font-size:12px;color:#aaa;}"
        "</style></head><body>"
        "<h1>Upscale Experiment Gallery</h1>"
        "<p>This is a non-destructive proof-of-concept. "
        "Original images are on the left; upscaled variants on the right.</p>"
        "<table>"
        "<tr><th>Fighter ID</th><th>Original</th><th>Upscaled</th><th>Metrics</th></tr>"
    )

    for record in metrics:
        if not record.selected_for_experiment:
            continue
        original_rel = f"originals/{record.filename}"
        upscaled_rel = f"upscaled/{record.filename}"

        metrics_html = (
            f"<div class='meta'>"
            f"<div><strong>Original:</strong> {record.width}x{record.height}, "
            f"{(record.file_size_kb or 0):.1f} KB</div>"
            f"<div><strong>Entropy:</strong> {record.entropy}</div>"
            f"<div><strong>Dominant color %:</strong> {record.dominant_color_pct}</div>"
            f"<div><strong>Upscaled:</strong> "
            f"{record.upscaled_width}x{record.upscaled_height}</div>"
            f"<div><strong>Reason:</strong> {record.reason}</div>"
            f"</div>"
        )

        rows.append(
            "<tr>"
            f"<td>{record.fighter_id}</td>"
            f"<td><img src='{original_rel}' alt='original-{record.fighter_id}'></td>"
            f"<td><img src='{upscaled_rel}' alt='upscaled-{record.fighter_id}'></td>"
            f"<td>{metrics_html}</td>"
            "</tr>"
        )

    rows.append("</table></body></html>")
    return "\n".join(rows)


def run_experiment(limit: int | None = None) -> None:
    if not BASE_IMAGES_DIR.exists():
        raise SystemExit(f"Base images directory not found: {BASE_IMAGES_DIR}")

    ensure_experiment_dirs()

    placeholder_ids = load_placeholder_ids()
    all_metrics: list[ImageMetrics] = []
    selected_records: list[ImageMetrics] = []

    # Collect metrics for all images first.
    for image_path in iter_image_files(BASE_IMAGES_DIR):
        fighter_id = image_path.stem
        is_placeholder = fighter_id in placeholder_ids

        result = validate_image(image_path)
        details = result["details"]

        width = details.get("width")
        height = details.get("height")
        entropy = details.get("entropy")
        dominant_color_pct = details.get("dominant_color_pct")
        file_size_bytes = details.get("file_size")
        file_size_kb = float(file_size_bytes) / 1024.0 if file_size_bytes is not None else None

        selected = False
        reason = ""

        # Only consider non-placeholder images for this experiment.
        if not is_placeholder:
            selected, reason = should_select_for_experiment(
                height=height,
                entropy=entropy,
                file_kb=file_size_kb,
            )

        metrics = ImageMetrics(
            fighter_id=fighter_id,
            filename=image_path.name,
            width=width,
            height=height,
            entropy=entropy,
            dominant_color_pct=dominant_color_pct,
            file_size_bytes=file_size_bytes,
            file_size_kb=file_size_kb,
            is_placeholder=is_placeholder,
            selected_for_experiment=selected,
            reason=reason,
            upscaled_width=None,
            upscaled_height=None,
        )
        all_metrics.append(metrics)

        if selected:
            selected_records.append(metrics)

    # Sort selected records so the "worst" images are first: low entropy, small size, small height.
    def sort_key(record: ImageMetrics) -> tuple[float, float, int]:
        entropy = record.entropy if record.entropy is not None else 10.0
        file_kb = record.file_size_kb if record.file_size_kb is not None else 1000.0
        height = record.height if record.height is not None else 10_000
        return (entropy, file_kb, height)

    selected_records.sort(key=sort_key)

    if limit is not None:
        selected_records = selected_records[:limit]

    # Process selected records: copy originals and generate upscaled variants.
    for record in selected_records:
        src_path = BASE_IMAGES_DIR / record.filename
        dst_original = ORIGINALS_DIR / record.filename
        dst_upscaled = UPSCALED_DIR / record.filename

        # Copy original (non-destructive).
        shutil.copy2(src_path, dst_original)

        # Generate upscaled variant (non-AI placeholder).
        new_w, new_h = upscale_image(src_path, dst_upscaled)
        record.upscaled_width = new_w
        record.upscaled_height = new_h

    # Persist full metadata for transparency and future tuning.
    EXPERIMENT_ROOT.mkdir(parents=True, exist_ok=True)
    with METADATA_PATH.open("w", encoding="utf-8") as f:
        json.dump([asdict(m) for m in all_metrics], f, indent=2)

    gallery_html = build_gallery_html(selected_records)
    GALLERY_PATH.write_text(gallery_html, encoding="utf-8")

    print(f"Total images scanned: {len(all_metrics)}")
    print(f"Selected for experiment: {len(selected_records)}")
    print(f"Experiment root: {EXPERIMENT_ROOT}")
    print(f"- Originals: {ORIGINALS_DIR}")
    print(f"- Upscaled: {UPSCALED_DIR}")
    print(f"- Metadata: {METADATA_PATH}")
    print(f"- Gallery: {GALLERY_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a non-destructive upscaling experiment on low-quality fighter images.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of candidate images to include in the experiment (default: 100).",
    )
    args = parser.parse_args()
    run_experiment(limit=args.limit)


if __name__ == "__main__":
    main()
