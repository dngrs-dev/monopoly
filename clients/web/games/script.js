const playersElement = document.querySelector('.table-body-players');
const boardElement = document.querySelector('.table-body-board');

const state = {
    lobbyId: null,
    ws: null,
    playerId: null,
    gameState: null,
    board: [],
    choices: [],
    connected: false,
    playerMeta: {},
}
const events = [];

function getPlayerColor(playerId) {
    const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6'];
    return colors[playerId % colors.length];
}

function appendEvents(newEvents) {
    events.push(...newEvents);
}

function closeAllMenus(exceptCard = null) {
    document.querySelectorAll('.table-body-players-card.menu-open').forEach((card) => {
        if (card === exceptCard) return;
        card.classList.remove('menu-open');
    });
}

playersElement.addEventListener('click', (event) => {
    if (event.target.closest('.table-body-players-card-menu')) {
        // Clicked inside menu, do nothing
        return;
    }

    const card = event.target.closest('.table-body-players-card');
    if (!card) return;

    const wasOpen = card.classList.contains('menu-open');
    closeAllMenus();
    if (!wasOpen) {
        card.classList.add('menu-open');
    }
});

document.addEventListener('click', (event) => {
    if (!event.target.closest('.table-body-players-card')) {
        closeAllMenus();
    }
});

function renderPlayers() {
    if (!state.gameState || !state.gameState.players) return;

    playersElement.innerHTML = '';

    state.gameState.players.forEach((player) => {
        const card = document.createElement('div');
        card.className = 'table-body-players-card';
        card.classList.add(player.id === state.playerId ? 'self' : 'other');
        card.classList.add(player.id === state.gameState.current_player_id ? 'active' : 'inactive');

        // Body
        const body = document.createElement('div');
        body.className = 'table-body-players-card-body';

        const meta = state.playerMeta[player.id] || {};
        console.log('Meta for player', player.id, meta);

        // Avatar
        const avatar = document.createElement('img');
        avatar.className = 'table-body-players-card-body-avatar';
        avatar.src = meta.avatar_url || '/avatars';
        avatar.alt = meta.display_name || 'Avatar';

        // Name
        const name = document.createElement('div');
        name.className = 'table-body-players-card-body-name';
        const _status = document.createElement('div');
        _status.className = '_status';
        
        const _name = document.createElement('div');
        _name.className = '_name';
        _name.textContent = meta.display_name || `Player ${player.id}`;

        const _muted = document.createElement('div');
        _muted.className = '_muted';

        const _ignored = document.createElement('div');
        _ignored.className = '_ignored';
        
        name.append(_status, _name, _muted, _ignored);

        // Money
        const money = document.createElement('div');
        money.className = 'table-body-players-card-body-money';
        money.textContent = `${player.balance} $`;

        // Timer
        const timer = document.createElement('div');
        timer.className = 'table-body-players-card-body-timer';

        body.append(avatar, name, money, timer);

        // Menu
        const menu = document.createElement('div');
        menu.className = 'table-body-players-card-menu';

        const _profile = document.createElement('div');
        _profile.className = '_profile';
        _profile.textContent = 'Profile';
        _profile.addEventListener('click', () => {
            const newWindow = window.open(`/profile/${meta.profile_link}`, '_blank', 'noopener,noreferrer');
            if (newWindow) newWindow.opener = null;
        });

        // Only for self user
        const _leave = document.createElement('div');
        _leave.className = '_leave';
        _leave.textContent = 'Leave';
        _leave.addEventListener('click', () => {
            // TODO: Add confirmation modal and also make the player bankrupt instead of just leaving the game
            if (confirm('Are you sure you want to leave the game?')) {
                state.ws.close();
                window.location.href = '/lobbies';
            }
        });

        // Only for other users
        const _contract = document.createElement('div');
        _contract.className = '_contract';
        _contract.textContent = 'Contract';

        const _ignore = document.createElement('div');
        _ignore.className = '_ignore';
        _ignore.textContent = 'Ignore';
        // TODO: Implement ignore logic (unignore if already ignored)

        const _report = document.createElement('div');
        _report.className = '_report';
        _report.textContent = 'Report';

        menu.append(_profile);
        if (player.id === state.playerId) {
            menu.append(_leave);
        } else {
            menu.append(_contract, _ignore, _report);
        }

        // Current player logic
        if (player.id === state.gameState.current_player_id) {
            // TODO: Add timer logic + styling + status
            _status.textContent = 'Turn';
            body.style.backgroundColor = getPlayerColor(player.id) + '33'; // CHANGE TO THE BORDER
        }

        card.append(body, menu);
        playersElement.appendChild(card);
    });
}

function setConnectionStatus(connected) {
    state.connected = connected;
}

function parseLobbyId() {
    const segments = window.location.pathname.split('/').filter(Boolean);
    return segments[segments.length - 1] || null;
}

function renderChoices() {

}

function renderBoard() {
    if (!state.board) return;

    boardElement.innerHTML = '';

    state.board.forEach((cell) => {
        console.log('Rendering board cell:', cell);
        const cellElement = document.createElement('div');
        cellElement.className = 'table-body-board-cell';

        boardElement.append(cellElement);
    });
}

function renderAll() {
    renderPlayers();
    renderBoard();
}

function connectWebSocket() {
    if (!state.lobbyId) return;
    if (state.ws) {
        state.ws.close();
    }

    const wsProtocol = location.protocol === 'https:' ? 'wss' : 'ws';
    state.ws = new WebSocket(`${wsProtocol}://${location.host}/ws/games/${state.lobbyId}`);

    state.ws.onopen = () => setConnectionStatus(true);

    state.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === 'init') {
            console.log('Received init message:', msg);
            state.playerId = msg.player_id;
            state.gameState = msg.state;
            state.board = msg.board;
            state.choices = msg.choices || [];
            state.playerMeta = msg.player_meta || {};
            setConnectionStatus(true);
            renderAll();
            return;
        }

        if (msg.type === 'state') {
            state.gameState = msg.state;
            appendEvents(msg.events || []);
            renderAll();
        }

        if (msg.type === 'board') {
            state.board = msg.board;
            renderBoard();
        }

        if (msg.type === 'choices') {
            state.choices = msg.choices || [];
            renderChoices();
        }
    };

    state.ws.onclose = (event) => {
        setConnectionStatus(false);
        if (event.code === 1008) {
            window.location.href = '/login';
        }
    };
}


function init() {
    state.lobbyId = parseLobbyId();
    connectWebSocket();
}

init();