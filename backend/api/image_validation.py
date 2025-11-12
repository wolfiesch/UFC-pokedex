"""API endpoints for image validation data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_async_session
from backend.db.models import Fighter
from backend.schemas.fighter import FighterListItem
from backend.services.image_resolver import resolve_fighter_image

router = APIRouter(tags=["Image Validation"])


@router.get("/stats")
async def get_validation_stats(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get overall image validation statistics.

    Returns:
        Dictionary with validation statistics including:
        - total_fighters: Total number of fighters
        - validated: Number of fighters with validated images
        - with_faces: Number with detected faces
        - without_faces: Number without detected faces
        - low_quality: Number with quality score < 50
        - with_flags: Number with validation flags
        - flag_breakdown: Count of each flag type
    """
    # Get all fighters
    query = select(Fighter)
    result = await session.execute(query)
    fighters = result.scalars().all()

    stats = {
        "total_fighters": len(fighters),
        "validated": 0,
        "with_faces": 0,
        "without_faces": 0,
        "low_quality": 0,
        "with_flags": 0,
        "flag_breakdown": {
            "low_resolution": 0,
            "no_face_detected": 0,
            "multiple_faces": 0,
            "blurry_image": 0,
            "too_dark": 0,
            "too_bright": 0,
            "potential_duplicates": 0,
        },
    }

    for fighter in fighters:
        if fighter.image_validated_at:
            stats["validated"] += 1

            if fighter.has_face_detected:
                stats["with_faces"] += 1
            elif fighter.has_face_detected is False:
                stats["without_faces"] += 1

            if fighter.image_quality_score and fighter.image_quality_score < 50:
                stats["low_quality"] += 1

            if fighter.image_validation_flags:
                stats["with_flags"] += 1

                # Count individual flags
                for flag_key in fighter.image_validation_flags:
                    if flag_key in stats["flag_breakdown"]:
                        stats["flag_breakdown"][flag_key] += 1

    return stats


@router.get("/low-quality")
async def get_low_quality_images(
    min_score: float = Query(50.0, description="Minimum quality score threshold"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get fighters with low-quality images.

    Args:
        min_score: Quality score threshold (return fighters below this score)
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Dictionary with fighters list and metadata
    """
    # Query fighters with quality score below threshold
    query = (
        select(Fighter)
        .where(
            and_(
                Fighter.image_validated_at.isnot(None),
                Fighter.image_quality_score < min_score,
            )
        )
        .order_by(Fighter.image_quality_score.asc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)
    fighters = result.scalars().all()

    # Convert to response format
    items = []
    for fighter in fighters:
        items.append(
            {
                "fighter_id": fighter.id,
                "name": fighter.name,
                "image_url": resolve_fighter_image(fighter.id, fighter.image_url),
                "quality_score": fighter.image_quality_score,
                "resolution": (
                    f"{fighter.image_resolution_width}x{fighter.image_resolution_height}"
                    if fighter.image_resolution_width
                    else None
                ),
                "has_face": fighter.has_face_detected,
                "flags": fighter.image_validation_flags or {},
                "validated_at": (
                    fighter.image_validated_at.isoformat()
                    if fighter.image_validated_at
                    else None
                ),
            }
        )

    return {"fighters": items, "count": len(items), "limit": limit, "offset": offset}


@router.get("/no-face")
async def get_fighters_without_faces(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get fighters where no face was detected.

    These images may be:
    - Not actual fighter photos
    - Poor quality or corrupted
    - Action shots without clear face
    - Placeholder images

    Returns:
        Dictionary with fighters list and metadata
    """
    query = (
        select(Fighter)
        .where(
            and_(
                Fighter.image_validated_at.isnot(None),
                Fighter.has_face_detected == False,
            )
        )
        .order_by(Fighter.name)
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)
    fighters = result.scalars().all()

    items = []
    for fighter in fighters:
        items.append(
            {
                "fighter_id": fighter.id,
                "name": fighter.name,
                "image_url": resolve_fighter_image(fighter.id, fighter.image_url),
                "quality_score": fighter.image_quality_score,
                "resolution": (
                    f"{fighter.image_resolution_width}x{fighter.image_resolution_height}"
                    if fighter.image_resolution_width
                    else None
                ),
                "flags": fighter.image_validation_flags or {},
            }
        )

    return {"fighters": items, "count": len(items), "limit": limit, "offset": offset}


@router.get("/duplicates")
async def get_duplicate_images(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get fighters with potential duplicate images.

    Uses perceptual hashing to identify visually similar images.
    Duplicates may indicate:
    - Same fighter with multiple IDs
    - Incorrectly assigned images
    - Stock placeholder photos

    Returns:
        Dictionary with fighters and their duplicate matches
    """
    # Query fighters with duplicate flags
    query = (
        select(Fighter)
        .where(Fighter.image_validation_flags.isnot(None))
        .order_by(Fighter.name)
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)
    fighters = result.scalars().all()

    # Filter to only those with potential_duplicates flag
    items = []

    # Store fighter objects with their duplicate IDs for batch processing.
    fighters_with_duplicates: list[tuple[Fighter, list[str]]] = []

    # Collect all duplicate IDs to enable single batched lookup.
    referenced_duplicate_ids: set[str] = set()

    for fighter in fighters:
        flags = fighter.image_validation_flags or {}
        duplicate_ids: list[str] | None = flags.get("potential_duplicates")

        if duplicate_ids:
            fighters_with_duplicates.append((fighter, duplicate_ids))
            referenced_duplicate_ids.update(duplicate_ids)

    # Batch-fetch fighter names for all duplicate IDs.
    duplicate_lookup: dict[str, str] = {}
    if referenced_duplicate_ids:
        dup_query = select(Fighter.id, Fighter.name).where(
            Fighter.id.in_(referenced_duplicate_ids)
        )
        dup_result = await session.execute(dup_query)
        duplicate_lookup = {row.id: row.name for row in dup_result}

    for fighter, duplicate_ids in fighters_with_duplicates:
        duplicates = [
            {
                "fighter_id": duplicate_id,
                "name": duplicate_lookup.get(duplicate_id, "Unknown Fighter"),
            }
            for duplicate_id in duplicate_ids
        ]

        items.append(
            {
                "fighter_id": fighter.id,
                "name": fighter.name,
                "image_url": resolve_fighter_image(fighter.id, fighter.image_url),
                "quality_score": fighter.image_quality_score,
                "duplicates": duplicates,
            }
        )

    return {"fighters": items, "count": len(items), "limit": limit, "offset": offset}


@router.get("/flags")
async def get_fighters_by_flag(
    flag: str = Query(
        ...,
        description="Flag type: low_resolution, no_face_detected, multiple_faces, blurry_image, too_dark, too_bright",
    ),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get fighters with a specific validation flag.

    Args:
        flag: Flag type to filter by
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Dictionary with fighters list and metadata
    """
    # Query fighters with the specified flag
    # Note: JSON field querying syntax varies by database
    # PostgreSQL: use JSON operators, SQLite: need to parse JSON in Python

    query = (
        select(Fighter)
        .where(Fighter.image_validation_flags.isnot(None))
        .order_by(Fighter.name)
    )

    result = await session.execute(query)
    all_fighters = result.scalars().all()

    # Filter in Python (works for all databases)
    filtered = []
    for fighter in all_fighters:
        flags = fighter.image_validation_flags or {}
        if flag in flags:
            filtered.append(fighter)

    # Apply pagination
    paginated = filtered[offset : offset + limit]

    items = []
    for fighter in paginated:
        items.append(
            {
                "fighter_id": fighter.id,
                "name": fighter.name,
                "image_url": resolve_fighter_image(fighter.id, fighter.image_url),
                "quality_score": fighter.image_quality_score,
                "resolution": (
                    f"{fighter.image_resolution_width}x{fighter.image_resolution_height}"
                    if fighter.image_resolution_width
                    else None
                ),
                "flag_details": fighter.image_validation_flags.get(flag),
            }
        )

    return {
        "fighters": items,
        "count": len(items),
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{fighter_id}")
async def get_fighter_validation(
    fighter_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get validation details for a specific fighter.

    Args:
        fighter_id: Fighter ID

    Returns:
        Dictionary with complete validation data
    """
    query = select(Fighter).where(Fighter.id == fighter_id)
    result = await session.execute(query)
    fighter = result.scalar_one_or_none()

    if not fighter:
        return {"error": "Fighter not found"}

    if not fighter.image_validated_at:
        return {
            "fighter_id": fighter.id,
            "name": fighter.name,
            "validated": False,
            "message": "Image not yet validated",
        }

    return {
        "fighter_id": fighter.id,
        "name": fighter.name,
        "validated": True,
        "image_url": resolve_fighter_image(fighter.id, fighter.image_url),
        "quality_score": fighter.image_quality_score,
        "resolution": {
            "width": fighter.image_resolution_width,
            "height": fighter.image_resolution_height,
        },
        "face_detection": {
            "has_face": fighter.has_face_detected,
            "face_count": fighter.face_count,
        },
        "flags": fighter.image_validation_flags or {},
        "validated_at": (
            fighter.image_validated_at.isoformat()
            if fighter.image_validated_at
            else None
        ),
    }
