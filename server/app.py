from flask import Flask
from flask_migrate import Migrate
from server.models import db, bcrypt # Import bcrypt to initialize it!
from flask_cors import CORS
from routes import api 

app = Flask(__name__)

# ######################################
# 🔑 FIX: CONFIGURATION GOES FIRST
# ######################################
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///monopoly.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = 'your_super_secret_and_unique_key_here' 
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

# ######################################
# 🔑 INITIALIZE EXTENSIONS
# ######################################
db.init_app(app) # Now the URI is available
migrate = Migrate(app, db)
bcrypt.init_app(app) # Don't forget this critical fix from our last conversation!

# ######################################
# CORS CONFIGURATION
# ######################################
from datetime import timedelta
CORS(app, 
    supports_credentials=True, 
    origins="*", # Allow all origins for testing
    allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
    resources={r"/*": {"origins": "*"}},
    expose_headers=["Content-Type", "Authorization"],
    max_age=timedelta(hours=1)
)

# Register the Blueprint
app.register_blueprint(api, url_prefix='/api')

# Root route for quick backend check
@app.route("/")
def home():
    return {"message": "Monopoly Backend Running!"}

if __name__ == "__main__":
    with app.app_context():
        # This is where db.create_all should live
        db.create_all() 
    # Run the application
    app.run(host='localhost', port=5555, debug=True) # Added host='localhost' for CORS compatibility
