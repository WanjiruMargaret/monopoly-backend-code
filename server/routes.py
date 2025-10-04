from flask import Blueprint, jsonify, request
from models import db, PlayerManual, PropertyManual, Card, GameStateManual
import random

api = Blueprint("api", __name__)

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

# -----------------------------
# Roll Dice + Move Player
# -----------------------------
@api.route("/roll-dice", methods=["POST"])
def roll_dice():
    state = GameStateManual.query.first()
    players = PlayerManual.query.all()
    if not state or not players:
        return jsonify({"error": "Game not initialized"}), 400

    current_player = players[state.current_player]  # safe, it's an int
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2

    if current_player.in_jail:
        current_player.in_jail = False
        db.session.commit()
        state.current_player = (state.current_player + 1) % len(players)
        db.session.commit()
        return jsonify({"message": f"{current_player.name} is in jail and skips this turn."})

    # move player
    current_player.position = (current_player.position + steps) % 40
    db.session.commit()

    # get landed tile
    tile = PropertyManual.query.get(current_player.position)
    result = {
        "dice": [d1, d2],
        "player": current_player.to_dict(),
        "tile": tile.to_dict() if tile else None
    }

    # next turn
    state.current_player = (state.current_player + 1) % len(players)
    state.turn_number += 1
    db.session.commit()

    return jsonify(result)

# -----------------------------
# Buy Property
# -----------------------------
@api.route("/buy-property", methods=["POST"])
def buy_property():
    data = request.json
    player = PlayerManual.query.get(data["player_id"])
    prop = PropertyManual.query.get(data["property_id"])

    if not player or not prop:
        return jsonify({"error": "Invalid player or property"}), 400

    if prop.owner_id:
        return jsonify({"error": "Property already owned"}), 400

    if player.money < prop.price:
        return jsonify({"error": "Not enough money"}), 400

    player.money -= prop.price
    prop.owner_id = player.id
    db.session.commit()

    return jsonify({
        "message": f"{player.name} bought {prop.name} for ${prop.price}",
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
    prop = PropertyManual.query.get(data["property_id"])

    if not player or not prop or not prop.owner_id:
        return jsonify({"error": "Invalid rent action"}), 400

    owner = PlayerManual.query.get(prop.owner_id)
    rent = prop.rent

    player.money -= rent
    owner.money += rent
    db.session.commit()

    return jsonify({
        "message": f"{player.name} paid ${rent} rent to {owner.name}",
        "payer": player.to_dict(),
        "owner": owner.to_dict()
    })

# -----------------------------
# Draw a Card
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
