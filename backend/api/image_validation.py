"""API endpoints for image validation data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

import backend.db.connection as db_connection
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
    for fighter in fighters:
        flags = fighter.image_validation_flags or {}
        if "potential_duplicates" in flags:
            duplicate_ids = flags["potential_duplicates"]

            # Fetch duplicate fighter names
            dup_query = select(Fighter.id, Fighter.name).where(
                Fighter.id.in_(duplicate_ids)
            )
            dup_result = await session.execute(dup_query)
            duplicates = [
                {"fighter_id": row.id, "name": row.name} for row in dup_result.all()
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
    # Construct dialect-aware predicates up front to keep both the main data
    # query and the companion count query in sync.  We always guard against
    # NULL JSON blobs before applying the database-specific key lookup so that
    # SQLite's JSON1 functions and PostgreSQL's ``has_key`` operator behave
    # identically.
    flag_predicate: ColumnElement[bool] = _build_flag_predicate(flag)
    shared_predicates: tuple[ColumnElement[bool], ...] = (
        Fighter.image_validation_flags.isnot(None),
        flag_predicate,
    )

    # Execute a paginated data query that defers JSON evaluation to the
    # database engine.  This avoids materialising the entire fighters table in
    # Python when only a handful of rows match the requested flag.
    data_query = (
        select(Fighter)
        .where(*shared_predicates)
        .order_by(Fighter.name)
        .limit(limit)
        .offset(offset)
    )
    data_result = await session.execute(data_query)
    paginated_fighters = data_result.scalars().all()

    # Mirror the filtering conditions in a lightweight ``COUNT(*)`` query so
    # the ``total`` field reflects the true number of matching rows, even when
    # pagination clips the dataset.
    count_query = select(func.count()).select_from(Fighter).where(*shared_predicates)
    total: int = int((await session.execute(count_query)).scalar_one())

    items = []
    for fighter in paginated_fighters:
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
                "flag_details": (fighter.image_validation_flags or {}).get(flag),
            }
        )

    return {
        "fighters": items,
        "count": len(items),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _build_flag_predicate(flag: str) -> ColumnElement[bool]:
    """Return a SQL expression that checks for ``flag`` in the JSON payload.

    The function detects the active database backend at runtime and emits the
    most efficient operator supported by that dialect.  PostgreSQL benefits
    from the native ``?`` operator exposed via SQLAlchemy's ``has_key`` helper,
    while SQLite development environments rely on JSON1's ``json_type`` to
    determine whether the key is present.

    Args:
        flag: The validation flag key requested by the API consumer.

    Returns:
        A :class:`~sqlalchemy.sql.elements.ColumnElement` producing a boolean
        predicate that evaluates to ``True`` whenever ``flag`` exists in the
        ``image_validation_flags`` JSON document.
    """

    database_type: str = db_connection.get_database_type()
    if database_type == "postgresql":
        # ``has_key`` maps to PostgreSQL's ``?`` operator, performing an index
        # assisted existence check without inspecting the JSON payload in
        # Python.  SQLAlchemy does not annotate the return type precisely, so
        # we silence mypy's ``attr-defined`` warning.
        return Fighter.image_validation_flags.has_key(flag)  # type: ignore[attr-defined]

    # SQLite's JSON1 extension returns ``NULL`` when the path is missing.  Using
    # ``json_type`` instead of ``json_extract`` ensures that explicit ``null``
    # values remain discoverable because SQLite reports their type as the string
    # ``"null"`` rather than propagating ``NULL`` up to SQLAlchemy.
    json_path: str = f"$.{flag}"
    return func.json_type(Fighter.image_validation_flags, json_path).isnot(None)


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
