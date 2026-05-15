# Monopoly (Engine + WebSocket Demo)
![Python Version](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small Monopoly-like game engine written in Python, plus a FastAPI WebSocket server and a minimal browser client.

This repo is intentionally a **prototype / learning project**: the core is an event/choice-driven engine, and the server turns engine choices into UI actions.

## Structure

- `engine/` — core game engine (state + rules)
- `server/` — FastAPI app
- `clients/web/` — tiny HTML/JS client
- `demo/` — terminal demo
- `tests/` — unit tests

## What’s implemented

Engine:

- Turn system with choice-based commands (see `engine/choices.py`)
- Event stream describing what happened (see `engine/events.py`)
- Movement + Start tile pass/land bonuses (supports multiple Start tiles)
- Ownable tiles: buy, ownership tracking, rent payments, optional auctions
- Chance tiles + card effects (move steps, move to position, money, go to jail, "get out of jail free")
- Jail actions (pay fine, try doubles, use "get out of jail free" card)
- Trade offers (make/send/accept/reject) (see `engine/tradeoffer.py`)

## What’s incomplete

WEB

## Requirements

- Python 3.11+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the web demo

Start the FastAPI server:

```bash
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```
or
```bash
fastapi dev server/app.py
```

## Run the terminal demo (no server)

```bash
python -m demo.run
```

## Run tests / lint

```bash
pytest
ruff check .
```

## WebSocket protocol

Endpoint: `/ws`

Client → Server:

- `{"type":"join","room_id":"room1","player_id":1}`
- `{"type":"choose","room_id":"room1","player_id":1,"choice_id":"...","payload":{...}}`

Trade payload:

- For `SendTradeOfferChoice`, `payload` must include:
  - `offered_money` (int)
  - `requested_money` (int)
  - `offered_properties_positions` (list[int])
  - `requested_properties_positions` (list[int])

Server → Client:

- `joined`: initial snapshot + available choices
- `update`: events + updated snapshot + new choices
- `error`: validation/runtime errors (kept simple for the demo)

## License

MIT. See [LICENSE](LICENSE).
