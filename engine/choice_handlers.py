from functools import singledispatch
from engine.choices import (
    Choice,
    RollDiceChoice,
    BuyPropertyChoice,
    DeclineBuyPropertyChoice,
    PayFineChoice,
    TryDoublesJailChoice,
    UseGetOutOfJailFreeCardChoice,
    AuctionBidChoice,
    AuctionPassChoice,
    MakeTradeOfferChoice,
    SendTradeOfferChoice,
    AcceptTradeOfferChoice,
    RejectTradeOfferChoice,
    BuyImprovementChoice,
    SellImprovementChoice,
    MortgagePropertyChoice,
    UnmortgagePropertyChoice,
    PayPendingPaymentChoice,
    DeclareBankruptcyChoice,
)
from engine.game import Game, TurnPhase, build_available_choices
from engine.events import (
    Event,
    PlayerRolledDice,
    PlayerMoved,
    MoveReason,
    PlayerBoughtProperty,
    AuctionStarted,
    PlayerPaidJailFine,
    PlayerReleasedFromJail,
    PlayerSkipTurn,
    PlayerUsedGetOutOfJailFreeCard,
    PlayerBoughtImprovement,
    PlayerSoldImprovement,
    PlayerMortgagedProperty,
    PlayerUnmortgagedProperty,
    PlayerPaidRent,
    PlayerPaidFine,
    PlayerPaidMoney,
)
from engine.tiles import OwnableTile, StreetTile
from engine.tile_handlers import resolve_tile, _calculate_rent
from engine.cards import GetOutOfJailFreeCard
from engine.auction import Auction
from engine.tradeoffer import TradeOffer


def _assert_turn(game: Game, player_id: int, choice: Choice):
    print(f"Applying choice: {choice}")
    if game.turn_phase != TurnPhase.AWAIT_CHOICE:
        raise ValueError("Not awaiting choice")

    if game.trade_offer is not None:
        if isinstance(choice, (AcceptTradeOfferChoice, RejectTradeOfferChoice)):
            if player_id != game.trade_offer.receiving_player_id:
                raise ValueError(
                    "Only the receiving player can accept or reject the trade offer"
                )
            return
        raise ValueError(
            "A trade offer is active; only accept/reject choices are allowed"
        )

    if isinstance(choice, (AuctionBidChoice, AuctionPassChoice)):
        if game.auction is None:
            raise ValueError("No active auction")
        if game.auction.active_player_id() != player_id:
            raise ValueError("It's not the player's auction turn")
        return

    # While an auction is active, only auction choices.
    if game.auction is not None:
        raise ValueError("Auction is active; only auction choices are allowed")

    if game.pending_payment is not None:
        if player_id != game.pending_payment.debtor_player_id:
            raise ValueError("Only the debtor may act while a payment is pending")
        if not isinstance(
            choice,
            (
                MortgagePropertyChoice,
                SellImprovementChoice,
                PayPendingPaymentChoice,
                DeclareBankruptcyChoice,
            ),
        ):
            raise ValueError(
                "A payment is pending; only mortgage/sell/pay/bankruptcy choices are allowed"
            )
        return

    if game.current_player().id != player_id:
        raise ValueError("It's not the player's turn")


def _get_player_by_id(game: Game, player_id: int):
    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        raise ValueError("Player not found")
    return player


@singledispatch
def apply_choice(choice: Choice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for choice type: {type(choice)}")


@apply_choice.register
def _(choice: RollDiceChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if player.in_jail:
        raise ValueError("Player is in jail and cannot roll dice")

    dice1, dice2 = game.dice.roll()
    roll = dice1 + dice2
    from_position = player.position
    move_events = player.move_steps(roll, game.board)

    events.append(PlayerRolledDice(player_id=player.id, dice1=dice1, dice2=dice2))
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            steps=roll,
            reason=MoveReason.ROLL_DICE,
        )
    )
    events.extend(move_events)

    game.turn_phase = TurnPhase.RESOLVE_TILE
    game, tile_events, tile_choices = resolve_tile(
        game.board.get_tile(game.current_player().position), game
    )
    events.extend(tile_events)
    choices.extend(tile_choices)
    return game, events, choices


@apply_choice.register
def _(choice: BuyPropertyChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    tile = game.board.get_tile(player.position)
    if not isinstance(tile, OwnableTile):
        raise ValueError("Current tile is not a property")
    if tile.owner is not None:
        raise ValueError("Property is already owned")
    if player.balance < tile.price:
        raise ValueError("Player cannot afford this property")
    if tile.price != choice.price:
        raise ValueError("Offer price does not match property price")
    if tile.name != choice.property_name:
        raise ValueError("Property name does not match current tile")

    player.update_balance(-tile.price)
    tile.owner = player.id
    events.append(
        PlayerBoughtProperty(
            player_id=player.id, property_name=tile.name, price=tile.price
        )
    )
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@apply_choice.register
def _(
    choice: DeclineBuyPropertyChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    tile = game.board.get_tile(player.position)
    if not isinstance(tile, OwnableTile):
        raise ValueError("Current tile is not a property")
    if tile.owner is not None:
        raise ValueError("Property is already owned")

    if game.rules.auction_enabled:
        # Order bidders by table order starting with the next player.
        ordered_ids: list[int] = []
        for offset in range(1, len(game.players) + 1):
            p = game.players[(game.current_player_index + offset) % len(game.players)]
            if not p.bankrupt and p.balance > 0:
                ordered_ids.append(p.id)

        game.auction = Auction(
            tile_position=player.position,
            base_price=tile.price,
            initial_player_id=player.id,
            step=0,
            cursor_index=0,
            active_player_ids=ordered_ids,
        )
        events.append(
            AuctionStarted(
                tile_position=player.position,
                base_price=tile.price,
                initial_player_id=player.id,
            )
        )
        choices.extend(game.auction.start())
        return game, events, choices

    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@apply_choice.register
def _(choice: PayFineChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if not player.in_jail:
        raise ValueError("Player is not in jail")
    if player.balance < choice.fine:
        raise ValueError("Player cannot afford the fine")

    player.update_balance(-choice.fine)
    player.in_jail = False
    player.skip_turns = 0
    events.append(PlayerPaidJailFine(player_id=player.id, amount=choice.fine))
    events.append(PlayerReleasedFromJail(player_id=player.id))
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@apply_choice.register
def _(
    choice: TryDoublesJailChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if not player.in_jail:
        raise ValueError("Player is not in jail")

    dice1, dice2 = game.dice.roll()
    events.append(PlayerRolledDice(player_id=player.id, dice1=dice1, dice2=dice2))

    if dice1 == dice2:
        player.in_jail = False
        player.skip_turns = 0
        events.append(PlayerReleasedFromJail(player_id=player.id))
        # Move the player according to the roll
        from_position = player.position
        roll = dice1 + dice2
        move_events = player.move_steps(roll, game.board)
        events.append(
            PlayerMoved(
                player_id=player.id,
                from_position=from_position,
                to_position=player.position,
                steps=roll,
                reason=MoveReason.ROLL_DICE,
            )
        )
        events.extend(move_events)
        game.turn_phase = TurnPhase.RESOLVE_TILE
        game, tile_events, tile_choices = resolve_tile(
            game.board.get_tile(game.current_player().position), game
        )
        events.extend(tile_events)
        choices.extend(tile_choices)
    else:
        player.skip_turns -= 1
        events.append(PlayerSkipTurn(player_id=player.id, turns_left=player.skip_turns))
        if player.skip_turns <= 0:
            # Player must pay fine on next turn if they fail to roll doubles
            choices.append(PayFineChoice(player_id=player.id, fine=50))
        else:
            game.turn_phase = TurnPhase.END_TURN

    return game, events, choices


@apply_choice.register
def _(
    choice: UseGetOutOfJailFreeCardChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if not player.in_jail:
        raise ValueError("Player is not in jail")

    card_index = next(
        (
            i
            for i, card in enumerate(player.cards)
            if isinstance(card, GetOutOfJailFreeCard)
        ),
        None,
    )
    if card_index is None:
        raise ValueError("Player does not have a Get Out of Jail Free card")

    # Remove the card from player's hand
    card = player.cards.pop(card_index)
    events.append(PlayerUsedGetOutOfJailFreeCard(player_id=player.id))

    # Return the card to the deck it was originally drawn from
    if card.origin_deck is not None:
        card.origin_deck.discard_card(card)

    player.in_jail = False
    player.skip_turns = 0

    choices.append(
        RollDiceChoice(player_id=player.id)
    )  # Allow player to roll immediately after using the card
    events.append(PlayerReleasedFromJail(player_id=player.id))

    return game, events, choices


@apply_choice.register
def _(choice: AuctionBidChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    if choice.tile_position != game.auction.tile_position:
        raise ValueError("Bid choice tile position does not match active auction")
    if choice.player_id not in game.auction.active_player_ids:
        raise ValueError("Player is not an active bidder in this auction")

    events: list[Event] = []
    choices: list[Choice] = []

    # Update auction state with the new bid
    auction = game.auction
    auction.last_bidder_id = choice.player_id
    auction.last_bid_amount = choice.bid
    auction.step += 1

    if auction.check_auction_end():
        # If nobody bid or everyone passed, the property stays unowned.
        if not auction.active_player_ids or auction.last_bid_amount is None:
            game.auction = None
            game.turn_phase = TurnPhase.END_TURN
            return game, events, choices

        winning_player_id = auction.active_player_ids[0]
        winning_bid = auction.last_bid_amount
        tile = game.board.get_tile(auction.tile_position)
        if not isinstance(tile, OwnableTile):
            raise ValueError("Auctioned tile is not a property")

        # Transfer ownership of the property to the winning bidder
        tile.owner = winning_player_id
        winning_player = next(p for p in game.players if p.id == winning_player_id)
        winning_player.update_balance(-winning_bid)

        events.append(
            PlayerBoughtProperty(
                player_id=winning_player_id,
                property_name=tile.name,
                price=winning_bid,
            )
        )

        # Clear the auction state
        game.auction = None

        # End the turn after the auction concludes
        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices

    # Move cursor to the next active bidder
    auction.cursor_index = (auction.cursor_index + 1) % len(auction.active_player_ids)

    # Generate choices for the next bidder
    next_bidder_id = auction.active_player_id()
    choices.append(
        AuctionBidChoice(
            player_id=next_bidder_id,
            tile_position=auction.tile_position,
            bid=auction.active_bid(),
        )
    )
    choices.append(
        AuctionPassChoice(
            player_id=next_bidder_id,
            tile_position=auction.tile_position,
        )
    )

    return game, events, choices


@apply_choice.register
def _(choice: AuctionPassChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    if choice.tile_position != game.auction.tile_position:
        raise ValueError("Pass choice tile position does not match active auction")
    if choice.player_id not in game.auction.active_player_ids:
        raise ValueError("Player is not an active bidder in this auction")

    events: list[Event] = []
    choices: list[Choice] = []

    # Remove the player from active bidders
    auction = game.auction
    auction.active_player_ids.remove(choice.player_id)

    # Check if the auction has ended
    if auction.check_auction_end():
        # If nobody bid or everyone passed, the property stays unowned.
        if not auction.active_player_ids or auction.last_bid_amount is None:
            game.auction = None
            game.turn_phase = TurnPhase.END_TURN
            return game, events, choices

        winning_player_id = auction.active_player_ids[0]
        winning_bid = auction.last_bid_amount
        tile = game.board.get_tile(auction.tile_position)
        if not isinstance(tile, OwnableTile):
            raise ValueError("Auctioned tile is not a property")

        # Transfer ownership of the property to the winning bidder
        tile.owner = winning_player_id
        winning_player = next(p for p in game.players if p.id == winning_player_id)
        winning_player.update_balance(-winning_bid)

        events.append(
            PlayerBoughtProperty(
                player_id=winning_player_id,
                property_name=tile.name,
                price=winning_bid,
            )
        )

        # Clear the auction state
        game.auction = None

        # End the turn after the auction concludes
        game.turn_phase = TurnPhase.END_TURN
    else:
        # Move cursor to the next active bidder
        auction.cursor_index = (auction.cursor_index + 1) % len(
            auction.active_player_ids
        )

        # Generate choices for the next bidder
        next_bidder_id = auction.active_player_id()
        choices.append(
            AuctionBidChoice(
                player_id=next_bidder_id,
                tile_position=auction.tile_position,
                bid=auction.active_bid(),
            )
        )
        choices.append(
            AuctionPassChoice(
                player_id=next_bidder_id,
                tile_position=auction.tile_position,
            )
        )

    return game, events, choices


## TRADE OFFER


def _get_player(game: Game, player_id: int):
    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        raise ValueError("Player not found")
    return player


def _assert_positions_owned_by(game: Game, positions: list[int], owner_id: int):
    size = game.board.size()
    seen: set[int] = set()
    for pos in positions:
        if not isinstance(pos, int):
            raise ValueError("Position must be an integer")
        if pos < 0 or pos >= size:
            raise ValueError("Position out of board bounds")
        if pos in seen:
            raise ValueError("Duplicate position in list")
        seen.add(pos)

        tile = game.board.get_tile(pos)
        if not isinstance(tile, OwnableTile):
            raise ValueError(f"Tile at position {pos} is not a property")
        if tile.owner != owner_id:
            raise ValueError(
                f"Tile at position {pos} is not owned by player {owner_id}"
            )


@apply_choice.register
def _(
    choice: MakeTradeOfferChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    if choice.player_id == choice.receiving_player_id:
        raise ValueError("Cannot make a trade offer to oneself")

    _get_player(game, choice.receiving_player_id)  # Validate receiving player exists

    events: list[Event] = []
    choices: list[Choice] = []

    choices.append(
        SendTradeOfferChoice(
            player_id=choice.player_id,
            receiving_player_id=choice.receiving_player_id,
        )
    )
    return game, events, choices


@apply_choice.register
def _(
    choice: SendTradeOfferChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    if choice.player_id == choice.receiving_player_id:
        raise ValueError("Cannot send a trade offer to oneself")
    if choice.offered_money < 0 or choice.requested_money < 0:
        raise ValueError("Money amounts cannot be negative")

    offering_player = _get_player(game, choice.player_id)
    receiving_player = _get_player(game, choice.receiving_player_id)

    if offering_player.balance < choice.offered_money:
        raise ValueError("Offering player cannot afford the offered money")
    if receiving_player.balance < choice.requested_money:
        raise ValueError("Receiving player cannot afford the requested money")

    game.trade_offer = TradeOffer(
        offering_player_id=choice.player_id,
        receiving_player_id=choice.receiving_player_id,
        offered_money=choice.offered_money,
        requested_money=choice.requested_money,
        offered_properties_positions=choice.offered_properties_positions,
        requested_properties_positions=choice.requested_properties_positions,
    )

    events: list[Event] = []
    choices: list[Choice] = [
        AcceptTradeOfferChoice(
            player_id=choice.receiving_player_id,
        ),
        RejectTradeOfferChoice(
            player_id=choice.receiving_player_id,
        ),
    ]

    return game, events, choices


@apply_choice.register
def _(
    choice: AcceptTradeOfferChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    if game.trade_offer is None:
        raise ValueError("No active trade offer to accept")
    if game.trade_offer.receiving_player_id != choice.player_id:
        raise ValueError("Only the receiving player can accept the trade offer")

    offer = game.trade_offer
    offering_player = _get_player(game, offer.offering_player_id)
    receiving_player = _get_player(game, offer.receiving_player_id)

    if offering_player.balance < offer.offered_money:
        raise ValueError("Offering player cannot afford the offered money")
    if receiving_player.balance < offer.requested_money:
        raise ValueError("Receiving player cannot afford the requested money")

    # Validate ownership of offered and requested properties
    _assert_positions_owned_by(
        game, offer.offered_properties_positions, offer.offering_player_id
    )
    _assert_positions_owned_by(
        game, offer.requested_properties_positions, offer.receiving_player_id
    )

    # Execute the trade
    offering_player.update_balance(-offer.offered_money)
    offering_player.update_balance(offer.requested_money)
    receiving_player.update_balance(-offer.requested_money)
    receiving_player.update_balance(offer.offered_money)

    for pos in offer.offered_properties_positions:
        tile = game.board.get_tile(pos)
        if isinstance(tile, OwnableTile):
            tile.owner = receiving_player.id

    for pos in offer.requested_properties_positions:
        tile = game.board.get_tile(pos)
        if isinstance(tile, OwnableTile):
            tile.owner = offering_player.id

    # Clear the active trade offer
    game.trade_offer = None

    return game, [], build_available_choices(game)


@apply_choice.register
def _(
    choice: RejectTradeOfferChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    if game.trade_offer is None:
        raise ValueError("No active trade offer to reject")
    if game.trade_offer.receiving_player_id != choice.player_id:
        raise ValueError("Only the receiving player can reject the trade offer")

    # Clear the active trade offer
    game.trade_offer = None

    return game, [], build_available_choices(game)


@apply_choice.register
def _(
    choice: BuyImprovementChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []

    player = game.current_player()
    tile = game.board.get_tile(choice.property_position)
    if not isinstance(tile, StreetTile):
        raise ValueError("Tile at position is not a street property")
    if tile.owner != player.id:
        raise ValueError("Player does not own this property")
    if tile.improvement_level >= len(tile.rent_schedule) - 1:
        raise ValueError("Property is already at max improvement level")
    improvement_price = (
        tile.improvement_prices
        if isinstance(tile.improvement_prices, int)
        else tile.improvement_prices[tile.improvement_level]
    )
    if choice.price != improvement_price:
        raise ValueError("Offer price does not match improvement price")
    if player.balance < improvement_price:
        raise ValueError("Player cannot afford this improvement")

    group_tiles = game.board.get_group_tiles(tile.group_id)
    if any(t.owner != player.id for t in group_tiles):
        raise ValueError(
            "Player must own all properties in the group to buy improvements"
        )

    player.update_balance(-improvement_price)
    tile.improvement_level += 1
    events.append(
        PlayerBoughtImprovement(
            player_id=player.id,
            property_name=tile.name,
            improvement_level=tile.improvement_level,
            price=improvement_price,
        )
    )

    tile.rent = _calculate_rent(tile, game)  # Update rent after improvement

    return game, events, build_available_choices(game)


@apply_choice.register
def _(
    choice: SellImprovementChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []

    player = game.current_player()
    tile = game.board.get_tile(choice.property_position)
    if not isinstance(tile, StreetTile):
        raise ValueError("Tile at position is not a street property")
    if tile.owner != player.id:
        raise ValueError("Player does not own this property")
    if tile.improvement_level <= 0:
        raise ValueError("No improvements to sell on this property")
    improvement_price = (
        tile.improvement_prices
        if isinstance(tile.improvement_prices, int)
        else tile.improvement_prices[tile.improvement_level - 1]
    )
    improvement_sell_price = int(
        improvement_price * tile.improvement_sell_price_multiplier
    )
    if choice.price != improvement_sell_price:
        raise ValueError("Offer price does not match improvement sell price")

    player.update_balance(improvement_sell_price)
    tile.improvement_level -= 1
    events.append(
        PlayerSoldImprovement(
            player_id=player.id,
            property_name=tile.name,
            improvement_level=tile.improvement_level,
            price=improvement_sell_price,
        )
    )

    tile.rent = _calculate_rent(tile, game)  # Update rent after selling improvement

    return game, events, build_available_choices(game)


@apply_choice.register
def _(
    choice: MortgagePropertyChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []

    player = game.current_player()
    tile = game.board.get_tile(choice.property_position)
    if not isinstance(tile, OwnableTile):
        raise ValueError("Tile at position is not a property")
    if isinstance(tile, StreetTile) and tile.improvement_level > 0:
        raise ValueError("Cannot mortgage a street with improvements")
    if tile.owner != player.id:
        raise ValueError("Player does not own this property")
    if tile.mortgaged:
        raise ValueError("Property is already mortgaged")
    mortgage_value = tile.price // 2
    if choice.mortgage_value != mortgage_value:
        raise ValueError("Offer price does not match mortgage value")
    player.update_balance(mortgage_value)
    tile.mortgaged = True
    events.append(
        PlayerMortgagedProperty(
            player_id=player.id,
            property_name=tile.name,
            mortgage_value=mortgage_value,
        )
    )
    return game, events, build_available_choices(game)


@apply_choice.register
def _(
    choice: UnmortgagePropertyChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    events: list[Event] = []

    player = game.current_player()
    tile = game.board.get_tile(choice.property_position)
    if not isinstance(tile, OwnableTile):
        raise ValueError("Tile at position is not a property")
    if tile.owner != player.id:
        raise ValueError("Player does not own this property")
    if not tile.mortgaged:
        raise ValueError("Property is not mortgaged")
    unmortgage_value = int(tile.price * 0.55)
    if choice.unmortgage_value != unmortgage_value:
        raise ValueError("Offer price does not match unmortgage value")
    if player.balance < unmortgage_value:
        raise ValueError("Player cannot afford to unmortgage this property")
    player.update_balance(-unmortgage_value)
    tile.mortgaged = False
    events.append(
        PlayerUnmortgagedProperty(
            player_id=player.id,
            property_name=tile.name,
            mortgage_value=unmortgage_value,
        )
    )

    return game, events, build_available_choices(game)


@apply_choice.register
def _(
    choice: PayPendingPaymentChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    pending = game.pending_payment
    if pending is None:
        raise ValueError("No pending payment")
    if pending.debtor_player_id != choice.player_id:
        raise ValueError("Only the debtor can pay the pending payment")
    if choice.amount != pending.amount:
        raise ValueError("Payment amount does not match pending payment")

    debtor = game.current_player()
    if debtor.balance < pending.amount:
        raise ValueError("Debtor cannot afford the pending payment")

    debtor.update_balance(-pending.amount)

    if pending.creditor_player_id is not None:
        creditor = _get_player_by_id(game, pending.creditor_player_id)
        creditor.update_balance(pending.amount)

    events: list[Event] = []
    if pending.reason == "rent":
        events.append(
            PlayerPaidRent(
                player_id=debtor.id,
                to_player_id=pending.creditor_player_id,
                property_name=pending.property_name or "(unknown)",
                rent=pending.amount,
            )
        )
    elif pending.reason == "fine":
        events.append(PlayerPaidFine(player_id=debtor.id, amount=pending.amount))
    else:
        events.append(
            PlayerPaidMoney(
                player_id=debtor.id,
                amount=-pending.amount,
                reason=pending.reason or "pending_payment",
            )
        )

    game.pending_payment = None
    game.turn_phase = TurnPhase.END_TURN
    return game, events, []


@apply_choice.register
def _(
    choice: DeclareBankruptcyChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id, choice)

    pending = game.pending_payment
    if pending is None:
        raise ValueError("No pending payment")
    if pending.debtor_player_id != choice.player_id:
        raise ValueError("Only the debtor can declare bankruptcy")

    debtor = game.current_player()
    debtor.bankrupt = True

    # Transfer remaining cash and properties.
    creditor_id = pending.creditor_player_id
    if creditor_id is not None:
        creditor = _get_player_by_id(game, creditor_id)
        if debtor.balance > 0:
            creditor.update_balance(debtor.balance)
            debtor.balance = 0
        for tile in game.board.tiles:
            if isinstance(tile, OwnableTile) and tile.owner == debtor.id:
                tile.owner = creditor.id
        if debtor.cards:
            creditor.cards.extend(debtor.cards)
            debtor.cards.clear()
    else:
        # Bank: clear ownership.
        for tile in game.board.tiles:
            if isinstance(tile, OwnableTile) and tile.owner == debtor.id:
                tile.owner = None
                tile.mortgaged = False
                if isinstance(tile, StreetTile):
                    tile.improvement_level = 0
        debtor.balance = 0
        debtor.cards.clear()

    game.pending_payment = None
    game.turn_phase = TurnPhase.END_TURN

    events: list[Event] = [
        PlayerPaidMoney(
            player_id=debtor.id,
            amount=0,
            reason="bankruptcy",
        )
    ]
    return game, events, []
