import random
from server.models import db, Player, Property, GameState, Card

def roll_dice_logic(player_id):
    player = Player.query.get(player_id)
    if not player:
        return {"error": "Player not found"}

    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    steps = d1 + d2

    # Jail skip
    if player.in_jail:
        player.in_jail = False
        db.session.commit()
        return {"message": f"{player.name} is in jail and skips this turn."}

    # Move player
    player.position = (player.position + steps) % 40
    db.session.commit()

    message = f"{player.name} rolled {d1} + {d2} = {steps}, moved to tile {player.position}."

    return {
        "dice": [d1, d2],
        "players": [p.to_dict() for p in Player.query.all()],
        "message": message,
        "next_player": (player.id % Player.query.count())
    }

def buy_property_logic(player_id, property_id):
    player = Player.query.get(player_id)
    prop = Property.query.get(property_id)

    if not player or not prop:
        return {"error": "Player or Property not found"}

    if prop.owner_id:
        return {"message": "Property already owned"}

    if player.money < prop.price:
        return {"message": "Not enough money"}

    player.money -= prop.price
    prop.owner_id = player.id
    db.session.commit()

    return {
        "message": f"{player.name} bought {prop.name} for ${prop.price}.",
        "players": [p.to_dict() for p in Player.query.all()]
    }

def apply_card_logic(player_id, card_id):
    player = Player.query.get(player_id)
    card = Card.query.get(card_id)

    if not player or not card:
        return {"error": "Player or Card not found"}

    # Very simple placeholder logic
    if "pay" in card.text.lower():
        player.money -= 50
        msg = f"{player.name} drew card: {card.text} and paid $50."
    elif "collect" in card.text.lower():
        player.money += 50
        msg = f"{player.name} drew card: {card.text} and collected $50."
    else:
        msg = f"{player.name} drew card: {card.text}."

    db.session.commit()

    return {
        "message": msg,
        "players": [p.to_dict() for p in Player.query.all()]
    }
