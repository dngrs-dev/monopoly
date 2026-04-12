from typing import Any, TypedDict, NotRequired


class ClientJoin(TypedDict):
    type: str  # "join"
    room_id: str
    player_id: int


class ClientChoose(TypedDict):
    type: str  # "choose"
    room_id: str
    player_id: int
    choice_id: str
    payload: NotRequired[dict[str, Any]]  # Additional data for trade offers


def is_join(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "join" and "room_id" in msg and "player_id" in msg


def is_choose(msg: dict[str, Any]) -> bool:
    if not (
        msg.get("type") == "choose"
        and "room_id" in msg
        and "player_id" in msg
        and "choice_id" in msg
    ):
        return False

    if (
        "payload" in msg
        and msg["payload"] is not None
        and not isinstance(msg["payload"], dict)
    ):
        return False

    return True
