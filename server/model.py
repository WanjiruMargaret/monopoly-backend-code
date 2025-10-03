from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin

db = SQLAlchemy()


class Player(db.Model, SerializerMixin):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)  # number of the player (1, 2, 3)
    name = db.Column(db.String(50), nullable=False)  # name of the player
    position = db.Column(db.Integer, default=0)  # start from 0
    money = db.Column(db.Integer, default=1500)  # start with 1500 as the money
    in_jail = db.Column(db.Boolean, default=False)  # if the person is in jail or not

    # one player -> many properties
    properties = db.relationship("Property", back_populates="owner")

    serialize_rules = ('-properties.owner',)



class Property(db.Model, SerializerMixin):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    rent = db.Column(db.Integer, nullable=False)

    color_set = db.Column(db.String(50), nullable=False, default='Other')  # Brown, Railroad, Utility, etc.
    houses = db.Column(db.Integer, default=0)  # 0–4 houses, 5 = hotel
    is_mortgaged = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('players.id'))  # foreign key -> Player
    owner = db.relationship("Player", back_populates="properties")

    serialize_rules = ('-owner.properties',)



class ChestCard(db.Model, SerializerMixin):
    __tablename__ = 'cards'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False)  # "chance" or "community"
    effect = db.Column(db.String, nullable=False)  # description of effect


class GameProgram(db.Model, SerializerMixin):
    __tablename__ = 'game_states'

    id = db.Column(db.Integer, primary_key=True)
    current_player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    turn_number = db.Column(db.Integer, default=1)

    # relationship to know who is the current player
    current_player = db.relationship("Player")
