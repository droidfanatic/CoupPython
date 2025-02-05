from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit, Namespace
import random
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

CORS(app, resources={r"/*": {"origins": "*"}})

# Lobby state
lobby = {
    "players": [],
    "max_players": 14,
    "game_started": False
}

game = {
    "currentPlayerTurn": 0,
    "playerCount": 0,
    "deck": [],
    "hands": []
}

unshuffledDeck = [
    "Captain",
    "Assassin",
    "Duke",
    "Contesta",
    "Ambassador"
]


class GameNamespace(Namespace):
    def on_connect(self):
        print('Client connected')

    def on_disconnect(self):
        print('Client disconnected')
        # Handle player disconnection
        for player in lobby["players"]:
            if not player:  # Check disconnected players
                lobby["players"].remove(player)
                emit('player_left', {"players": lobby["players"]}, broadcast=True, namespace='/game')

    def on_join(self, data):
        username = data.get('username')
        if not username:
            emit('error', {"error": "Username is required"}, namespace='/game')
            return

        if len(lobby["players"]) >= lobby["max_players"]:
            emit('error', {"error": "Lobby is full"}, namespace='/game')
            return

        if username in lobby["players"]:
            emit('error', {"error": "Username already in the lobby"}, namespace='/game')
            return

        lobby["players"].append(username)
        emit('player_joined', {"players": lobby["players"]}, broadcast=True, namespace='/game')

    def on_leave(self, data):
        username = data.get('username')
        if username not in lobby["players"]:
            emit('error', {"error": "Invalid username"}, namespace='/game')
            return

        lobby["players"].remove(username)
        emit('player_left', {"players": lobby["players"]}, broadcast=True, namespace='/game')


socketio.on_namespace(GameNamespace('/game'))


@app.route('/reset', methods=['GET'])
def reset_game():
    lobby["players"].clear()
    lobby["game_started"] = False

    game["currentPlayerTurn"] = 0
    game["playerCount"] = 0
    game["deck"].clear()
    game["hands"].clear()
    return jsonify({"Message": "Game has been reset"}), 200


@app.route('/lobby', methods=['GET'])
def get_lobby():
    return jsonify({"players": lobby["players"]}), 200


@app.route('/start', methods=['POST'])
def start_game():
    if lobby["game_started"]:
        return jsonify({"error": "Game already started"}), 400

    if len(lobby["players"]) < 2:
        return jsonify({"error": "At least 2 players are required to start the game"}), 400

    game["playerCount"] = len(lobby["players"])
    if game["playerCount"] <= 6:
        for i in range(3):
            game["deck"].extend(unshuffledDeck)
    elif game["playerCount"] <= 9:
        for i in range(4):
            game["deck"].extend(unshuffledDeck)
    elif game["playerCount"] <= 11:
        for i in range(5):
            game["deck"].extend(unshuffledDeck)
    elif game["playerCount"] <= 13:
        for i in range(6):
            game["deck"].extend(unshuffledDeck)
    elif game["playerCount"] <= 15:
        for i in range(7):
            game["deck"].extend(unshuffledDeck)

    shuffleDeck()
    dealHands()

    lobby["game_started"] = True
    emit('game_started', {"players": lobby["players"]}, broadcast=True, namespace='/game')
    return jsonify({"message": "Game started"})


@app.route('/hand', methods=['GET'])
def get_hand():
    data = request.json
    username = data.get('username')
    return jsonify({"hand": game["hands"][lobby["players"].index(username)]}), 200


@socketio.on('ping_lobby')
def ping_lobby():
    emit('lobby_update', {"players": lobby["players"], "game_started": lobby["game_started"]}, namespace='/game')


def shuffleDeck():
    random.shuffle(game["deck"])


def dealHands():
    for i in range(game["playerCount"]):
        game["hands"].append([])

    for i in range(2):
        for j in range(game["playerCount"]):
            game["hands"][j].append(game["deck"].pop(0))


if __name__ == '__main__':
    socketio.run(app, debug=True)
