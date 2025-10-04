from flask import Flask
from flask_migrate import Migrate
from models import db,Player, Property, Card, GameState # your Monopoly models
from game_logic import roll_dice_logic, buy_property_logic, apply_card_logic
from flask_cors import CORS


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///monopoly.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

@app.route("/")
def home():
    return {"message": "Monopoly Backend Running!"}

@app.route("/players", methods=["GET"])
def get_players():
    players = Player.query.all()
    return jsonify([p.to_dict() for p in players])

@app.route("/roll-dice", methods=["POST"])
def roll_dice():
    data = request.get_json()
    return jsonify(roll_dice_logic(data["player_id"]))

@app.route("/buy-property", methods=["POST"])
def buy_property():
    data = request.get_json()
    return jsonify(buy_property_logic(data["player_id"], data["property_id"]))

@app.route("/apply-card", methods=["POST"])
def apply_card():
    data = request.get_json()
    return jsonify(apply_card_logic(data["player_id"], data["card_id"]))

@app.route("/game-state", methods=["GET"])
def game_state():
    state = GameState.query.first()
    return jsonify(state.to_dict() if state else {})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(port=5555,debug=True)