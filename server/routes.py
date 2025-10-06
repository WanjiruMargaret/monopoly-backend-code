from flask import Blueprint, jsonify, request, session
# ✅ FIX: Changed relative import (.models) to absolute import (models)
from models import db, PlayerManual, PropertyManual, Card, GameStateManual, User, bcrypt 
import random

# Initialize the Blueprint
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
    
    # Store user id in session
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
# Helper Functions/Data
# ----------------------------------------------------

# Simplified Map for Non-Property Tiles
NON_PROPERTY_MAP = {
    # Lazima iwe hapa
    0: {"name": "GO", "type": "passive"},
    4: {"name": "Income Tax", "type": "tax"},
    7: {"name": "Chance", "type": "chance"},
    10: {"name": "Jail / Just Visiting", "type": "passive"},
    17: {"name": "Community Chest", "type": "community_chest"},
    20: {"name": "Free Parking", "type": "passive"},
    22: {"name": "Chance", "type": "chance"},
    30: {"name": "Go To Jail", "type": "go_to_jail"},
    33: {"name": "Community Chest", "type": "community_chest"},
    36: {"name": "Chance", "type": "chance"},
    38: {"name": "Luxury Tax", "type": "tax"},
}

# HELPER FUNCTION: ELIMINATE PLAYER
def eliminate_player(player_id):
    player = PlayerManual.query.get(player_id)
    
    if not player:
        return 0, False
    
    for prop in PropertyManual.query.filter_by(owner_id=player_id).all():
        prop.owner_id = None
    
    db.session.delete(player)
    db.session.commit()
    
    remaining_players = PlayerManual.query.count()
    game_over = remaining_players == 1
    
    return remaining_players, game_over


# KAZI MPYA YA KUSAIDIA KWA LOGIC YA TILE
def land_on_tile_logic(player_id):
    """Logic ya /land-on-tile iliyohamishwa ili iweze kutumika na /roll-dice."""
    player = PlayerManual.query.get(player_id)
    if not player:
        # Note: This should ideally not happen if called after successful roll
        return {"error": "Player not found"}

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
            action_needed = "BUY"
            message += f" It costs ${property_tile.price}. Available to purchase."
            
        elif property_tile.owner_id != player_id:
            action_needed = "PAY_RENT"
            owner = PlayerManual.query.get(property_tile.owner_id)
            message += f" Owned by {owner.name}. Must pay ${property_tile.rent} rent."
        else:
            action_needed = "NONE"  # Owned by current player, no action needed
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
        # For passive tiles (GO, Free Parking, Just Visiting), action_needed remains "NONE"

    return {
        "player": player.to_dict(),
        "tile": tile_data,
        "action_needed": action_needed,
        "message": message
    }


# ----------------------------------------------------
# 🃏 NEW HELPER FUNCTION: APPLY CARD EFFECT LOGIC
# NOTE: This assumes Card.to_dict() provides 'description', 'effect_type', and 'value'
# ----------------------------------------------------
def apply_card_effect(player_id, card_data):
    """Applies the effect of a drawn Chance or Community Chest card to the player and game state."""
    player = PlayerManual.query.get(player_id)
    state = GameStateManual.query.first()
    
    if not player or not state:
        return {"error": "Player or Game State not found"}
        
    card_message = card_data.get("description", "A mysterious card was drawn.")
    
    # Assuming Card model has these keys:
    effect_type = card_data.get("effect_type")
    value = card_data.get("value", 0)
    
    extra_message = ""
    new_action_needed = "NONE" # Default action after card is processed
    
    if effect_type == "money":
        player.money += value
        if value > 0:
            extra_message = f"Collected ${value}."
        elif value < 0:
            extra_message = f"Paid ${abs(value)}."
            
            # Check for bankruptcy after paying money
            if player.money < 0:
                # Assuming this is simplified bankruptcy where they are eliminated
                remaining, game_over = eliminate_player(player.id)
                db.session.commit()
                return {
                    "message": f"💥 {player.name} went bankrupt due to card payment! {card_message}",
                    "player": None,
                    "eliminated_player_id": player.id,
                    "game_over": game_over,
                    "status": "BANKRUPT"
                }

    elif effect_type == "move":
        old_position = player.position
        
        if value == 0: # Advance to GO (position 0)
            player.position = 0
            if old_position != 0:
                player.money += 200 # Collect $200 for passing/landing on GO
                extra_message = "Advanced to GO and collected $200!"
        
        elif value == 10: # Go To Jail (absolute position 10)
            player.position = 10
            player.in_jail = True
            extra_message = "Sent directly to Jail (position 10)!"
        
        else:
            # Relative move (e.g., -3 for "Go back 3 spaces")
            new_position = (player.position + value) % 40
            
            # Check for passing GO (only relevant if moving forward, i.e., value > 0)
            if new_position < old_position and value > 0:
                 player.money += 200
                 extra_message = "Passed GO and collected $200!"
                 
            player.position = new_position
            extra_message = f"Moved to tile {player.position}."
        
        # After a move, we need to re-evaluate the tile logic.
        land_result = land_on_tile_logic(player.id)
        new_action_needed = land_result["action_needed"] # May trigger new actions (rent, buy, tax, etc.)
        
        state.action_required = new_action_needed # Update state with the new requirement
        db.session.commit()
        
        return {
            "message": f"🃏 {card_message}. {extra_message} Now processing tile: {land_result['message']}",
            "player": player.to_dict(),
            "new_position": player.position,
            "action_required": new_action_needed,
            "status": "MOVE_COMPLETED",
            "active_tile": land_result["tile"]
        }

    elif effect_type == "get_out_of_jail":
        # Store card property on player if applicable
        player.has_get_out_of_jail_card = True 
        extra_message = "You now hold a 'Get Out of Jail Free' card."
    
    # Final cleanup for money/passive effects
    state.action_required = "NONE" 
    db.session.commit()
    
    return {
        "message": f"🃏 {card_message}. {extra_message}",
        "player": player.to_dict(),
        "action_required": "NONE",
        "status": "EFFECT_APPLIED"
    }


# -----------------------------
# Players
# -----------------------------
@api.route("/players", methods=["GET"])
def get_players():
    # Authorization check
    if not session.get('user_id'):
       return jsonify({"error": "Unauthorized"}), 401

    players = PlayerManual.query.all()
    return jsonify([p.to_dict() for p in players])

@api.route("/players", methods=["POST"])
def add_player():
    data = request.json
    user_id = session.get('user_id') 

    if not user_id:
        return jsonify({"error": "You must be logged in to create a player."}), 401

    # 🛑 TEMP FIX: Commenting out the check that prevents a single user from creating multiple players.
    # This allows the frontend to set up multiple players for a solo game/test.
    # if PlayerManual.query.filter_by(user_id=user_id).first():
    #     return jsonify({"error": "You are already registered as a player in this game."}), 400
    
    new_player = PlayerManual(name=data["name"], user_id=user_id) 
    
    db.session.add(new_player)
    db.session.commit()
    
    # Initialize GameState if it doesn't exist
    if not GameStateManual.query.first():
        db.session.add(GameStateManual(current_player=0, turn_number=1))
        db.session.commit()
        
    return jsonify(new_player.to_dict()), 201


# -----------------------------
# Game State
# -----------------------------
@api.route("/game-state", methods=["GET"])
def get_game_state():
    state = GameStateManual.query.first()
    if not state:
        state = GameStateManual(current_player=0, turn_number=1)
        db.session.add(state)
        db.session.commit()

    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    properties = PropertyManual.query.order_by(PropertyManual.position.asc()).all()

    players_list = [p.to_dict() for p in players]
    board_list = [prop.to_dict() for prop in properties]

    current_player_id = None
    try:
        current_player_id = players[state.current_player].id
    except IndexError:
        pass

    result = {
        "players": players_list,
        "board": board_list,
        "game_state": state.to_dict(),
        "current_player_id": current_player_id
    }
    return jsonify(result)


# ----------------------------------------------------
# 🎲 Roll Dice + Move Player
# ----------------------------------------------------
@api.route("/roll-dice", methods=["POST"])
def roll_dice():
    import sys
    print("[ROLL-DICE] Called", file=sys.stderr)
    data = request.json
    player_id_to_roll = data.get("player_id")

    # 🔑 1. AUTHENTICATION: Pata User aliyeingia kwenye Session
    user_id = session.get('user_id')
    if not user_id:
        print("[ROLL-DICE] Unauthorized: No user_id in session", file=sys.stderr)
        return jsonify({"error": "Unauthorized"}), 401

    # ✅ Authorization Check 1: Does the player_id exist?
    # 🛑 TEMP FIX: Relaxed authorization to allow single user to control multiple players for testing
    player_attempting_roll = PlayerManual.query.get(player_id_to_roll)
    if not player_attempting_roll:
        print(f"[ROLL-DICE] Player {player_id_to_roll} not found", file=sys.stderr)
        return jsonify({"error": "Player not found."}), 404

    # Pata Game State
    state = GameStateManual.query.first()
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    if not state or not players:
        print("[ROLL-DICE] Game not initialized", file=sys.stderr)
        return jsonify({"error": "Game not initialized"}), 400

    # Explicitly check action_required
    if state.action_required != "ROLL":
        print(f"[ROLL-DICE] Action required is '{state.action_required}', not 'ROLL'", file=sys.stderr)
        return jsonify({"error": f"Cannot roll dice. Current action required is '{state.action_required}'."}), 403

    try:
        current_turn_player = players[state.current_player]
    except IndexError:
        print("[ROLL-DICE] Invalid current player index in state", file=sys.stderr)
        return jsonify({"error": "Invalid current player index in state"}), 500

    if current_turn_player.id != player_id_to_roll:
        print(f"[ROLL-DICE] Wrong turn: {current_turn_player.id} vs {player_id_to_roll}", file=sys.stderr)
        return jsonify({"error": f"❌ It's not {current_turn_player.name}'s turn (ID: {current_turn_player.id}). Roll attempted by ID: {player_id_to_roll}."}), 403

    current_player = current_turn_player

    # 3. GAME LOGIC
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2
    print(f"[ROLL-DICE] Dice rolled: {d1}, {d2} (steps: {steps})", file=sys.stderr)

    # Handle Jail logic (simplified release)
    if current_player.in_jail:
        print(f"[ROLL-DICE] Player {current_player.name} released from jail", file=sys.stderr)
        current_player.in_jail = False

    old_position = current_player.position
    current_player.position = (current_player.position + steps) % 40

    message = f"🎲 {current_player.name} rolled {d1} + {d2} = {steps}, moved to tile {current_player.position}."
    if current_player.position < old_position:
        current_player.money += 200
        message = f"💰 {current_player.name} passed GO and collected $200! " + message.split("🎲")[1].strip()

    print(f"[ROLL-DICE] {message}", file=sys.stderr)
    land_on_result = land_on_tile_logic(current_player.id)
    print(f"[ROLL-DICE] Landed on tile: {land_on_result['message']}", file=sys.stderr)

    state.action_required = land_on_result["action_needed"]
    db.session.commit()

    result = {
        "dice": [d1, d2],
        "player": current_player.to_dict(),
        "message": message,
        "rolled_doubles": d1 == d2,
        "new_position": current_player.position,
        "action_required": land_on_result["action_needed"],
        "active_tile": land_on_result["tile"],
        "land_on_message": land_on_result["message"]
    }

    print(f"[ROLL-DICE] Returning result", file=sys.stderr)
    return jsonify(result)


# ----------------------------------------------------
# 🛑 Handle Landing on a Tile
# ----------------------------------------------------
@api.route("/land-on-tile", methods=["POST"])
def land_on_tile():
    # This route is mainly for debugging or handling post-roll actions where position doesn't change
    data = request.json
    player_id = data.get("player_id")
    
    result = land_on_tile_logic(player_id)
    
    if "error" in result:
        return jsonify(result), 404
        
    return jsonify(result)


# ----------------------------------------------------
# 🔄 Next Turn
# ----------------------------------------------------
@api.route("/next_turn", methods=["POST"])
def next_turn():
    # Authorization check: only the current player (or someone who just finished their action) should call this.
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        state = GameStateManual.query.first()
        players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
        
        if not state or not players:
            if PlayerManual.query.count() == 1:
                return jsonify({"error": "Game Over: Only one player remains."}), 400
            return jsonify({"error": "Game not initialized or no players found"}), 400

        num_players = len(players)
        
        # Start looking from the index immediately after the current one
        start_index = (state.current_player + 1) % num_players
        current_index = start_index

        for _ in range(num_players):
            player_id_to_check = players[current_index].id
            
            # Check if player still exists (i.e., not eliminated)
            if PlayerManual.query.get(player_id_to_check):
                state.current_player = current_index
                state.turn_number += 1 # Increment turn number
                # Reset action for the new player to "ROLL"
                state.action_required = "ROLL" 
                db.session.commit()
                return jsonify({
                    "current_player_id": players[current_index].id,
                    "current_player_index": current_index,
                    "turn_number": state.turn_number,
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
# Buy Property
# -----------------------------
@api.route("/buy-property", methods=["POST"])
def buy_property():
    data = request.json
    
    # Simple security check (could be enhanced by checking session user ID)
    player = PlayerManual.query.get(data.get("player_id")) 
    prop = PropertyManual.query.filter_by(position=data.get("property_position")).first()
    
    if not player or not prop:
        return jsonify({"error": "Invalid request: Player or Property not found"}), 400

    if prop.owner_id:
        return jsonify({"error": "Property already owned"}), 400
        
    # Check if this player is the one whose turn it is (authorization for game action)
    state = GameStateManual.query.first()
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    current_turn_player = players[state.current_player]

    if current_turn_player.id != player.id:
        return jsonify({"error": f"It's not {player.name}'s turn to make a move."}), 403


    if player.money < prop.price:
        return jsonify({"error": f"Not enough money. Need ${prop.price}, have ${player.money}"}), 400

    player.money -= prop.price
    prop.owner_id = player.id

    # Advance to next turn automatically
    num_players = len(players)
    state.current_player = (state.current_player + 1) % num_players
    state.turn_number += 1
    state.action_required = "ROLL"
    db.session.commit()

    return jsonify({
        "message": f"🎉 {player.name} bought {prop.name} for ${prop.price}!",
        "player": player.to_dict(),
        "property": prop.to_dict(),
        "next_player_id": players[state.current_player].id,
        "turn_number": state.turn_number,
        "action_required": state.action_required
    })


# -----------------------------
# Pay Rent
# -----------------------------
@api.route("/pay-rent", methods=["POST"])
def pay_rent():
    data = request.json
    payer = PlayerManual.query.get(data.get("player_id"))
    prop = PropertyManual.query.filter_by(position=data.get("property_position")).first()

    if not payer or not prop or not prop.owner_id:
        return jsonify({"error": "Invalid rent action: Player/Property/Owner Missing"}), 400

    # Authorization Check (Only the player whose turn it is should be paying rent)
    state = GameStateManual.query.first()
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    current_turn_player = players[state.current_player]

    if current_turn_player.id != payer.id:
        return jsonify({"error": f"It's not {payer.name}'s turn."}), 403
        
    owner = PlayerManual.query.get(prop.owner_id)
    rent = prop.rent

    if payer.money < rent:
        remaining, game_over = eliminate_player(payer.id)
        
        # Action completed, move to next turn/none required
        state.action_required = "NONE" 
        db.session.commit()
        
        return jsonify({
            "message": f"💥 {payer.name} went bankrupt paying rent to {owner.name}!",
            "game_over": game_over,
            "eliminated_player_id": payer.id,
            "owner": owner.to_dict(),
        }), 200

    # Standard transaction
    payer.money -= rent
    owner.money += rent

    # Advance to next turn automatically
    num_players = len(players)
    state.current_player = (state.current_player + 1) % num_players
    state.turn_number += 1
    state.action_required = "ROLL"
    db.session.commit()

    return jsonify({
        "message": f"💸 {payer.name} paid ${rent} rent to {owner.name}.",
        "payer": payer.to_dict(),
        "owner": owner.to_dict(),
        "property": prop.to_dict(),
        "game_over": False,
        "next_player_id": players[state.current_player].id,
        "turn_number": state.turn_number,
        "action_required": state.action_required
    })


# -----------------------------
# Pay Tax
# -----------------------------
@api.route("/pay-tax", methods=["POST"])
def pay_tax():
    data = request.json
    player = PlayerManual.query.get(data.get("player_id"))
    tax_position = data.get("tax_position")
    
    # Authorization Check
    state = GameStateManual.query.first()
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    current_turn_player = players[state.current_player]

    if current_turn_player.id != player.id:
        return jsonify({"error": f"It's not {player.name}'s turn to pay tax."}), 403

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
        state.action_required = "NONE" # Action complete (bankruptcy)
        db.session.commit()
        
        return jsonify({
            "message": f"💥 {player.name} went bankrupt paying tax!",
            "game_over": game_over,
            "eliminated_player_id": player.id,
        }), 200

    player.money -= tax_amount
    # Advance to next turn automatically
    num_players = len(players)
    state.current_player = (state.current_player + 1) % num_players
    state.turn_number += 1
    state.action_required = "ROLL"
    db.session.commit()

    return jsonify({
        "message": f"💸 {player.name} paid ${tax_amount} tax!",
        "player": player.to_dict(),
        "game_over": False,
        "next_player_id": players[state.current_player].id,
        "turn_number": state.turn_number,
        "action_required": state.action_required
    })

# -----------------------------
# Go To Jail
# -----------------------------
@api.route("/go-to-jail", methods=["POST"])
def go_to_jail():
    data = request.json
    player = PlayerManual.query.get(data.get("player_id"))
    
    # Authorization Check
    state = GameStateManual.query.first()
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    current_turn_player = players[state.current_player]

    if current_turn_player.id != player.id:
        return jsonify({"error": f"It's not {player.name}'s turn for this action."}), 403

    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    player.position = 10 
    player.in_jail = True
    
    # Action complete (player is now in jail and cannot roll)
    state.action_required = "NONE" 
    
    db.session.commit()

    return jsonify({
        "message": f"🚨 {player.name} sent to Jail!",
        "player": player.to_dict()
    })

# -----------------------------
# Card Endpoints
# ----------------------------------------------------
@api.route("/cards", methods=["GET"])
def get_cards():
    cards = Card.query.all()
    return jsonify([c.to_dict() for c in cards])

@api.route("/cards/draw", methods=["POST"])
def draw_card():
    data = request.json
    player_id_request = data.get("player_id")

    # Authorization Check: Check if this player is the one whose turn it is AND requires a card draw.
    state = GameStateManual.query.first()
    if not state:
        return jsonify({"error": "Game not initialized"}), 400
        
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    try:
        current_turn_player = players[state.current_player]
    except IndexError:
        return jsonify({"error": "Invalid current player index in state"}), 500

    if current_turn_player.id != player_id_request:
        return jsonify({"error": f"It's not {current_turn_player.name}'s turn to draw a card."}), 403

    if state.action_required not in ("CHANCE", "COMMUNITY_CHEST"):
        return jsonify({"error": "Card draw not required for the current player."}), 400

    cards = Card.query.filter_by(card_type=state.action_required.lower()).all()
    if not cards:
        return jsonify({"error": f"No {state.action_required} cards available"}), 400

    card = random.choice(cards)
    
    # Apply the card's effect and update the game state
    result = apply_card_effect(player_id_request, card.to_dict())
    
    # If the card application resulted in bankruptcy, we don't return the player object directly
    if result.get("status") == "BANKRUPT":
        return jsonify(result), 200
    
    return jsonify(result)


# -----------------------------
# Reset Game
# -----------------------------
@api.route("/reset-game", methods=["POST"])
def reset_game():
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
