"""
Monitor location data health and completeness.

Usage:
    python scripts/monitor_location_data_health.py
    python scripts/monitor_location_data_health.py --json  # Output as JSON
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta

import click
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter


async def get_health_stats(session: AsyncSession) -> dict:
    """
    Gather health statistics for location data.

    Returns dict with:
        - total_fighters: int
        - with_birthplace: int
        - with_training_gym: int
        - with_nationality: int
        - with_fighting_out_of: int
        - needs_manual_review: int
        - stale_data_30d: int
        - stale_data_90d: int
        - never_scraped: int
        - recent_changes_7d: int
    """
    stats = {}

    # Total fighters
    result = await session.execute(select(func.count(Fighter.id)))
    stats["total_fighters"] = result.scalar()

    # Fighters with birthplace data
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.birthplace.isnot(None))
    )
    stats["with_birthplace"] = result.scalar()
    stats["with_birthplace_pct"] = (
        stats["with_birthplace"] / stats["total_fighters"] * 100
        if stats["total_fighters"]
        else 0
    )

    # Fighters with training gym data
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.training_gym.isnot(None))
    )
    stats["with_training_gym"] = result.scalar()
    stats["with_training_gym_pct"] = (
        stats["with_training_gym"] / stats["total_fighters"] * 100
        if stats["total_fighters"]
        else 0
    )

    # Fighters with nationality data
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.nationality.isnot(None))
    )
    stats["with_nationality"] = result.scalar()
    stats["with_nationality_pct"] = (
        stats["with_nationality"] / stats["total_fighters"] * 100
        if stats["total_fighters"]
        else 0
    )

    # Fighters with fighting_out_of data
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.fighting_out_of.isnot(None))
    )
    stats["with_fighting_out_of"] = result.scalar()
    stats["with_fighting_out_of_pct"] = (
        stats["with_fighting_out_of"] / stats["total_fighters"] * 100
        if stats["total_fighters"]
        else 0
    )

    # Fighters needing manual review
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.needs_manual_review == True)  # noqa: E712
    )
    stats["needs_manual_review"] = result.scalar()

    # Never scraped from UFC.com
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.ufc_com_scraped_at.is_(None))
    )
    stats["never_scraped"] = result.scalar()

    # Stale data (>30 days)
    cutoff_30d = datetime.utcnow() - timedelta(days=30)
    result = await session.execute(
        select(func.count(Fighter.id)).where(
            Fighter.ufc_com_scraped_at.isnot(None),
            Fighter.ufc_com_scraped_at < cutoff_30d,
        )
    )
    stats["stale_data_30d"] = result.scalar()

    # Stale data (>90 days)
    cutoff_90d = datetime.utcnow() - timedelta(days=90)
    result = await session.execute(
        select(func.count(Fighter.id)).where(
            Fighter.ufc_com_scraped_at.isnot(None),
            Fighter.ufc_com_scraped_at < cutoff_90d,
        )
    )
    stats["stale_data_90d"] = result.scalar()

    # Recent changes (last 7 days)
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    result = await session.execute(
        select(func.count(Fighter.id)).where(
            Fighter.ufc_com_scraped_at.isnot(None),
            Fighter.ufc_com_scraped_at >= cutoff_7d,
        )
    )
    stats["recent_changes_7d"] = result.scalar()

    # UFC.com matched fighters
    result = await session.execute(
        select(func.count(Fighter.id)).where(Fighter.ufc_com_slug.isnot(None))
    )
    stats["with_ufc_com_slug"] = result.scalar()
    stats["with_ufc_com_slug_pct"] = (
        stats["with_ufc_com_slug"] / stats["total_fighters"] * 100
        if stats["total_fighters"]
        else 0
    )

    # Active fighters (fought in last 6 months)
    cutoff_6mo = datetime.utcnow().date() - timedelta(days=180)
    result = await session.execute(
        select(func.count(Fighter.id)).where(
            Fighter.last_fight_date.isnot(None),
            Fighter.last_fight_date >= cutoff_6mo,
        )
    )
    stats["active_fighters_6mo"] = result.scalar()

    return stats


def check_health_thresholds(stats: dict) -> tuple[bool, list[str]]:
    """
    Check if health metrics meet minimum thresholds.

    Returns:
        (is_healthy: bool, issues: list[str])
    """
    issues = []

    # Minimum coverage thresholds
    if stats["with_birthplace_pct"] < 60:
        issues.append(
            f"⚠️  Birthplace coverage is low: {stats['with_birthplace_pct']:.1f}% "
            f"(target: 60%)"
        )

    if stats["with_nationality_pct"] < 80:
        issues.append(
            f"⚠️  Nationality coverage is low: {stats['with_nationality_pct']:.1f}% "
            f"(target: 80%)"
        )

    # Stale data warnings
    if stats["stale_data_90d"] > 100:
        issues.append(
            f"⚠️  {stats['stale_data_90d']} fighters have stale data (>90 days old)"
        )

    # Manual review queue
    if stats["needs_manual_review"] > 50:
        issues.append(
            f"⚠️  {stats['needs_manual_review']} fighters flagged for manual review"
        )

    # Never scraped
    if stats["never_scraped"] > 500:
        issues.append(
            f"⚠️  {stats['never_scraped']} fighters never scraped from UFC.com"
        )

    return len(issues) == 0, issues


def format_health_report(stats: dict, issues: list[str]) -> str:
    """
    Format health statistics as human-readable report.
    """
    report = []
    report.append("\n" + "=" * 70)
    report.append("LOCATION DATA HEALTH REPORT")
    report.append("=" * 70 + "\n")

    # Overall Coverage
    report.append("📊 OVERALL COVERAGE")
    report.append("-" * 70)
    report.append(f"Total fighters:              {stats['total_fighters']:,}")
    report.append(
        f"With birthplace data:        {stats['with_birthplace']:,} "
        f"({stats['with_birthplace_pct']:.1f}%)"
    )
    report.append(
        f"With training gym data:      {stats['with_training_gym']:,} "
        f"({stats['with_training_gym_pct']:.1f}%)"
    )
    report.append(
        f"With nationality data:       {stats['with_nationality']:,} "
        f"({stats['with_nationality_pct']:.1f}%)"
    )
    report.append(
        f"With fighting location:      {stats['with_fighting_out_of']:,} "
        f"({stats['with_fighting_out_of_pct']:.1f}%)"
    )
    report.append("")

    # UFC.com Integration
    report.append("🔗 UFC.COM INTEGRATION")
    report.append("-" * 70)
    report.append(
        f"Matched to UFC.com:          {stats['with_ufc_com_slug']:,} "
        f"({stats['with_ufc_com_slug_pct']:.1f}%)"
    )
    report.append(f"Never scraped:               {stats['never_scraped']:,}")
    report.append(f"Recent updates (7d):         {stats['recent_changes_7d']:,}")
    report.append("")

    # Data Freshness
    report.append("🕒 DATA FRESHNESS")
    report.append("-" * 70)
    report.append(f"Stale data (>30 days):       {stats['stale_data_30d']:,}")
    report.append(f"Stale data (>90 days):       {stats['stale_data_90d']:,}")
    report.append(f"Active fighters (6mo):       {stats['active_fighters_6mo']:,}")
    report.append("")

    # Action Items
    report.append("🔧 ACTION ITEMS")
    report.append("-" * 70)
    report.append(f"Needs manual review:         {stats['needs_manual_review']:,}")
    report.append("")

    # Health Status
    is_healthy = len(issues) == 0
    report.append("🏥 HEALTH STATUS")
    report.append("-" * 70)
    if is_healthy:
        report.append("✅ All metrics within healthy thresholds")
    else:
        report.append("❌ Issues detected:\n")
        for issue in issues:
            report.append(f"   {issue}")

    report.append("")
    report.append("=" * 70)
    report.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report.append("=" * 70 + "\n")

    return "\n".join(report)


@click.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output health stats as JSON instead of formatted report",
)
@click.option(
    "--exit-code",
    is_flag=True,
    help="Exit with code 1 if issues detected (for CI/CD)",
)
def main(output_json: bool, exit_code: bool):
    """
    Monitor location data health and completeness.

    Returns exit code 0 if healthy, 1 if issues detected (when --exit-code is used).
    """
    asyncio.run(run_health_check(output_json, exit_code))


async def run_health_check(output_json: bool, exit_code: bool):
    """Main health check logic."""
    async with get_session() as session:
        stats = await get_health_stats(session)

    is_healthy, issues = check_health_thresholds(stats)

    if output_json:
        output = {
            "stats": stats,
            "is_healthy": is_healthy,
            "issues": issues,
            "generated_at": datetime.utcnow().isoformat(),
        }
        click.echo(json.dumps(output, indent=2))
    else:
        report = format_health_report(stats, issues)
        click.echo(report)

    # Exit with appropriate code
    if exit_code and not is_healthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
