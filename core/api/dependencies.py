from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.db.session import get_db

T = TypeVar("T")


def resolve_entity_by_id_or_prefix(
    db: Session,
    model: type[T],
    identifier: str,
    entity_name: str = "entity",
    min_prefix_length: int = 4,
) -> T:
    """
    Resolves a database entity by its exact ID or an unambiguous prefix (Docker/Git style).

    - Exact match fast-path (O(1)).
    - Prefix match for identifiers >= min_prefix_length (default: 4).
    - Returns 400 with candidate IDs on ambiguity.
    - Returns 400 on prefix shorter than min_prefix_length.
    - Returns 404 when no matching record is found.
    """
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{entity_name.capitalize()} identifier must not be empty.",
        )

    target_id = identifier.strip()

    # 1. Exact match fast-path
    entity = db.query(model).filter(model.id == target_id).first()
    if entity:
        return entity

    # 2. Reject short prefix if exact match not found
    if len(target_id) < min_prefix_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Identifier prefix '{target_id}' is too short. Please provide at least {min_prefix_length} characters.",
        )

    # 3. Escape wildcard characters for safe prefix lookup
    safe_prefix = target_id.replace("%", "").replace("_", "")
    if not safe_prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid identifier prefix provided.",
        )

    matches = db.query(model).filter(model.id.ilike(f"{safe_prefix}%")).limit(5).all()

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name.capitalize()} '{target_id}' not found.",
        )

    if len(matches) > 1:
        candidates = [m.id[:12] for m in matches]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ambiguous {entity_name} identifier '{target_id}' matches multiple records: {', '.join(candidates)}. Please specify more characters.",
        )

    return matches[0]


__all__ = ["get_db", "resolve_entity_by_id_or_prefix"]

