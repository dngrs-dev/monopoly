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


class ClientLobbyJoinInvite(TypedDict):
    type: str  # "lobby_join_invite"
    invite_code: str


class ClientLobbyLeave(TypedDict):
    type: str  # "lobby_leave"
    lobby_id: str


class ClientLobbyStart(TypedDict):
    type: str  # "lobby_start"
    lobby_id: str


class ClientLobbyList(TypedDict):
    type: str  # "lobby_list"


class ClientEquip(TypedDict):
    type: str  # "equip_card"
    card_instance_id: str
    board_id: str
    multiplier: float
    target_positions: NotRequired[list[int]]
    target_group_id: NotRequired[int]


class ClientUnequip(TypedDict):
    type: str  # "unequip_card"
    card_instance_id: NotRequired[str]
    equip_id: NotRequired[str]


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


def is_lobby_join_invite(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_join_invite" and "invite_code" in msg


def is_lobby_leave(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_leave" and "lobby_id" in msg


def is_lobby_start(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_start" and "lobby_id" in msg


def is_lobby_list(msg: dict[str, Any]) -> bool:
    return msg.get("type") == "lobby_list"


def is_equip(msg: dict[str, Any]) -> bool:
    if msg.get("type") != "equip_card":
        return False
    if "card_instance_id" not in msg or "board_id" not in msg or "multiplier" not in msg:
        return False
    if ("target_positions" in msg) and not (
        isinstance(msg["target_positions"], list) and all(isinstance(x, int) for x in msg["target_positions"])
    ):
        return False
    return True


def is_unequip(msg: dict[str, Any]) -> bool:
    if msg.get("type") != "unequip_card":
        return False
    if ("card_instance_id" not in msg) and ("equip_id" not in msg):
        return False
    return True
