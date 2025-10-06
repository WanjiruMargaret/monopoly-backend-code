from app import app, db
# Import all models needed for both versions (Manual is the one you are using)
from models import Player, Property, ChestCard, GameState
from models import PlayerManual, Card, PropertyManual, GameStateManual

with app.app_context():
    db.drop_all()
    db.create_all()

    # --- Option 1: Basic Seeding (for the legacy model, if you still use it) ---
    p1 = Player(name="Player 1")
    p2 = Player(name="Player 2")
    db.session.add_all([p1, p2])

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

    # -------------------------------------------------------------
    # --- Option 2: Full Seeding for the PropertyManual model ---
    # -------------------------------------------------------------
    
    p3 = PlayerManual(name="Player 3")
    p4 = PlayerManual(name="Player 4")
    db.session.add_all([p3, p4])

    # 🔑 CRITICAL FIX: ALL 28 PURCHASABLE PROPERTIES ADDED HERE
    board_props_manual = [
        # BROWN (1, 3)
        PropertyManual(position=1, name="Mediterranean Avenue", price=60, rent=2),
        PropertyManual(position=3, name="Baltic Avenue", price=60, rent=4),
        
        # LIGHT BLUE (6, 8, 9)
        PropertyManual(position=6, name="Oriental Avenue", price=100, rent=6),
        PropertyManual(position=8, name="Vermont Avenue", price=100, rent=6),
        PropertyManual(position=9, name="Connecticut Avenue", price=120, rent=8),
        
        # RAILROADS (5, 15, 25, 35) - Rent is dynamic but price is static
        PropertyManual(position=5, name="Reading Railroad", price=200, rent=25),
        PropertyManual(position=15, name="Pennsylvania Railroad", price=200, rent=25),
        PropertyManual(position=25, name="B. & O. Railroad", price=200, rent=25),
        PropertyManual(position=35, name="Short Line", price=200, rent=25),
        
        # UTILITIES (12, 28) - Rent is dynamic (4x/10x roll) but price is static
        PropertyManual(position=12, name="Electric Company", price=150, rent=10), 
        PropertyManual(position=28, name="Water Works", price=150, rent=10),
        
        # PINK (11, 13, 14)
        PropertyManual(position=11, name="St. Charles Place", price=140, rent=10),
        PropertyManual(position=13, name="States Avenue", price=140, rent=10),
        PropertyManual(position=14, name="Virginia Avenue", price=160, rent=12),
        
        # ORANGE (16, 18, 19)
        PropertyManual(position=16, name="St. James Place", price=180, rent=14),
        PropertyManual(position=18, name="Tennessee Avenue", price=180, rent=14),
        PropertyManual(position=19, name="New York Avenue", price=200, rent=16),
        
        # RED (21, 23, 24)
        PropertyManual(position=21, name="Kentucky Avenue", price=220, rent=18),
        PropertyManual(position=23, name="Indiana Avenue", price=220, rent=18),
        PropertyManual(position=24, name="Illinois Avenue", price=240, rent=20),
        
        # YELLOW (26, 27, 29)
        PropertyManual(position=26, name="Atlantic Avenue", price=260, rent=22),
        PropertyManual(position=27, name="Ventnor Avenue", price=260, rent=22),
        PropertyManual(position=29, name="Marvin Gardens", price=280, rent=24),
        
        # GREEN (31, 32, 34)
        PropertyManual(position=31, name="Pacific Avenue", price=300, rent=26),
        PropertyManual(position=32, name="North Carolina Avenue", price=300, rent=26),
        PropertyManual(position=34, name="Pennsylvania Avenue", price=320, rent=28),

        # DARK BLUE (37, 39)
        PropertyManual(position=37, name="Park Place", price=350, rent=35),
        PropertyManual(position=39, name="Boardwalk", price=400, rent=50),
    ]
    db.session.add_all(board_props_manual)

    card1 = Card(type="chance", text="Advance to Go", effect="move_start")
    card2 = Card(type="community", text="Doctor's fee, pay $50", effect="pay")
    db.session.add_all([card1, card2])

    game_state_manual = GameStateManual(current_player=0, turn_number=1)
    db.session.add(game_state_manual)

    # Commit everything
    db.session.commit()
    print("✅ Database seeded with both model versions and ALL Monopoly properties!")