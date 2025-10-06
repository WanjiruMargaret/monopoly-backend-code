from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
# 🔑 NEW IMPORTS for Authentication
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt() # 🔑 Initialize Bcrypt here or in your app's main file

# ==============================
# YUFFIS CODE (unchanged)
# ==============================

class Player(db.Model, SerializerMixin):
    __tablename__ = 'players'
    # ... (existing Player model code) ...
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(50), nullable=False) 
    position = db.Column(db.Integer, default=0) 
    money = db.Column(db.Integer, default=1500) 
    in_jail = db.Column(db.Boolean, default=False) 

    properties = db.relationship("Property", back_populates="owner")

    serialize_rules = ('-properties.owner',)


class Property(db.Model, SerializerMixin):
    __tablename__ = 'properties'
    # ... (existing Property model code) ...
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
    # ... (existing ChestCard model code) ...
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False) 
    effect = db.Column(db.String, nullable=False) 


class GameState(db.Model, SerializerMixin):
    __tablename__ = 'game_states'
    # ... (existing GameState model code) ...
    id = db.Column(db.Integer, primary_key=True)
    current_player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    turn_number = db.Column(db.Integer, default=1)

    current_player = db.relationship("Player")


# ==============================
# MY CODE
# ==============================

# 🔑 NEW: User Model for Authentication
class User(db.Model, SerializerMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Stores the HASH
    
    # Optional: Link game records to a user (one-to-many)
    player_manuals = db.relationship('PlayerManual', backref='user', lazy=True)

    def set_password(self, password):
        """Hashes the password and stores the hash."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks the provided password against the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
        }
        
# 🔑 UPDATE: Add foreign key to PlayerManual to link to a User
class PlayerManual(db.Model):
    __tablename__ = 'players_manual'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    position = db.Column(db.Integer, default=0)
    money = db.Column(db.Integer, default=1500)
    in_jail = db.Column(db.Boolean, default=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # 🔑 NEW FOREIGN KEY

    properties = db.relationship("PropertyManual", back_populates="owner")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "money": self.money,
            "in_jail": self.in_jail,
            "user_id": self.user_id, # 🔑 Include user_id
            "properties": [p.to_dict() for p in self.properties]
        }


class PropertyManual(db.Model):
    __tablename__ = 'properties_manual'
    # ... (rest of PropertyManual unchanged) ...
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, unique=True, nullable=False) 
    
    name = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer)
    rent = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey("players_manual.id"))

    owner = db.relationship("PlayerManual", back_populates="properties")

    def to_dict(self):
        return {
            "id": self.id,
            "position": self.position,
            "name": self.name,
            "price": self.price,
            "rent": self.rent,
            "owner_id": self.owner_id, 
        }


class Card(db.Model):
    __tablename__ = 'cards_manual'
    # ... (rest of Card unchanged) ...
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String) 
    text = db.Column(db.String)
    effect = db.Column(db.String) 

    def to_dict(self):
        return {"id": self.id, "type": self.type, "text": self.text}


class GameStateManual(db.Model):
    __tablename__ = 'game_states_manual'
    # ... (rest of GameStateManual unchanged) ...
    id = db.Column(db.Integer, primary_key=True)
    current_player = db.Column(db.Integer, default=0)
    turn_number = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "current_player": self.current_player,
            "turn_number": self.turn_number
        }