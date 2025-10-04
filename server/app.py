
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Player, Property, Card, GameState
from game_logic import roll_dice_logic, buy_property_logic, apply_card_logic

app = Flask(_name_)

from flask import Flask
from flask_migrate import Migrate
from models import db  # your Monopoly models

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///monopoly.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

CORS(app)

@app.route("/")
def home():
    return {"message": "Monopoly Backend Running"}

@app.route("/players", methods=["GET"])
def get_players():
    players = Player.query.all()
    return jsonify([p.to_dict() for p in players])    

migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run(debug=True)

