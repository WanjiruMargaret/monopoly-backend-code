from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import serializerMixin

db = SQLALchemy()

class player(db.Model, serializerMixin):
    __tablename__ = 'player'

    id = db.Column(db.Integer, Primary_key=True) ## number of the prayer(1, 2, 3)
    name = db.Column(db.String(50), nullable=False) ## name of the player 
    position = db.Colum(db.Integer, default=0) ## every pakyer should start from zero 
    money = db.Column(db. Integer, default=1500) ## start with 1500 as the money
    in_jail = db.Column(db.Boolean, default= False )##should say if the person is in jail or not 

    properties = db.relationship("property"), back_populates="owner"

    def to_dict(self):
        return{
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "money": self.money,
            "in_jail": self.in_jail,
        }

class property(db.Model, serializerMixin): ## we are creating a table in the database
    __tablename__ = 'properties'

    id = db.Column(db.Integer, Primary_key=True) ## integer is a number
    name = db.Column(db.String(100), nullable=False) ## name of the player 
    price = db.Colum(db.Integer, nullable=False) ## every pakyer should start from zero 
    rent = db.Column(db. Integer, nullable=False)

    owner_id = db.Column(db.Interger, db.ForeignKey('players.id')) ## this is a foreignKeyit points to the player
    owner = db.relationship("player", backref="properties")## this is relationship , connects models 

class user(db.Model, serializerMixin): ## we are creating a table in the database
    __tablename__ = 'user'

    id = db.Column(db.Integer, Primary_key=True) 
    username = db.Column(db.String, unique=True, nullable=False) ## dont repeat the user
    ##bio = db.Colum(db.string)
    ##image_url = db.Column(db.String)
    def to_dict(self):
        return{
            "id": self.id,
            "username": self.username
        }


