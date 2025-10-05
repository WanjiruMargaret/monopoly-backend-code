from app import app, db
# Import BOTH versions
from models import Player, Property, ChestCard, GameState
from models import PlayerManual,Card, PropertyManual, GameStateManual

with app.app_context():
    db.drop_all()
    db.create_all()

    # --- Option 1: Use Yuffis' SerializerMixin models ---
    p1 = Player(name="Player 1")
    p2 = Player(name="Player 2")
    db.session.add_all([p1, p2])

    # NOTE: These properties also need the 'position' column added 
    # if you update the base Property model similarly.
    board_props = [
        Property(name="Mediterranean Avenue", price=60, rent=2, color_set="Brown"),
        Property(name="Baltic Avenue", price=60, rent=4, color_set="Brown"),
        Property(name="Boardwalk", price=400, rent=50, color_set="Dark Blue"),
    ]
    db.session.add_all(board_props)

    chance = ChestCard(type="chance", effect="Collect $50")
    community = ChestCard(type="community", effect="Pay $50")
    db.session.add_all([chance, community])

    game_state = GameState(current_player_id=1, turn_number=1)
    db.session.add(game_state)

    # --- Option 2: Use your Manual to_dict() models ---
    p3 = PlayerManual(name="Player 3")
    p4 = PlayerManual(name="Player 4")
    db.session.add_all([p3, p4])

    # 🔑 FIX APPLIED HERE: Added the 'position' argument for each property.
    board_props_manual = [
        PropertyManual(position=37, name="Park Place", price=350, rent=35), # Park Place is at board index 37
        PropertyManual(position=24, name="Illinois Avenue", price=240, rent=20), # Illinois Avenue is at board index 24
    ]
    db.session.add_all(board_props_manual)

    card1 = Card(type="chance", text="Advance to Go", effect="move_start")
    card2 = Card(type="community", text="Doctor's fee, pay $50", effect="pay")
    db.session.add_all([card1, card2])

    game_state_manual = GameStateManual(current_player=0, turn_number=1)
    db.session.add(game_state_manual)

    # Commit everything
    db.session.commit()
    print("✅ Database seeded with both model versions!")
