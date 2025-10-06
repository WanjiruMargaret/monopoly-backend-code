from flask import Blueprint, jsonify, request
from models import db, PlayerManual, PropertyManual, Card, GameStateManual
import random

api = Blueprint("api", __name__)

# ----------------------------------------------------
# Helper Functions/Data
# ----------------------------------------------------

# Simplified Map for Non-Property Tiles (Used in /land-on-tile for messages/logic)
NON_PROPERTY_MAP = {
    0: {"name": "GO", "type": "go"},
    4: {"name": "Income Tax", "type": "tax"},
    10: {"name": "Jail (Just Visiting)", "type": "jail"},
    20: {"name": "Free Parking", "type": "free_parking"},
    30: {"name": "Go To Jail", "type": "go_to_jail"},
    2: {"name": "Community Chest", "type": "community_chest"},
    7: {"name": "Chance", "type": "chance"},
    17: {"name": "Community Chest", "type": "community_chest"},
    22: {"name": "Chance", "type": "chance"},
    33: {"name": "Community Chest", "type": "community_chest"},
    36: {"name": "Chance", "type": "chance"},
    38: {"name": "Luxury Tax", "type": "tax", "amount": 100}, # Added Luxury Tax example
}

# 🔑 NEW HELPER FUNCTION: ELIMINATE PLAYER (moved above usage)
def eliminate_player(player_id):
    """Handles player bankruptcy and elimination."""
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
    new_player = PlayerManual(name=data["name"])
    db.session.add(new_player)
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
    return jsonify(state.to_dict())


# ----------------------------------------------------
# 🎲 Roll Dice + Move Player
# ----------------------------------------------------
@api.route("/roll-dice", methods=["POST"])
def roll_dice():
    data = request.json
    player_id_attempting_roll = data.get("player_id")

    state = GameStateManual.query.first()
    # 🔑 CRITICAL: Get players *by position* to align with state.current_player index
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
        # For simplicity, release on roll or fine payment, but allow movement
        current_turn_player.in_jail = False
        # Continue to movement below
    
    # Save old position for Go check
    old_position = current_turn_player.position
    
    # Move player
    current_turn_player.position = (current_turn_player.position + steps) % 40

    # Handle Passing Go ($200 logic)
    message = f"🎲 {current_turn_player.name} rolled {d1} + {d2} = {steps}, moved to tile {current_turn_player.position}."    
    if current_turn_player.position < old_position:
        current_turn_player.money += 200
        message = f"💰 {current_turn_player.name} passed GO and collected $200!"
    else:
        message = f"🎲 {current_turn_player.name} rolled {d1} + {d2} = {steps}, moved to tile {current_turn_player.position}."

    db.session.commit()
    
    result = {
        "dice": [d1, d2],
        "player": current_turn_player.to_dict(),
        "message": message,
        "rolled_doubles": d1 == d2, 
    }

    return jsonify(result)


# ----------------------------------------------------
# 🛑 Handle Landing on a Tile (CRITICAL LOGIC)
# ----------------------------------------------------
@api.route("/land-on-tile", methods=["POST"])
def land_on_tile():
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
# 🔄 Next Turn 🔑 FIXED LOGIC
# ----------------------------------------------------
@api.route("/next_turn", methods=["POST"])
def next_turn():
    try:
        state = GameStateManual.query.first()
        
        # 🔑 CRITICAL: Always re-query the player list after a transaction/elimination
        players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
        
        if not state or not players:
            # If only one player remains, the next turn attempt confirms game over
            if PlayerManual.query.count() == 1:
                 return jsonify({"error": "Game Over: Only one player remains."}), 400
            return jsonify({"error": "Game not initialized or no players found"}), 400

        num_players = len(players)
        
        # Start looking for the next active player from the current player's *next* index
        start_index = (state.current_player + 1) % num_players
        current_index = start_index

        # Loop until a player is found (or we loop back to start)
        for _ in range(num_players):
            player_id_to_check = players[current_index].id
            
            # Check if this player still exists in the database
            if PlayerManual.query.get(player_id_to_check):
                # Found the next active player
                state.current_player = current_index
                db.session.commit()
                return jsonify({
                    "current_player": current_index,
                    "message": f"🔄 It is now {players[current_index].name}'s turn."
                }), 200
            
            # Move to the next index
            current_index = (current_index + 1) % num_players
            
            # If we've circled completely, it means something is wrong (should be caught by the count == 1 check)
            if current_index == start_index:
                break
        
        # Fallback if the loop finishes unexpectedly (e.g., player count error)
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
# Pay Rent 🔑 FIXED LOGIC
# -----------------------------
@api.route("/pay-rent", methods=["POST"])
def pay_rent():
    data = request.json
    payer = PlayerManual.query.get(data["player_id"])
    prop = PropertyManual.query.filter_by(position=data["property_position"]).first()

    if not payer or not prop or not prop.owner_id:
        return jsonify({"error": "Invalid rent action: Player/Property/Owner Missing"}), 400

    owner = PlayerManual.query.get(prop.owner_id)
    rent = prop.rent

    if payer.money < rent:
        # 🔑 BANKRUPTCY LOGIC
        remaining, game_over = eliminate_player(payer.id)
        
        # NOTE: The owner still gets the money from the player's remaining assets, 
        # but for simplicity, we skip that complex step here and just pass the flag.
        
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
# Pay Tax (Simplistic) 🔑 FIXED LOGIC
# -----------------------------
@api.route("/pay-tax", methods=["POST"])
def pay_tax():
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
        # 🔑 BANKRUPTCY LOGIC
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
# Go To Jail
# -----------------------------
@api.route("/go-to-jail", methods=["POST"])
def go_to_jail():
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
# Card Endpoints
# -----------------------------
@api.route("/cards", methods=["GET"])
def get_cards():
    cards = Card.query.all()
    return jsonify([c.to_dict() for c in cards])

@api.route("/cards/draw", methods=["POST"])
def draw_card():
    cards = Card.query.all()
    if not cards:
        return jsonify({"error": "No cards available"}), 400

    card = random.choice(cards)
    return jsonify(card.to_dict())


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