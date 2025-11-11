"""
Apply manual location overrides from JSON file.

Usage:
    python scripts/apply_manual_overrides.py --file data/manual/location_overrides.json
    python scripts/apply_manual_overrides.py --file data/manual/location_overrides.json --dry-run
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import click
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter


async def apply_override(
    session: AsyncSession, override: dict, dry_run: bool = False
) -> tuple[bool, str]:
    """
    Apply a single location override to a fighter.

    Returns:
        (success: bool, message: str)
    """
    fighter_id = override.get("fighter_id")
    fighter_name = override.get("fighter_name")

    if not fighter_id:
        return False, "Missing fighter_id"

    # Fetch fighter
    result = await session.execute(select(Fighter).where(Fighter.id == fighter_id))
    fighter = result.scalar_one_or_none()

    if not fighter:
        return False, f"Fighter not found: {fighter_id}"

    # Verify name matches (safety check)
    if fighter_name and fighter.name != fighter_name:
        return (
            False,
            f"Name mismatch: DB has '{fighter.name}', override has '{fighter_name}'",
        )

    if dry_run:
        return True, f"Would apply override to {fighter.name}"

    # Apply field overrides
    fields = override.get("fields", {})
    applied_fields = []

    if "birthplace" in fields:
        fighter.birthplace = fields["birthplace"]
        applied_fields.append("birthplace")

        # Parse city and country if provided as compound
        if "," in fields["birthplace"]:
            parts = fields["birthplace"].split(",")
            fighter.birthplace_city = parts[0].strip()
            fighter.birthplace_country = ",".join(parts[1:]).strip()

    if "birthplace_city" in fields:
        fighter.birthplace_city = fields["birthplace_city"]
        applied_fields.append("birthplace_city")

    if "birthplace_country" in fields:
        fighter.birthplace_country = fields["birthplace_country"]
        applied_fields.append("birthplace_country")

    if "nationality" in fields:
        fighter.nationality = fields["nationality"]
        applied_fields.append("nationality")

    if "training_gym" in fields:
        fighter.training_gym = fields["training_gym"]
        applied_fields.append("training_gym")

    if "training_city" in fields:
        fighter.training_city = fields["training_city"]
        applied_fields.append("training_city")

    if "training_country" in fields:
        fighter.training_country = fields["training_country"]
        applied_fields.append("training_country")

    if "fighting_out_of" in fields:
        fighter.fighting_out_of = fields["fighting_out_of"]
        applied_fields.append("fighting_out_of")

    # Set do_not_auto_update flag if specified
    do_not_auto_update = override.get("do_not_auto_update", True)
    if do_not_auto_update:
        fighter.needs_manual_review = True

    # Update metadata
    fighter.ufc_com_match_method = "manual"
    fighter.ufc_com_match_confidence = 100.0
    fighter.ufc_com_scraped_at = datetime.utcnow()

    await session.commit()

    return True, f"Applied override to {fighter.name}: {', '.join(applied_fields)}"


@click.command()
@click.option(
    "--file",
    "override_file",
    type=click.Path(exists=True),
    required=True,
    help="Path to JSON file with manual overrides",
)
@click.option(
    "--dry-run", is_flag=True, help="Preview changes without applying them"
)
def main(override_file: str, dry_run: bool):
    """
    Apply manual location overrides from JSON file.

    The JSON file should have this structure:
    {
      "overrides": [
        {
          "fighter_id": "abc123",
          "fighter_name": "Conor McGregor",
          "override_reason": "UFC.com data incorrect, verified via Wikipedia",
          "fields": {
            "birthplace": "Crumlin, Dublin, Ireland",
            "training_gym": "SBG Ireland"
          },
          "do_not_auto_update": true,
          "verified_by": "admin",
          "verified_at": "2025-01-15"
        }
      ]
    }
    """
    asyncio.run(run_apply_overrides(override_file, dry_run))


async def run_apply_overrides(override_file: str, dry_run: bool):
    """Main override application logic."""
    click.echo(f"\n{'='*60}")
    click.echo("APPLY MANUAL LOCATION OVERRIDES")
    click.echo(f"{'='*60}\n")

    if dry_run:
        click.echo("🔍 DRY RUN MODE - No changes will be made\n")

    # Load overrides file
    try:
        with open(override_file) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error parsing JSON file: {e}")
        return
    except Exception as e:
        click.echo(f"❌ Error reading file: {e}")
        return

    overrides = data.get("overrides", [])
    if not overrides:
        click.echo("⚠️  No overrides found in file")
        return

    click.echo(f"📋 Found {len(overrides)} overrides to apply\n")

    stats = {
        "total": len(overrides),
        "applied": 0,
        "failed": 0,
    }

    async with get_session() as session:
        for i, override in enumerate(overrides, 1):
            fighter_name = override.get("fighter_name", "Unknown")
            override_reason = override.get("override_reason", "No reason provided")

            if dry_run:
                click.echo(
                    f"[{i}/{stats['total']}] {fighter_name}: {override_reason}"
                )
                fields = override.get("fields", {})
                for field, value in fields.items():
                    click.echo(f"    {field}: {value}")
                click.echo()
                stats["applied"] += 1
                continue

            success, message = await apply_override(session, override, dry_run)

            if success:
                stats["applied"] += 1
                click.echo(
                    f"✅ [{i}/{stats['total']}] {fighter_name}: {override_reason}"
                )
                click.echo(f"    {message}\n")
            else:
                stats["failed"] += 1
                click.echo(f"❌ [{i}/{stats['total']}] {fighter_name}: {message}\n")

    # Print summary
    click.echo(f"{'='*60}")
    click.echo("SUMMARY")
    click.echo(f"{'='*60}")
    click.echo(f"Total overrides:         {stats['total']}")
    click.echo(f"Applied successfully:    {stats['applied']}")
    click.echo(f"Failed:                  {stats['failed']}")
    click.echo(f"{'='*60}\n")

    if dry_run:
        click.echo("ℹ️  This was a dry run. Run without --dry-run to apply changes.\n")


if __name__ == "__main__":
    main()
