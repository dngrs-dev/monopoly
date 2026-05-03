# from engine.board import Board
# from engine.cards import *
# from engine.deck import Deck
# from engine.tiles import *


# def build_chance_deck() -> Deck:
#     return Deck(
#         cards=[
#             MoveToNearestTileByTypeCard(tile_type=StartTile),
#             GoToJailCard(),
#             MoveToPositionCard(position=3),  # Illinois Avenue
#             MoveToPositionCard(position=12),  # St. Charles Place
#             MoveToNearestTileByTypeCard(tile_type=UtilityTile),
#             MoveToNearestTileByTypeCard(tile_type=RailroadTile),
#             MoveToNearestTileByTypeCard(tile_type=RailroadTile),
#             MoneyCard(amount=50),
#             GetOutOfJailFreeCard(),
#             MoveStepsCard(steps=-3),
#             # Pay 25 for each house and 100 for each hotel owned
#             MoneyCard(amount=-15),
#             MoveToPositionCard(position=5),  # Reading Railroad
#             MoveToPositionCard(position=39),  # Boardwalk
#             # Pay each player 50
#             MoneyCard(amount=150),
#         ]
#     )


# def build_community_chest_deck() -> Deck:
#     return Deck(
#         cards=[
#             MoveToNearestTileByTypeCard(tile_type=StartTile),
#             MoneyCard(amount=200),
#             MoneyCard(amount=-50),
#             MoneyCard(amount=50),
#             GetOutOfJailFreeCard(),
#             GoToJailCard(),
#             # Collect 50 from each player
#             MoneyCard(amount=100),
#             MoneyCard(amount=20),
#             # Collect 10 from each player
#             MoneyCard(amount=100),
#             MoneyCard(amount=-100),
#             MoneyCard(amount=-150),
#             MoneyCard(amount=25),
#             # Pay 40 for each house and 115 for each hotel owned
#             MoneyCard(amount=10),
#         ]
#     )


# def build_classic_board() -> Board:
#     pass
