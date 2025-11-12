"""
Batch orchestration helper for the UFC.com athlete detail spider.

This script reads the scraped UFC athletes list, slices it into polite-sized
batches, and executes the detail spider sequentially with configurable pauses.
It is especially useful for the first full scrape (~3k fighters) where we need
to avoid hammering UFC.com while still making steady progress.

Usage examples:
    python scripts/scrape_ufc_com_batched.py
    python scripts/scrape_ufc_com_batched.py --batch-size 75 --batch-delay 45
    python scripts/scrape_ufc_com_batched.py --slugs conor-mcgregor,israel-adesanya
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

import click

DEFAULT_INPUT = "data/processed/ufc_com_athletes_list.jsonl"
DEFAULT_OUTPUT_DIR = "data/processed/ufc_com_fighters"
DEFAULT_LOG_DIR = "data/logs"
DEFAULT_SCRAPY_BIN = ".venv/bin/scrapy"


def _normalize_slug(slug: str) -> str:
    return slug.strip().lower()


def _load_slugs_from_jsonl(path: Path) -> list[str]:
    if not path.exists():
        raise click.BadParameter(f"Input file not found: {path}")

    slugs: list[str] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"Failed to parse JSONL line: {exc}") from exc
            slug = (record.get("slug") or "").strip()
            if slug:
                slugs.append(slug)
    return slugs


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize_slug(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _filter_existing(slugs: Sequence[str], output_dir: Path, skip_existing: bool) -> list[str]:
    if not skip_existing:
        return list(slugs)

    remaining: list[str] = []
    for slug in slugs:
        output_file = output_dir / f"{slug}.json"
        if output_file.exists():
            continue
        remaining.append(slug)
    return remaining


def _resolve_scrapy_bin(scrapy_bin: str) -> str:
    path = Path(scrapy_bin)
    if path.exists():
        return str(path)

    resolved = shutil.which(scrapy_bin)
    if resolved:
        return resolved

    raise click.ClickException(
        f"Unable to find scrapy executable at '{scrapy_bin}'. "
        "Pass --scrapy-bin or ensure Scrapy is on PATH."
    )


def _run_batch(
    slugs: Sequence[str],
    batch_num: int,
    total_batches: int,
    scrapy_bin: str,
    log_dir: Path,
    env: dict[str, str],
) -> None:
    slug_arg = ",".join(slugs)
    batch_label = f"{batch_num:03d}-of-{total_batches:03d}"
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"ufc_com_batch_{batch_label}_{timestamp}.log"

    cwd = Path.cwd()
    try:
        log_display = log_path.relative_to(cwd)
    except ValueError:
        log_display = log_path

    click.echo(
        f"🚀 Batch {batch_num}/{total_batches}: {len(slugs)} fighters "
        f"(log: {log_display})"
    )

    command = [
        scrapy_bin,
        "crawl",
        "ufc_com_athlete_detail",
        "-a",
        f"slugs={slug_arg}",
    ]

    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        assert process.stdout is not None  # For type checkers
        try:
            for line in process.stdout:
                sys.stdout.write(line)
                log_handle.write(line)
        except KeyboardInterrupt:
            process.terminate()
            raise
        finally:
            process.wait()

        if process.returncode != 0:
            raise click.ClickException(
                f"Batch {batch_num}/{total_batches} failed with exit code {process.returncode}."
            )


@click.command()
@click.option(
    "--input-file",
    "-i",
    type=click.Path(exists=True, dir_okay=False),
    default=DEFAULT_INPUT,
    show_default=True,
    help="Path to JSONL file produced by the ufc_com_athletes spider.",
)
@click.option(
    "--slugs",
    "-s",
    multiple=True,
    help="Additional comma-separated slugs to include (can be repeated).",
)
@click.option(
    "--batch-size",
    type=click.IntRange(1, 200),
    default=100,
    show_default=True,
    help="How many fighters to process per Scrapy invocation.",
)
@click.option(
    "--batch-delay",
    type=click.FloatRange(0, None),
    default=60.0,
    show_default=True,
    help="Seconds to wait between batches.",
)
@click.option(
    "--limit",
    type=click.IntRange(1, None),
    help="Optional cap on total fighters processed.",
)
@click.option(
    "--skip-existing/--no-skip-existing",
    default=True,
    show_default=True,
    help="Skip fighters that already have JSON output files.",
)
@click.option(
    "--scrapy-bin",
    default=DEFAULT_SCRAPY_BIN,
    show_default=True,
    help="Path or executable name for Scrapy.",
)
@click.option(
    "--log-dir",
    default=DEFAULT_LOG_DIR,
    show_default=True,
    help="Directory for batch log files.",
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Do not abort the run if a batch fails; continue with the next one.",
)
def main(
    input_file: str,
    slugs: tuple[str, ...],
    batch_size: int,
    batch_delay: float,
    limit: int | None,
    skip_existing: bool,
    scrapy_bin: str,
    log_dir: str,
    continue_on_error: bool,
):
    """Run the UFC.com detail spider in polite batches."""
    base_slugs = _load_slugs_from_jsonl(Path(input_file))

    extra_slugs: list[str] = []
    for chunk in slugs:
        if not chunk:
            continue
        extra_slugs.extend(part.strip() for part in chunk.split(",") if part.strip())

    all_slugs = _dedupe_preserve_order([*base_slugs, *extra_slugs])
    if not all_slugs:
        raise click.ClickException("No fighter slugs found to process.")

    output_dir = Path(DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    remaining = _filter_existing(all_slugs, output_dir, skip_existing)
    if limit:
        remaining = remaining[:limit]

    if not remaining:
        click.echo("All fighters already scraped. Nothing to do.")
        return

    total_batches = math.ceil(len(remaining) / batch_size)
    click.echo(
        f"🧮 Prepared {len(remaining)} fighters "
        f"→ {total_batches} batches (size={batch_size}, delay={batch_delay}s)"
    )

    scrapy_executable = _resolve_scrapy_bin(scrapy_bin)
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ".")

    log_dir_path = Path(log_dir)
    start_time = time.perf_counter()

    for idx in range(0, len(remaining), batch_size):
        batch_num = idx // batch_size + 1
        batch_slugs = remaining[idx : idx + batch_size]
        batch_start = time.perf_counter()

        try:
            _run_batch(
                batch_slugs,
                batch_num,
                total_batches,
                scrapy_executable,
                log_dir_path,
                env,
            )
        except click.ClickException as exc:
            click.echo(f"❌ {exc}")
            if not continue_on_error:
                raise
        except KeyboardInterrupt:
            click.echo("\nInterrupted by user. Exiting…")
            raise

        batch_duration = time.perf_counter() - batch_start
        remaining_batches = total_batches - batch_num

        click.echo(
            f"✅ Completed batch {batch_num}/{total_batches} in {batch_duration:.1f}s. "
            f"{remaining_batches} batches remaining."
        )

        if batch_num < total_batches and batch_delay > 0:
            click.echo(f"⏳ Sleeping {batch_delay:.1f}s before next batch…")
            time.sleep(batch_delay)

    total_duration = time.perf_counter() - start_time
    click.echo(f"🎉 All batches finished in {timedelta(seconds=int(total_duration))}.")


if __name__ == "__main__":
    main()
