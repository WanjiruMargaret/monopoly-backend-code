from flask import Flask
from flask_migrate import Migrate
from models import db  # your Monopoly models
from flask_cors import CORS
from routes import api  # your Blueprint

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///monopoly.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = 'your_super_secret_and_unique_key_here'

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

# Register the Blueprint
app.register_blueprint(api)

# Root route for quick backend check
@app.route("/")
def home():
    return {"message": "Monopoly Backend Running!"}

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # make sure tables exist
    app.run(port=5555, debug=True)
