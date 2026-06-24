from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependecies import User, UserMultiplierCard, get_db
from ..jwt_utils import get_current_user_optional

router = APIRouter(prefix="/inventory", tags=["inventory"])

def serialize_owned_card(card: UserMultiplierCard, *, is_owner: bool | None) -> dict:
    definition = card.definition
    return {
        "id": card.id,
        "name": definition.name,
        "description": definition.description,
        "image_url": definition.image_url,
        "points_cost": definition.points_cost,
        "available_shop": definition.available_shop,
        "available_market": definition.available_market,
        "tradeable": definition.tradeable,
        "sellable": definition.sellable,
        "equipped": card.equipped,
        "rarity": {
            "id": definition.rarity.id,
            "name": definition.rarity.name,
            "color": definition.rarity.color,
            "multiplier": definition.rarity.multiplier,
            "sort_order": definition.rarity.sort_order
        },
        **({"tradeable": card.tradeable, "sellable": card.sellable} if is_owner else {}),
    }
    
@router.get("/{profile_link}")
def public_inventory(
    profile_link: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    profile_user = db.scalar(
        select(User).where(User.profile_link == profile_link)
    )
    if not profile_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cards = db.scalars(
        select(UserMultiplierCard)
        .where(UserMultiplierCard.user_id == profile_user.id)
    ).all()
    is_owner = current_user and current_user.id == profile_user.id
    
    return {
        "user": {"id": profile_user.id, "display_name": profile_user.display_name, "profile_link": profile_user.profile_link, "avatar_url": profile_user.avatar_url},
        "is_owner": is_owner,
        "cards": [serialize_owned_card(card, is_owner=is_owner) for card in cards],
    }