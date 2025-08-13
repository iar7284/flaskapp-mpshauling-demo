# NewWebApps/__init__.py
from flask import Flask
from flask_login import LoginManager
from routes import upload_routes, user_routes, view_hm_routes, view_absen_routes, view_hauling_routes, view_rom_routes, view_mor_routes

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user.login'

# Register blueprints
app.register_blueprint(user_routes.user_bp)
app.register_blueprint(upload_routes.upload_bp)
app.register_blueprint(view_hm_routes.hm_bp)
app.register_blueprint(view_absen_routes.absen_bp)
app.register_blueprint(view_hauling_routes.hauling_bp)
app.register_blueprint(view_rom_routes.rom_bp)
app.register_blueprint(view_mor_routes.mor_bp)
