# Deedbound

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![License](https://img.shields.io/badge/license-MIT-green)
[![CI](https://github.com/dngrs-dev/monopoly/actions/workflows/ci.yml/badge.svg)](https://github.com/dngrs-dev/monopoly/actions/workflows/ci.yml)

A browser-playable property-trading game with a Python rules engine, FastAPI backend, realtime lobbies, authenticated profiles, and a lightweight vanilla web client.

The project is split cleanly between game logic and delivery code: the `engine` package owns the board-game rules, events, cards, choices, payments, auctions, trades, and tests, while `server` exposes the web app, auth, lobbies, WebSocket game sessions, profiles, shop, and inventory APIs.

## Highlights

| Area | What is included |
| --- | --- |
| Game engine | Turn phases, dice rolls, movement, jail, property ownership, rent, mortgages, improvements, payments, bankruptcy, cards, trades, and optional auction rules. |
| Classic board | A 40-tile board builder with streets, railroads, utilities, taxes, Chance, Community Chest, Jail, Free Parking, Go To Jail, and Boardwalk. |
| Realtime play | Lobby and game WebSockets keep players synchronized while choices are applied server-side. |
| Accounts | Email registration, login, JWT cookie sessions, public profile links, display names, and avatar uploads. |
| Progression layer | Points, multiplier cards, shop purchases, public inventory, rarity metadata, and transaction records. |

## Tech Stack

- Python 3.11+
- FastAPI and Uvicorn
- SQLAlchemy with SQLite by default
- python-jose JWT cookies
- Passlib password hashing
- Vanilla HTML, CSS, and JavaScript client
- Pytest and Ruff for development

## Quick Start

### 1. Install dependencies

```powershell
python -m pip install -e ".[dev]"
```

### 2. Set up environment

Create and edit `.env` using `.env.sample` as a template.

Create a `.data` directory:

```text
.data/
  avatars/default_avatar.png
  assets/
    favicon.ico
    logo.svg
```

### 3. Run the web app

```powershell
python -m uvicorn server.app:app --reload
```

## Web Routes

| Route | Purpose |
| --- | --- |
| `/` | Main page |
| `/login` | Login and registration page |
| `/browse` | Lobby browser |
| `/games/{lobby_id}` | Realtime game board |
| `/profile/{profile_link}` | Public profile page |
| `/settings` | Account settings and avatar upload |
| `/shop` | Multiplier card shop |

## Notes

- The server keeps lobbies and active games in memory, so running multiple server processes will not share active sessions without additional storage.
- SQLite is the default persistence layer for accounts, profiles, shop inventory, owned cards, and point transactions.
- `.data` and `.env` are ignored by Git, which keeps local databases, uploaded files, assets, and secrets out of commits.

## License

See [LICENSE](LICENSE) for details.
