from flask import Blueprint, jsonify, request, session
# 🔑 NEW IMPORTS for Authentication
from models import db, PlayerManual, PropertyManual, Card, GameStateManual, User, bcrypt 
import random

api = Blueprint("api", __name__)

# ----------------------------------------------------
# 🔑 AUTHENTICATION ROUTES
# ----------------------------------------------------
@api.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    # Store user id in session (simplistic manual session handling)
    session['user_id'] = new_user.id 

    return jsonify(new_user.to_dict()), 201

@api.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        # Store user id in session
        session['user_id'] = user.id
        return jsonify(user.to_dict()), 200
    
    return jsonify({"error": "Invalid username or password"}), 401

@api.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Successfully logged out"}), 200

@api.route('/check-session', methods=['GET'])
def check_session():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify(user.to_dict()), 200
    
    return jsonify({"message": "Not authenticated"}), 401

# ----------------------------------------------------
# Helper Functions/Data (unchanged)
# ----------------------------------------------------

# Simplified Map for Non-Property Tiles (Used in /land-on-tile for messages/logic)
NON_PROPERTY_MAP = {
# ... (NON_PROPERTY_MAP code unchanged) ...
}

# HELPER FUNCTION: ELIMINATE PLAYER (unchanged)
def eliminate_player(player_id):
# ... (eliminate_player code unchanged) ...
    player = PlayerManual.query.get(player_id)
    
    if not player:
        return 0, False # Player already gone
    
    # 1. Clear ownership of all properties
    for prop in PropertyManual.query.filter_by(owner_id=player_id).all():
        prop.owner_id = None
    
    # 2. Delete the Player
    db.session.delete(player)
    db.session.commit()
    
    # 3. Check for Game Over
    remaining_players = PlayerManual.query.count()
    game_over = remaining_players == 1
    
    return remaining_players, game_over

# -----------------------------
# Players
# -----------------------------
@api.route("/players", methods=["GET"])
def get_players():
    players = PlayerManual.query.all()
    return jsonify([p.to_dict() for p in players])

@api.route("/players", methods=["POST"])
def add_player():
    data = request.json
    # 🔑 Optional: Get user_id from session to link the player
    user_id = session.get('user_id') 
    
    # 🔑 Pass user_id if present
    new_player = PlayerManual(name=data["name"], user_id=user_id) 
    
    db.session.add(new_player)
    db.session.commit()
    return jsonify(new_player.to_dict()), 201


# -----------------------------
# Game State (unchanged)
# -----------------------------
@api.route("/game-state", methods=["GET"])
def get_game_state():
# ... (get_game_state code unchanged) ...
    state = GameStateManual.query.first()
    if not state:
        state = GameStateManual(current_player=0, turn_number=1)
        db.session.add(state)
        db.session.commit()
    return jsonify(state.to_dict())


# ----------------------------------------------------
# 🎲 Roll Dice + Move Player (unchanged)
# ----------------------------------------------------
@api.route("/roll-dice", methods=["POST"])
def roll_dice():
# ... (roll_dice code unchanged) ...
    data = request.json
    player_id_attempting_roll = data.get("player_id")

    state = GameStateManual.query.first()
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all() 
    
    if not state or not players or not player_id_attempting_roll:
        return jsonify({"error": "Game not initialized or Player ID missing"}), 400

    try:
        current_turn_player = players[state.current_player]
    except IndexError:
        return jsonify({"error": "Invalid current player index in state"}), 500

    player_attempting_roll = PlayerManual.query.get(player_id_attempting_roll)

    if not player_attempting_roll or current_turn_player.id != player_attempting_roll.id:
        return jsonify({"error": f"❌ It's not {current_turn_player.name}'s turn."}), 403

    # Use 'current_turn_player' for the action
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2

    # Handle Jail logic (simplified release)
    if current_turn_player.in_jail:
        current_turn_player.in_jail = False
    
    # Save old position for Go check
    old_position = current_turn_player.position
    
    # Move player
    current_turn_player.position = (current_turn_player.position + steps) % 40

    # Handle Passing Go ($200 logic)
    message = f"🎲 {current_turn_player.name} rolled {d1} + {d2} = {steps}, moved to tile {current_turn_player.position}." 
    if current_turn_player.position < old_position:
        current_turn_player.money += 200
        message = f"💰 {current_turn_player.name} passed GO and collected $200! " + message.split("🎲")[1].strip()
    
    db.session.commit()
    
    result = {
        "dice": [d1, d2],
        "player": current_turn_player.to_dict(),
        "message": message,
        "rolled_doubles": d1 == d2, 
    }

    return jsonify(result)

# ----------------------------------------------------
# 🛑 Handle Landing on a Tile (unchanged)
# ----------------------------------------------------
@api.route("/land-on-tile", methods=["POST"])
def land_on_tile():
# ... (land_on_tile code unchanged) ...
    data = request.json
    player_id = data.get("player_id")

    player = PlayerManual.query.get(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404

    position = player.position
    property_tile = PropertyManual.query.filter_by(position=position).first()
    
    action_needed = "NONE" 
    message = f"{player.name} is at position {position}."
    tile_data = None
    
    if property_tile:
        # Case 1: Landed on a Property
        tile_data = property_tile.to_dict()
        message = f"{player.name} landed on {property_tile.name}."
        
        if property_tile.owner_id is None:
            # Unowned Property: Offer to Buy
            action_needed = "BUY"
            message += f" It costs ${property_tile.price}. Available to purchase."
            
        elif property_tile.owner_id != player_id:
            # Owned by another Player: Pay Rent
            action_needed = "PAY_RENT"
            owner = PlayerManual.query.get(property_tile.owner_id)
            message += f" Owned by {owner.name}. Must pay ${property_tile.rent} rent."
        else:
            # Owned by current Player: Do nothing
            action_needed = "OWNED"
            message += " You already own this property."
    
    else:
        # Case 2: Landed on a Non-Property Tile
        tile_info = NON_PROPERTY_MAP.get(position, {"name": "Unknown Tile", "type": "passive"})
        name = tile_info["name"]
        
        tile_data = {"position": position, "name": name, "type": tile_info["type"]}
        message = f"{player.name} landed on {name}."
        
        if tile_info["type"] in ("community_chest", "chance"):
            action_needed = tile_info["type"].upper()
        elif tile_info["type"] == "tax": 
            action_needed = "TAX"
            message += " Must pay tax."
        elif position == 30: # Go To Jail (position 30)
            action_needed = "GO_TO_JAIL"
            message += " 🚨 GO TO JAIL! Moving to position 10."
            
    return jsonify({
        "player": player.to_dict(),
        "tile": tile_data,
        "action_needed": action_needed,
        "message": message
    })


# ----------------------------------------------------
# 🔄 Next Turn (unchanged)
# ----------------------------------------------------
@api.route("/next_turn", methods=["POST"])
def next_turn():
# ... (next_turn code unchanged) ...
    try:
        state = GameStateManual.query.first()
        
        players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
        
        if not state or not players:
            if PlayerManual.query.count() == 1:
                    return jsonify({"error": "Game Over: Only one player remains."}), 400
            return jsonify({"error": "Game not initialized or no players found"}), 400

        num_players = len(players)
        
        start_index = (state.current_player + 1) % num_players
        current_index = start_index

        for _ in range(num_players):
            player_id_to_check = players[current_index].id
            
            if PlayerManual.query.get(player_id_to_check):
                state.current_player = current_index
                db.session.commit()
                return jsonify({
                    "current_player": current_index,
                    "message": f"🔄 It is now {players[current_index].name}'s turn."
                }), 200
            
            current_index = (current_index + 1) % num_players
            
            if current_index == start_index:
                break
        
        return jsonify({"error": "Could not determine next player. Check player list."}), 500

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# -----------------------------
# Buy Property (unchanged)
# -----------------------------
@api.route("/buy-property", methods=["POST"])
def buy_property():
# ... (buy_property code unchanged) ...
    data = request.json
    player = PlayerManual.query.get(data["player_id"])
    prop = PropertyManual.query.filter_by(position=data["property_position"]).first()

    if not player or not prop:
        return jsonify({"error": "Invalid request: Player or Property not found"}), 400

    if prop.owner_id:
        return jsonify({"error": "Property already owned"}), 400

    if player.money < prop.price:
        return jsonify({"error": f"Not enough money. Need ${prop.price}, have ${player.money}"}), 400

    player.money -= prop.price
    prop.owner_id = player.id
    db.session.commit()

    return jsonify({
        "message": f"🎉 {player.name} bought {prop.name} for ${prop.price}!",
        "player": player.to_dict(),
        "property": prop.to_dict()
    })


# -----------------------------
# Pay Rent (unchanged)
# -----------------------------
@api.route("/pay-rent", methods=["POST"])
def pay_rent():
# ... (pay_rent code unchanged) ...
    data = request.json
    payer = PlayerManual.query.get(data["player_id"])
    prop = PropertyManual.query.filter_by(position=data["property_position"]).first()

    if not payer or not prop or not prop.owner_id:
        return jsonify({"error": "Invalid rent action: Player/Property/Owner Missing"}), 400

    owner = PlayerManual.query.get(prop.owner_id)
    rent = prop.rent

    if payer.money < rent:
        remaining, game_over = eliminate_player(payer.id)
        
        return jsonify({
            "message": f"💥 {payer.name} went bankrupt paying rent to {owner.name}!",
            "game_over": game_over,
            "eliminated_player_id": payer.id,
            "owner": owner.to_dict(),
        }), 200

    # Standard transaction
    payer.money -= rent
    owner.money += rent
    db.session.commit()

    return jsonify({
        "message": f"💸 {payer.name} paid ${rent} rent to {owner.name}.",
        "payer": payer.to_dict(),
        "owner": owner.to_dict(),
        "property": prop.to_dict(),
        "game_over": False
    })


# -----------------------------
# Pay Tax (unchanged)
# -----------------------------
@api.route("/pay-tax", methods=["POST"])
def pay_tax():
# ... (pay_tax code unchanged) ...
    data = request.json
    player = PlayerManual.query.get(data["player_id"])
    tax_position = data["tax_position"]
    
    tax_info = NON_PROPERTY_MAP.get(tax_position)
    
    # Calculate tax amount (Income Tax 200, Luxury Tax 100)
    if tax_position == 4:
        tax_amount = 200
    elif tax_position == 38:
        tax_amount = 100
    else:
        return jsonify({"error": "Invalid tax position"}), 400

    if not player:
        return jsonify({"error": "Player not found"}), 404

    if player.money < tax_amount:
        remaining, game_over = eliminate_player(player.id)
        
        return jsonify({
            "message": f"💥 {player.name} went bankrupt paying tax!",
            "game_over": game_over,
            "eliminated_player_id": player.id,
        }), 200

    player.money -= tax_amount
    db.session.commit()

    return jsonify({
        "message": f"💸 {player.name} paid ${tax_amount} tax!",
        "player": player.to_dict(),
        "game_over": False
    })

# -----------------------------
# Go To Jail (unchanged)
# -----------------------------
@api.route("/go-to-jail", methods=["POST"])
def go_to_jail():
# ... (go_to_jail code unchanged) ...
    data = request.json
    player = PlayerManual.query.get(data["player_id"])

    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    player.position = 10 
    player.in_jail = True
    db.session.commit()

    return jsonify({
        "message": f"🚨 {player.name} sent to Jail!",
        "player": player.to_dict()
    })

# -----------------------------
# Card Endpoints (unchanged)
# ----------------------------------------------------
@api.route("/cards", methods=["GET"])
def get_cards():
# ... (get_cards code unchanged) ...
    cards = Card.query.all()
    return jsonify([c.to_dict() for c in cards])

@api.route("/cards/draw", methods=["POST"])
def draw_card():
# ... (draw_card code unchanged) ...
    cards = Card.query.all()
    if not cards:
        return jsonify({"error": "No cards available"}), 400

    card = random.choice(cards)
    return jsonify(card.to_dict())


# -----------------------------
# Reset Game (unchanged)
# -----------------------------
@api.route("/reset-game", methods=["POST"])
def reset_game():
# ... (reset_game code unchanged) ...
    """Clears all players, properties, and game state to start a new game."""
    try:
        db.session.query(PlayerManual).delete()
        db.session.query(PropertyManual).update({"owner_id": None})
        GameStateManual.query.delete()
        db.session.add(GameStateManual(current_player=0, turn_number=1))
        
        db.session.commit()
        return jsonify({"message": "Game state reset successfully."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to reset game state: {str(e)}"}), 500