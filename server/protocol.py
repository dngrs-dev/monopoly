from typing import Any, TypedDict, NotRequired


class ClientJoin(TypedDict):
    type: str  # "join"
    room_id: str


class ClientChoose(TypedDict):
    type: str  # "choose"
    room_id: str
    choice_id: str
    payload: NotRequired[dict[str, Any]]  # Additional data for trade offers


class ClientLobbyCreate(TypedDict):
    type: str  # "lobby_create"
    user_limit: NotRequired[int]
    is_public: NotRequired[bool]


class ClientLobbyJoin(TypedDict):
    type: str  # "lobby_join"
    lobby_id: str


class ClientLobbyLeave(TypedDict):
    type: str  # "lobby_leave"
    lobby_id: str


class ClientLobbyStart(TypedDict):
    type: str  # "lobby_start"
    lobby_id: str


class ClientLobbyList(TypedDict):
    type: str  # "lobby_list"


def is_join(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "join" and "room_id" in msg


def is_choose(msg: dict[str, Any]) -> bool:
    if not (msg.get("type") == "choose" and "room_id" in msg and "choice_id" in msg):
        return False

    if (
        "payload" in msg
        and msg["payload"] is not None
        and not isinstance(msg["payload"], dict)
    ):
        return False

    return True


def is_lobby_create(msg: dict[str, Any]) -> bool:
    if msg.get("type") != "lobby_create":
        return False
    if "user_limit" in msg and not isinstance(msg["user_limit"], int):
        return False
    if "is_public" in msg and not isinstance(msg["is_public"], bool):
        return False
    return True


def is_lobby_join(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_join" and "lobby_id" in msg


def is_lobby_leave(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_leave" and "lobby_id" in msg


def is_lobby_start(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_start" and "lobby_id" in msg


def is_lobby_list(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_list"
