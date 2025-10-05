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
    players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
    
    if not state or not players or not player_id_attempting_roll:
        return jsonify({"error": "Game not initialized or Player ID missing"}), 400

    try:
        current_turn_player = players[state.current_player]
    except IndexError:
        return jsonify({"error": "Invalid current player index in state"}), 500

    player_attempting_roll = PlayerManual.query.get(player_id_attempting_roll)

    if not player_attempting_roll or current_turn_player.id != player_attempting_roll.id:
        return jsonify({"error": f"❌ It's not {player_attempting_roll.name}'s turn. It's {current_turn_player.name}'s turn."}), 403

    # Use 'current_turn_player' for the action
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2

    # Handle Jail logic (Releasing them only, they don't move here)
    if current_turn_player.in_jail:
        # NOTE: This is a simplified release without checking for doubles/payment
        current_turn_player.in_jail = False
        db.session.commit()
        return jsonify({
            "dice": [d1, d2],
            "player": current_turn_player.to_dict(),
            "message": f"🗃️ {current_turn_player.name} paid fine/rolled out of jail and skips movement this turn.",
            "action_needed": "NONE"
        })

    # Save old position for Go check
    old_position = current_turn_player.position
    
    # Move player
    current_turn_player.position = (current_turn_player.position + steps) % 40

    # Handle Passing Go ($200 logic)
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
        # 'rolled_doubles' is false for now, assuming simple turn structure
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
        
        # Tile data for the frontend modal context
        tile_data = {"position": position, "name": name, "type": tile_info["type"]}
        message = f"{player.name} landed on {name}."
        
        if tile_info["type"] == "community_chest":
            action_needed = "COMMUNITY_CHEST"
        elif tile_info["type"] == "chance":
            action_needed = "CHANCE"
        elif tile_info["type"] == "tax": 
            # Tax is handled automatically by GameContext after the rollDice call
            action_needed = "TAX"
            # NOTE: For simplicity, the actual money deduction is often done in a separate endpoint
            message += " Must pay tax."
        elif position == 30: # Go To Jail (position 30)
            action_needed = "GO_TO_JAIL"
            message += " 🚨 GO TO JAIL! Moving to position 10."
            
        # Passive tiles like GO, Free Parking, Jail (Just Visiting) resolve to NONE, ending the turn automatically.
        
    return jsonify({
        "player": player.to_dict(),
        "tile": tile_data,
        "action_needed": action_needed,
        "message": message
    })


# ----------------------------------------------------
# Next Turn
# ----------------------------------------------------
@api.route("/next_turn", methods=["POST"])
def next_turn():
    try:
        state = GameStateManual.query.first()
        players = PlayerManual.query.order_by(PlayerManual.id.asc()).all()
        
        if not state or not players:
            return jsonify({"error": "Game not initialized"}), 400

        # Determine next player index (wrap around)
        next_index = (state.current_player + 1) % len(players)
        
        # Update the current player index
        state.current_player = next_index
        db.session.commit()
        
        next_player = players[next_index]
        return jsonify({
            "current_player": next_index,
            "message": f"🔄 It is now {next_player.name}'s turn."
        }), 200

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
    
    # Look up the property by its position
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
# Pay Rent
# -----------------------------
@api.route("/pay-rent", methods=["POST"])
def pay_rent():
    data = request.json
    player = PlayerManual.query.get(data["player_id"])
    
    # Look up by position
    prop = PropertyManual.query.filter_by(position=data["property_position"]).first()

    if not player or not prop or not prop.owner_id:
        return jsonify({"error": "Invalid rent action: Player/Property/Owner Missing"}), 400

    owner = PlayerManual.query.get(prop.owner_id)
    rent = prop.rent

    player.money -= rent
    owner.money += rent
    db.session.commit()

    return jsonify({
        "message": f"💸 {player.name} paid ${rent} rent to {owner.name}.",
        "payer": player.to_dict(),
        "owner": owner.to_dict(),
        "property": prop.to_dict()
    })


# Add these two new endpoints to your routes.py file

# -----------------------------
# Pay Tax (Simplistic)
# -----------------------------
@api.route("/pay-tax", methods=["POST"])
def pay_tax():
    data = request.json
    player = PlayerManual.query.get(data["player_id"])
    tax_position = data["tax_position"]
    
    # Simple check for Income Tax (4) or Luxury Tax (38)
    tax_amount = 200 if tax_position == 4 else 100 

    if not player:
        return jsonify({"error": "Player not found"}), 404

    if player.money < tax_amount:
        # NOTE: Real Monopoly forces bankruptcy, but here we'll just fail for now.
        return jsonify({"error": "Not enough money to pay tax"}), 400

    player.money -= tax_amount
    db.session.commit()

    return jsonify({
        "message": f"💸 {player.name} paid ${tax_amount} tax!",
        "player": player.to_dict()
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
    
    # Move player to Jail tile (Position 10) and set jail status
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