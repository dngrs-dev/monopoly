# Monopoly (Engine + WebSocket Demo)

A small Monopoly-like game engine written in Python, plus a FastAPI WebSocket server and a minimal browser client.

This repo is intentionally a **prototype / learning project**: the core is an event/choice-driven engine, and the server turns engine choices into UI actions.

## What’s implemented

- Turn system with choice-based commands (roll dice, buy/decline property, jail actions)
- Moving around a board and “Start” pass/land bonuses
- Properties: buy, ownership tracking, rent payments
- Chance tiles: draw cards and resolve effects (move steps, move to position, money, go to jail, get-out-of-jail-free)
- Optional auctions when declining to buy (see `auction_enabled`)
- Trade offers (create, send with money/properties, accept/reject)
- WebSocket “rooms”: multiple browser tabs can join the same room and see the same game state

## What’s *not* implemented (yet)

This is **not a full Monopoly ruleset**. For example: full 40-tile board, houses/hotels, sets/monopolies, mortgaging, railroads/utilities, bankruptcy rules, and a polished UI are not included.

## Requirements

- Tested on Python 3.14.2, but can work with older version
- See other [requirements](requirements.txt).

## Run the web demo

Start the FastAPI server:

```bash
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Notes:

- The server currently uses a small demo board (8 tiles) defined in `server/app.py`.
- State is in-memory only; restarting the server resets rooms.

## Run the engine demo (no server)

There is also a simple terminal simulation:

```bash
python engine/demo.py
```

## WebSocket protocol

Client → Server:

- `{"type":"join","room_id":"room1","player_id":1}`
- `{"type":"choose","room_id":"room1","player_id":1,"choice_id":"...","payload":{...}}`

Server → Client:

- `joined`: initial snapshot + available choices
- `update`: events + updated snapshot + new choices
- `error`: validation/runtime errors (kept simple for the demo)

## License

MIT. See [LICENSE](LICENSE).