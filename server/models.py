from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin

db = SQLAlchemy()

# ==============================
# YUFFIS CODE
# ==============================

class Player(db.Model, SerializerMixin):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)  
    name = db.Column(db.String(50), nullable=False)  
    position = db.Column(db.Integer, default=0)  
    money = db.Column(db.Integer, default=1500)  
    in_jail = db.Column(db.Boolean, default=False)  

    properties = db.relationship("Property", back_populates="owner")

    serialize_rules = ('-properties.owner',)


class Property(db.Model, SerializerMixin):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    rent = db.Column(db.Integer, nullable=False)

    color_set = db.Column(db.String(50), nullable=False, default='Other')
    houses = db.Column(db.Integer, default=0)  
    is_mortgaged = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    owner = db.relationship("Player", back_populates="properties")

    serialize_rules = ('-owner.properties',)


class ChestCard(db.Model, SerializerMixin):
    __tablename__ = 'cards'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False)  # "chance" or "community"
    effect = db.Column(db.String, nullable=False)  


class GameState(db.Model, SerializerMixin):
    __tablename__ = 'game_states'

    id = db.Column(db.Integer, primary_key=True)
    current_player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    turn_number = db.Column(db.Integer, default=1)

    current_player = db.relationship("Player")


# ==============================
# MY CODE
# ==============================

class PlayerManual(db.Model):
    __tablename__ = 'players_manual'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    position = db.Column(db.Integer, default=0)
    money = db.Column(db.Integer, default=1500)
    in_jail = db.Column(db.Boolean, default=False)

    properties = db.relationship("PropertyManual", back_populates="owner")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "money": self.money,
            "in_jail": self.in_jail,
            "properties": [p.to_dict() for p in self.properties]
        }


class PropertyManual(db.Model):
    __tablename__ = 'properties_manual'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer)
    rent = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey("players_manual.id"))

    owner = db.relationship("PlayerManual", back_populates="properties")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "rent": self.rent,
            "owner": self.owner_id
        }


class Card(db.Model):
    __tablename__ = 'cards_manual'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String)  
    text = db.Column(db.String)
    effect = db.Column(db.String)  

    def to_dict(self):
        return {"id": self.id, "type": self.type, "text": self.text}


class GameStateManual(db.Model):
    __tablename__ = 'game_states_manual'

    id = db.Column(db.Integer, primary_key=True)
    current_player = db.Column(db.Integer, default=0)
    turn_number = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "current_player": self.current_player,
            "turn_number": self.turn_number
        }
