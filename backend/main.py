from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import random

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Card types
CARD_TYPES = ["Character", "Item", "Tactic", "Location", "Resource"]
THRESHOLDS = ["Rage", "Greed", "Obsession", "Elitism", "Deception"]

# Global game state
game_state = None

def create_card(name, card_type):
    return {
        "name": name,
        "type": card_type,
        "cost": random.randint(0, 3),
        "threshold": random.choice(THRESHOLDS)
    }

def create_faction_card(name):
    return {
        "name": name,
        "type": "Faction",
        "start_turn_action": "draw_or_resource"
    }

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/api/start_game', methods=['POST'])
def start_game():
    global game_state
    game_state = {
        "players": {
            "player1": {
                "hand": [], "deck": [], "resources": [], "attached_resources": [], "in_play": [],
                "discard": [], "removed": [], "faction": None
            },
            "player2": {
                "hand": [], "deck": [], "resources": [], "attached_resources": [], "in_play": [],
                "discard": [], "removed": [], "faction": None
            }
        },
        "current_player": "player1",
        "turn": 1,
        "phase": "start",
        "waiting_for_start_action": True,
        "waiting_for_resource_selection": False
    }
    
    # Reset game state
    for player in game_state["players"]:
        game_state["players"][player]["deck"] = [
            create_card(f"Card{i}", random.choice(CARD_TYPES)) for i in range(30)
        ]
        random.shuffle(game_state["players"][player]["deck"])
        game_state["players"][player]["hand"] = [game_state["players"][player]["deck"].pop() for _ in range(5)]
        game_state["players"][player]["faction"] = create_faction_card(f"{player} Faction")
    
    socketio.emit('game_update', game_state)
    return jsonify({"message": "Game started", "state": game_state})

@app.route('/api/reset_turn', methods=['POST'])
def reset_turn():
    global game_state
    current_player = game_state["current_player"]
    player_state = game_state["players"][current_player]

    if game_state["phase"] != "start" or not game_state["waiting_for_start_action"]:
        return jsonify({"error": "Can only reset at the start of a turn"}), 400

    # Reset turn state
    game_state["waiting_for_start_action"] = True
    game_state["waiting_for_resource_selection"] = False
    game_state["phase"] = "start"

    socketio.emit('game_update', game_state)
    return jsonify({"message": "Turn reset", "state": game_state})

@app.route('/api/start_turn', methods=['POST'])
def start_turn():
    global game_state
    current_player = game_state["current_player"]
    player_state = game_state["players"][current_player]

    # Detach all resources
    player_state["resources"].extend(player_state["attached_resources"])
    player_state["attached_resources"] = []

    # Set waiting for start action
    game_state["waiting_for_start_action"] = True
    game_state["phase"] = "start"

    socketio.emit('game_update', game_state)
    return jsonify({"message": "Turn started", "state": game_state})

@app.route('/api/choose_start_action', methods=['POST'])
def choose_start_action():
    global game_state
    data = request.json
    action = data.get('action')
    
    if not game_state["waiting_for_start_action"]:
        return jsonify({"error": "Not waiting for start action"}), 400

    current_player = game_state["current_player"]
    player_state = game_state["players"][current_player]

    if action == "draw":
        if player_state["deck"]:
            drawn_card = player_state["deck"].pop()
            player_state["hand"].append(drawn_card)
            game_state["waiting_for_start_action"] = False
            game_state["phase"] = "main"
    elif action == "resource":
        game_state["waiting_for_resource_selection"] = True
        game_state["waiting_for_start_action"] = False
    else:
        return jsonify({"error": "Invalid action"}), 400

    socketio.emit('game_update', game_state)
    return jsonify({"message": f"Performed start action: {action}", "state": game_state})

@app.route('/api/play_resource', methods=['POST'])
def play_resource():
    global game_state
    data = request.json
    card_name = data.get('card')
    face_up = data.get('face_up', False)
    
    if not game_state["waiting_for_resource_selection"]:
        return jsonify({"error": "Not waiting for resource selection"}), 400

    current_player = game_state["current_player"]
    player_state = game_state["players"][current_player]

    card = next((c for c in player_state["hand"] if c["name"] == card_name), None)
    if not card:
        return jsonify({"error": "Card not in hand"}), 400

    if face_up and card["type"] != "Resource":
        return jsonify({"error": "Only Resource cards can be played face-up as resources"}), 400

    player_state["hand"].remove(card)
    card["face_up"] = face_up
    player_state["resources"].append(card)

    game_state["waiting_for_resource_selection"] = False
    game_state["phase"] = "main"

    socketio.emit('game_update', game_state)
    return jsonify({"message": f"Played resource: {card_name}", "state": game_state})

@app.route('/api/cancel_resource_selection', methods=['POST'])
def cancel_resource_selection():
    global game_state
    
    if not game_state["waiting_for_resource_selection"]:
        return jsonify({"error": "Not waiting for resource selection"}), 400

    game_state["waiting_for_resource_selection"] = False
    game_state["waiting_for_start_action"] = True

    socketio.emit('game_update', game_state)
    return jsonify({"message": "Resource selection cancelled", "state": game_state})

@app.route('/api/play_card', methods=['POST'])
def play_card():
    global game_state
    data = request.json
    player = data.get('player')
    card_name = data.get('card')
    
    if player != game_state["current_player"]:
        return jsonify({"error": "Not your turn"}), 400
    
    if game_state["phase"] != "main":
        return jsonify({"error": "You can only play cards during the main phase"}), 400
    
    player_state = game_state["players"][player]
    card = next((c for c in player_state["hand"] if c["name"] == card_name), None)
    
    if not card:
        return jsonify({"error": "Card not in hand"}), 400
    
    if card["type"] == "Resource":
        return jsonify({"error": "Cannot play Resource cards directly"}), 400
    
    if len(player_state["resources"]) < card["cost"]:
        return jsonify({"error": "Not enough resources"}), 400
    
    # Remove card from hand
    player_state["hand"].remove(card)
    
    # Pay the cost
    for _ in range(card["cost"]):
        resource = player_state["resources"].pop()
        player_state["attached_resources"].append(resource)
    
    # Put card into play or resolve its effect
    if card["type"] in ["Character", "Item", "Location"]:
        player_state["in_play"].append(card)
    elif card["type"] == "Tactic":
        player_state["discard"].append(card)
        # Resolve tactic effect here
    
    socketio.emit('game_update', game_state)
    return jsonify({"message": f"Played card: {card_name}", "state": game_state})

@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    global game_state
    current_player = game_state["current_player"]
    player_state = game_state["players"][current_player]

    # TODO: Resolve "at the end of your turn" effects

    # Discard down to maximum hand size
    max_hand_size = 7
    while len(player_state["hand"]) > max_hand_size:
        discarded_card = player_state["hand"].pop()
        player_state["discard"].append(discarded_card)

    # Switch to next player
    game_state["current_player"] = "player2" if current_player == "player1" else "player1"
    game_state["turn"] += 1
    game_state["phase"] = "start"
    game_state["waiting_for_start_action"] = True
    game_state["waiting_for_resource_selection"] = False

    socketio.emit('game_update', game_state)
    return jsonify({"message": "Turn ended", "state": game_state})

@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    socketio.run(app, debug=True)
