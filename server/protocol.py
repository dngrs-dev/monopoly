from typing import Any, TypedDict


class ClientJoin(TypedDict):
    type: str  # "join"
    room_id: str
    player_id: int


class ClientChoose(TypedDict):
    type: str  # "choose"
    room_id: str
    player_id: int
    choice_id: str


def is_join(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "join" and "room_id" in msg and "player_id" in msg


def is_choose(msg: dict[str, Any]) -> bool:
    return (
        msg.get("type") == "choose"
        and "room_id" in msg
        and "player_id" in msg
        and "choice_id" in msg
    )