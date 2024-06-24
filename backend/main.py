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
        "threshold": random.choice(THRESHOLDS),
        "keywords": []  # Add keywords here if needed
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
        "active_player": "player1",
        "turn": 1,
        "phase": "start",
        "waiting_for_start_action": True,
        "waiting_for_resource_selection": False,
        "action_stack": [],
        "waiting_for_response": False
    }
    
    # Reset game state
    for player in game_state["players"]:
        game_state["players"][player]["deck"] = [
            create_card(f"Card{i}", random.choice(CARD_TYPES)) for i in range(30)
        ]
        random.shuffle(game_state["players"][player]["deck"])
        game_state["players"][player]["hand"] = [game_state["players"][player]["deck"].pop() for _ in range(5)]
        game_state["players"][player]["faction"] = create_faction_card(f"{player} Faction")
    
    emit_game_update()
    return jsonify({"message": "Game started", "state": game_state})

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

    emit_game_update()
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

    emit_game_update()
    return jsonify({"message": f"Played resource: {card_name}", "state": game_state})

@app.route('/api/cancel_resource_selection', methods=['POST'])
def cancel_resource_selection():
    global game_state
    
    if not game_state["waiting_for_resource_selection"]:
        return jsonify({"error": "Not waiting for resource selection"}), 400

    game_state["waiting_for_resource_selection"] = False
    game_state["waiting_for_start_action"] = True

    emit_game_update()
    return jsonify({"message": "Resource selection cancelled", "state": game_state})

@app.route('/api/play_card', methods=['POST'])
def play_card():
    global game_state
    data = request.json
    player = data.get('player')
    card_name = data.get('card')
    
    if player != game_state["active_player"]:
        return jsonify({"error": "Not your turn to act"}), 400
    
    player_state = game_state["players"][player]
    card = next((c for c in player_state["hand"] if c["name"] == card_name), None)
    
    if not card:
        return jsonify({"error": "Card not in hand"}), 400
    
    if game_state["current_player"] != player:
        if card["type"] not in ["Tactic"] and "TACTICAL" not in card.get("keywords", []):
            return jsonify({"error": "Cannot play this card type during opponent's turn"}), 400
    
    if len(player_state["resources"]) < card["cost"]:
        return jsonify({"error": "Not enough resources"}), 400
    
    game_state["action_stack"].append({"type": "play_card", "player": player, "card": card})
    game_state["active_player"] = "player2" if player == "player1" else "player1"
    game_state["waiting_for_response"] = True
    
    emit_game_update()
    return jsonify({"message": f"Card {card_name} added to stack", "state": game_state})

@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    global game_state
    current_player = game_state["current_player"]
    
    if current_player != game_state["active_player"]:
        return jsonify({"error": "Not your turn to end"}), 400

    # Add an "end turn" action to the stack
    game_state["action_stack"].append({"type": "end_turn", "player": current_player})
    
    # Switch active player to allow for response
    game_state["active_player"] = "player2" if current_player == "player1" else "player1"
    game_state["waiting_for_response"] = True

    emit_game_update()
    return jsonify({"message": "Turn ending, waiting for response", "state": game_state})

@app.route('/api/draw_card', methods=['POST'])
def draw_card():
    global game_state
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    
    data = request.get_json()
    player = data.get('player')
    
    if not player:
        return jsonify({"error": "Player not specified"}), 400
    
    print(f"Received draw_card request for player: {player}")
    player_state = game_state["players"][player]

    if len(player_state["resources"]) < 3:
        print(f"Not enough resources to draw a card for {player}")
        return jsonify({"error": "Not enough resources to draw a card"}), 400

    # Add the draw card action to the stack
    game_state["action_stack"].append({"type": "draw_card", "player": player})
    
    # Switch active player to allow for response
    game_state["active_player"] = "player2" if player == "player1" else "player1"
    game_state["waiting_for_response"] = True

    print(f"Draw card action added to stack for {player}")
    emit_game_update()
    return jsonify({"message": "Draw card action added to stack", "state": game_state})

@app.route('/api/play_additional_resource', methods=['POST'])
def play_additional_resource():
    global game_state
    data = request.json
    player = data.get('player')
    card_name = data.get('card')
    face_up = data.get('face_up', False)
    
    print(f"Received play_additional_resource request for player: {player}")  # Add this line
    player_state = game_state["players"][player]

    if len(player_state["resources"]) < 4:
        print(f"Not enough resources to play additional resource for {player}")  # Add this line
        return jsonify({"error": "Not enough resources to play additional resource"}), 400

    card = next((c for c in player_state["hand"] if c["name"] == card_name), None)
    if not card:
        print(f"Card {card_name} not found in hand for {player}")  # Add this line
        return jsonify({"error": "Card not in hand"}), 400

    if face_up and card["type"] != "Resource":
        print(f"Attempted to play non-Resource card face-up as resource for {player}")  # Add this line
        return jsonify({"error": "Only Resource cards can be played face-up as resources"}), 400

    # Add the play additional resource action to the stack
    game_state["action_stack"].append({"type": "play_additional_resource", "player": player, "card": card, "face_up": face_up})
    
    # Switch active player to allow for response
    game_state["active_player"] = "player2" if player == "player1" else "player1"
    game_state["waiting_for_response"] = True

    print(f"Play additional resource action added to stack for {player}")  # Add this line
    emit_game_update()
    return jsonify({"message": "Play additional resource action added to stack", "state": game_state})

@app.route('/api/respond', methods=['POST'])
def respond():
    global game_state
    data = request.json
    player = data.get('player')
    response = data.get('response')
    
    if player != game_state["active_player"]:
        return jsonify({"error": "Not your turn to respond"}), 400
    
    if response == "NO_RESPONSE":
        resolve_action_stack()
    elif response == "RESPONSE":
        game_state["waiting_for_response"] = True
        # The client should follow up with a play_card request
    else:
        return jsonify({"error": "Invalid response"}), 400
    
    emit_game_update()
    return jsonify({"message": "Response processed", "state": game_state})

def resolve_action_stack():
    global game_state
    while game_state["action_stack"]:
        action = game_state["action_stack"].pop(0)
        if action["type"] == "play_card":
            resolve_play_card(action)
        elif action["type"] == "end_turn":
            resolve_end_turn(action)
        elif action["type"] == "draw_card":
            resolve_draw_card(action)
        elif action["type"] == "play_additional_resource":
            resolve_play_additional_resource(action)
    game_state["waiting_for_response"] = False
    game_state["active_player"] = game_state["current_player"]
    emit_game_update()

def resolve_play_card(action):
    global game_state
    player = action["player"]
    card = action["card"]
    player_state = game_state["players"][player]
    
    # Remove card from hand if it's still there
    if any(c["name"] == card["name"] for c in player_state["hand"]):
        player_state["hand"] = [c for c in player_state["hand"] if c["name"] != card["name"]]
    
    # Pay the cost
    for _ in range(card["cost"]):
        if player_state["resources"]:
            resource = player_state["resources"].pop()
            player_state["attached_resources"].append(resource)
    
    # Put card into play or resolve its effect
    if card["type"] in ["Character", "Item", "Location"]:
        player_state["in_play"].append(card)
    elif card["type"] == "Tactic":
        player_state["discard"].append(card)
        # Resolve tactic effect here
    elif card["type"] == "Resource":
        player_state["resources"].append(card)
    
    print(f"Card {card['name']} resolved for {player}")

def resolve_end_turn(action):
    global game_state
    current_player = action["player"]
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

    # Start the next turn
    new_current_player = game_state["current_player"]
    new_player_state = game_state["players"][new_current_player]

    # Detach all resources for the new player
    new_player_state["resources"].extend(new_player_state["attached_resources"])
    new_player_state["attached_resources"] = []

    game_state["phase"] = "start"
    game_state["waiting_for_start_action"] = True
    game_state["waiting_for_resource_selection"] = False
    game_state["active_player"] = new_current_player

    print(f"Turn ended for {current_player}, new turn started for {new_current_player}")

def resolve_draw_card(action):
    global game_state
    player = action["player"]
    player_state = game_state["players"][player]

    if len(player_state["resources"]) < 3:
        print(f"Error: {player} doesn't have enough resources to draw a card")
        return

    # Pay the cost
    for _ in range(3):
        resource = player_state["resources"].pop()
        player_state["attached_resources"].append(resource)

    # Draw a card
    if player_state["deck"]:
        drawn_card = player_state["deck"].pop()
        player_state["hand"].append(drawn_card)
        print(f"{player} drew a card")
    else:
        print(f"{player} has no cards left in the deck")

def resolve_play_additional_resource(action):
    global game_state
    player = action["player"]
    card = action["card"]
    face_up = action["face_up"]
    player_state = game_state["players"][player]

    if len(player_state["resources"]) < 4:
        print(f"Error: {player} doesn't have enough resources to play additional resource")
        return

    # Pay the cost
    for _ in range(4):
        resource = player_state["resources"].pop()
        player_state["attached_resources"].append(resource)

    # Play the resource
    player_state["hand"].remove(card)
    card["face_up"] = face_up
    player_state["resources"].append(card)

    print(f"{player} played additional resource: {card['name']}")

def emit_game_update():
    global game_state
    # Create a copy of the game state with the action stack as a list
    emitted_state = {**game_state, 'action_stack': list(game_state['action_stack'])}
    socketio.emit('game_update', emitted_state)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    socketio.run(app, debug=True)
