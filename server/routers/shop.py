from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependecies import (
    MultiplierCard,
    PointTransaction,
    User,
    UserMultiplierCard,
    get_db,
)
from ..jwt_utils import get_current_user
from ..paths import WEB_ROOT

router = APIRouter(prefix="/shop", tags=["Shop"])

def serialize_card(card: MultiplierCard) -> dict:
    return {
        "id": card.id,
        "name": card.name,
        "description": card.description,
        "image_url": card.image_url,
        "points_cost": card.points_cost,
        "available_shop": card.available_shop,
        "available_market": card.available_market,
        "tradeable": card.tradeable,
        "rarity": {
            "id": card.rarity.id,
            "name": card.rarity.name,
            "color": card.rarity.color,
            "multiplier": card.rarity.multiplier,
            "sort_order": card.rarity.sort_order
        }
    }
    
@router.get("/")
async def shop_page():
    return FileResponse(WEB_ROOT / "shop" / "index.html")

@router.get("/cards")
def shop_cards(db: Session = Depends(get_db)):
    cards = db.scalars(
        select(MultiplierCard)
        .where(
            MultiplierCard.available_shop == True
        )
    ).all()
    return [serialize_card(card) for card in cards]

@router.post("/cards/{card_id}/buy")
def buy_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    card = db.get(MultiplierCard, card_id)
    if not card or not card.available_shop:
        raise HTTPException(status_code=404, detail="Card not found or not available in shop")

    if current_user.points < card.points_cost:
        raise HTTPException(status_code=400, detail="Insufficient points to buy this card")
    
    current_user.points -= card.points_cost
    
    owned = UserMultiplierCard(
        user_id=current_user.id,
        card_id=card.id,
        source="point_shop",
        tradeable=card.tradeable,
        sellable=card.sellable,
    )
    db.add(owned)
    db.flush()
    
    db.add(PointTransaction(
        user_id=current_user.id,
        amount=-card.points_cost,
        reason="point_shop_purchase",
        related_card_instance_id=owned.id,
    ))
    
    db.commit()
    return {"ok": True, "points_remaining": current_user.points, "card_id": owned.id}
        