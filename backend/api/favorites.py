"""FastAPI router exposing CRUD operations for favorites collections."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.schemas.favorites import (
    FavoriteCollectionCreate,
    FavoriteCollectionDetail,
    FavoriteCollectionListResponse,
    FavoriteCollectionStats,
    FavoriteCollectionUpdate,
    FavoriteEntryCreate,
    FavoriteEntryReorderRequest,
    FavoriteEntryUpdate,
)
from backend.schemas.favorites import (
    FavoriteEntry as FavoriteEntrySchema,
)
from backend.services.favorites_service import FavoritesService, get_favorites_service

router = APIRouter()


@router.get("/collections", response_model=FavoriteCollectionListResponse)
async def list_collections(
    user_id: str = Query("demo-user", min_length=1, description="Identifier for the owner"),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteCollectionListResponse:
    """Return the caller's collections, hydrating stats summaries."""

    return await service.list_collections(user_id=user_id)


@router.post(
    "/collections",
    response_model=FavoriteCollectionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    payload: FavoriteCollectionCreate,
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteCollectionDetail:
    """Create a new collection and return the fully hydrated payload."""

    return await service.create_collection(payload)


@router.get(
    "/collections/{collection_id}",
    response_model=FavoriteCollectionDetail,
)
async def get_collection(
    collection_id: int,
    user_id: str | None = Query(
        default=None,
        description=(
            "Optional owner identifier used to ensure the caller can only access"
            " their own collections."
        ),
    ),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteCollectionDetail:
    """Retrieve a single collection by identifier."""

    collection = await service.get_collection(
        collection_id=collection_id, user_id=user_id
    )
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.patch(
    "/collections/{collection_id}",
    response_model=FavoriteCollectionDetail,
)
async def update_collection(
    collection_id: int,
    payload: FavoriteCollectionUpdate,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteCollectionDetail:
    """Apply partial updates to a collection."""

    try:
        return await service.update_collection(
            collection_id=collection_id,
            user_id=user_id,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> Response:
    """Remove a collection and all of its entries."""

    try:
        await service.delete_collection(collection_id=collection_id, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/collections/{collection_id}/entries",
    response_model=FavoriteEntrySchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_entry(
    collection_id: int,
    payload: FavoriteEntryCreate,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteEntrySchema:
    """Insert a fighter into the requested collection."""

    try:
        return await service.add_entry(
            collection_id=collection_id,
            user_id=user_id,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch(
    "/collections/{collection_id}/entries/{entry_id}",
    response_model=FavoriteEntrySchema,
)
async def update_entry(
    collection_id: int,
    entry_id: int,
    payload: FavoriteEntryUpdate,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteEntrySchema:
    """Mutate entry metadata such as notes, tags, or ordering."""

    try:
        return await service.update_entry(
            collection_id=collection_id,
            entry_id=entry_id,
            user_id=user_id,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/collections/{collection_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_entry(
    collection_id: int,
    entry_id: int,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> Response:
    """Remove an entry from a collection."""

    try:
        await service.delete_entry(
            collection_id=collection_id,
            entry_id=entry_id,
            user_id=user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/collections/{collection_id}/entries/reorder",
    response_model=FavoriteCollectionDetail,
)
async def reorder_entries(
    collection_id: int,
    payload: FavoriteEntryReorderRequest,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteCollectionDetail:
    """Persist drag-and-drop ordering from the UI."""

    try:
        return await service.reorder_entries(
            collection_id=collection_id,
            user_id=user_id,
            payload=payload,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/collections/{collection_id}/stats",
    response_model=FavoriteCollectionStats,
)
async def get_collection_stats(
    collection_id: int,
    user_id: str | None = Query(default=None),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteCollectionStats:
    """Return stats for a collection without fetching entries."""

    try:
        stats = await service.get_collection_stats(
            collection_id=collection_id, user_id=user_id
        )
        return stats
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
