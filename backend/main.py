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
        "waiting_for_response": False,
        "resolving_stack": False,
        "resolving_trigger_or_cost": False,
        "pending_action": None,
        "last_to_pass": None
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
    elif action == "resource":
        game_state["waiting_for_resource_selection"] = True
    else:
        return jsonify({"error": "Invalid action"}), 400

    game_state["waiting_for_start_action"] = False
    game_state["phase"] = "main"
    game_state["active_player"] = current_player
    game_state["waiting_for_response"] = False

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
    
    if game_state["waiting_for_response"]:
        return jsonify({"error": "Waiting for response to previous action"}), 400
    
    player_state = game_state["players"][player]
    card = next((c for c in player_state["hand"] if c["name"] == card_name), None)
    
    if not card:
        return jsonify({"error": "Card not in hand"}), 400
    
    if game_state["current_player"] != player:
        if card["type"] not in ["Tactic"] and "TACTICAL" not in card.get("keywords", []):
            return jsonify({"error": "Cannot play this card type during opponent's turn"}), 400
    
    if len(player_state["resources"]) < card["cost"]:
        return jsonify({"error": "Not enough resources"}), 400
    
    # Pay the cost immediately
    for _ in range(card["cost"]):
        resource = player_state["resources"].pop()
        player_state["attached_resources"].append(resource)
    
    # Remove card from hand
    player_state["hand"].remove(card)
    
    # Add the play card action to the stack
    game_state["pending_action"] = {"type": "play_card", "player": player, "card": card}
    game_state["active_player"] = "player2" if player == "player1" else "player1"
    game_state["waiting_for_response"] = True
    game_state["last_to_pass"] = None
    
    emit_game_update()
    return jsonify({"message": f"Card {card_name} added to stack", "state": game_state})

@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    global game_state
    current_player = game_state["current_player"]
    
    if current_player != game_state["active_player"]:
        return jsonify({"error": "Not your turn to end"}), 400

    game_state["pending_action"] = {"type": "end_turn", "player": current_player}
    game_state["active_player"] = "player2" if current_player == "player1" else "player1"
    game_state["waiting_for_response"] = True
    game_state["last_to_pass"] = None

    emit_game_update()
    return jsonify({"message": "Turn ending, waiting for response", "state": game_state})


@app.route('/api/draw_card', methods=['POST'])
def draw_card():
    global game_state
    data = request.json
    player = data.get('player')
    player_state = game_state["players"][player]

    if len(player_state["resources"]) < 3:
        return jsonify({"error": "Not enough resources to draw a card"}), 400

    # Pay the cost immediately
    for _ in range(3):
        resource = player_state["resources"].pop()
        player_state["attached_resources"].append(resource)

    game_state["pending_action"] = {"type": "draw_card", "player": player}
    game_state["active_player"] = "player2" if player == "player1" else "player1"
    game_state["waiting_for_response"] = True
    game_state["last_to_pass"] = None

    emit_game_update()
    return jsonify({"message": "Draw card action added, waiting for response", "state": game_state})

def resolve_action(action):
    if action["type"] == "end_turn":
        resolve_end_turn(action)
    elif action["type"] == "draw_card":
        resolve_draw_card(action)
    # Add other action types as needed

@app.route('/api/play_additional_resource', methods=['POST'])
def play_additional_resource():
    global game_state
    data = request.json
    player = data.get('player')
    card_name = data.get('card')
    face_up = data.get('face_up', False)

    player_state = game_state["players"][player]

    if len(player_state["resources"]) < 4:
        return jsonify({"error": "Not enough resources to play additional resource"}), 400

    card = next((c for c in player_state["hand"] if c["name"] == card_name), None)
    if not card:
        return jsonify({"error": "Card not in hand"}), 400

    if face_up and card["type"] != "Resource":
        return jsonify({"error": "Only Resource cards can be played face-up as resources"}), 400

    # Pay the cost immediately
    for _ in range(4):
        resource = player_state["resources"].pop()
        player_state["attached_resources"].append(resource)

    # Remove card from hand
    player_state["hand"].remove(card)

    # Add the play additional resource action to the stack
    game_state["action_stack"].append({"type": "play_additional_resource", "player": player, "card": card, "face_up": face_up})

    if not game_state["resolving_stack"]:
        start_resolving_stack()
    else:
        # Switch active player to allow for response
        game_state["active_player"] = "player2" if player == "player1" else "player1"
        game_state["waiting_for_response"] = True

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
        if game_state["pending_action"]["type"] == "end_turn":
            resolve_end_turn(game_state["pending_action"])
            game_state["pending_action"] = None
        else:
            if game_state["last_to_pass"] is None:
                game_state["last_to_pass"] = player
                game_state["active_player"] = "player2" if player == "player1" else "player1"
            else:
                resolve_action(game_state["pending_action"])
                game_state["pending_action"] = None
                game_state["last_to_pass"] = None
    elif response == "RESPONSE":
        game_state["last_to_pass"] = None
        game_state["waiting_for_response"] = False
        # The client should follow up with a play_card or other action request
    else:
        return jsonify({"error": "Invalid response"}), 400
    
    emit_game_update()
    return jsonify({"message": "Response processed", "state": game_state})

def start_resolving_stack():
    global game_state
    game_state["resolving_stack"] = True
    resolve_top_action()

def resolve_top_action():
    global game_state
    if game_state["action_stack"]:
        action = game_state["action_stack"].pop(0)
        if action["type"] == "play_card":
            resolve_play_card(action)
        elif action["type"] == "end_turn":
            resolve_end_turn(action)
        elif action["type"] == "draw_card":
            resolve_draw_card(action)
        elif action["type"] == "play_additional_resource":
            resolve_play_additional_resource(action)

        # After resolving, switch active player and wait for response
        game_state["active_player"] = "player2" if game_state["active_player"] == "player1" else "player1"
        game_state["waiting_for_response"] = True
    else:
        # If the stack is empty, we're done resolving
        game_state["resolving_stack"] = False
        game_state["waiting_for_response"] = False
        game_state["active_player"] = game_state["current_player"]

    emit_game_update()

def resolve_play_card(action):
    global game_state
    player = action["player"]
    card = action["card"]
    player_state = game_state["players"][player]

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
    game_state["resolving_stack"] = False

    print(f"Turn ended for {current_player}, new turn started for {new_current_player}")
    emit_game_update()

def resolve_draw_card(action):
    global game_state
    player = action["player"]
    player_state = game_state["players"][player]

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

    # Play the resource
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
