#!/usr/bin/env python
"""Audit fighter images to ensure database paths and filesystem assets stay in sync."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from backend.db.connection import get_session
from backend.db.models import Fighter

IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp")
console = Console()


def _find_local_image(images_dir: Path, fighter_id: str) -> Path | None:
    """Return the first matching image path for ``fighter_id`` if it exists."""

    for extension in IMAGE_EXTENSIONS:
        candidate = images_dir / f"{fighter_id}.{extension}"
        if candidate.exists():
            return candidate
    return None


async def audit_fighter_images(*, show_limit: int) -> None:
    """Inspect the database and filesystem for missing or unsynced fighter images."""

    images_dir = Path("data/images/fighters")
    if not images_dir.exists():
        console.print(
            f"[red]Image directory '{images_dir}' does not exist. Skipping audit.[/red]"
        )
        return

    async with get_session() as session:
        result = await session.execute(
            select(Fighter.id, Fighter.name, Fighter.image_url).order_by(Fighter.name)
        )
        fighters = [(row.id, row.name, row.image_url) for row in result.all()]

    missing_disk: list[tuple[str, str, str]] = []
    disk_only: list[tuple[str, str, str]] = []
    still_missing: list[tuple[str, str]] = []

    for fighter_id, name, image_url in fighters:
        local_file = _find_local_image(images_dir, fighter_id)
        has_url = bool(image_url)
        has_file = local_file is not None

        if has_url and not has_file:
            missing_disk.append((fighter_id, name, image_url or ""))
        elif not has_url and has_file:
            disk_only.append((fighter_id, name, local_file.name))
        elif not has_url and not has_file:
            still_missing.append((fighter_id, name))

    console.print(f"[bold]Total fighters audited:[/bold] {len(fighters)}")
    console.print(f"[yellow]Missing files for existing image_url:[/yellow] {len(missing_disk)}")
    console.print(f"[cyan]Images on disk but DB image_url is NULL:[/cyan] {len(disk_only)}")
    console.print(f"[red]Still missing both DB entry and local file:[/red] {len(still_missing)}\n")

    def _render_table(
        title: str,
        rows: list[tuple[str, ...]],
        headers: tuple[str, ...],
    ) -> None:
        if not rows:
            return
        table = Table(*headers, title=title)
        for row in (rows if show_limit == 0 else rows[:show_limit]):
            table.add_row(*row)
        console.print(table)
        if show_limit and len(rows) > show_limit:
            console.print(
                f"... {len(rows) - show_limit} additional entries not shown. Use --show-limit 0 to display all."
            )

    _render_table(
        "DB image_url without filesystem asset",
        [(fid, name, path) for fid, name, path in missing_disk],
        ("Fighter ID", "Name", "DB Path"),
    )
    _render_table(
        "Filesystem image missing DB reference",
        [(fid, name, path) for fid, name, path in disk_only],
        ("Fighter ID", "Name", "Filename"),
    )
    _render_table(
        "Fighters missing both DB image_url and local file",
        [(fid, name) for fid, name in still_missing],
        ("Fighter ID", "Name"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit fighter images and flag mismatches between DB and disk."
    )
    parser.add_argument(
        "--show-limit",
        type=int,
        default=20,
        help="Number of rows to display per table (0 shows all).",
    )
    return parser.parse_args()


async def _async_main() -> None:
    args = parse_args()
    load_dotenv()
    await audit_fighter_images(show_limit=args.show_limit)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
