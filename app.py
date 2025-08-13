import os
from flask import Flask, render_template
from flask_login import LoginManager
from os import environ

login_manager = LoginManager()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static")
        )
app.secret_key = 'rahasia-super-aman'
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')

login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import & daftar blueprint
from routes.auth_routes import auth_bp, load_user
from routes.upload_routes import upload_bp
from routes.view_hm_routes import hm_bp
from routes.view_absen_routes import absen_bp
from routes.view_hauling_routes import hauling_bp
from routes.view_rom_routes import rom_bp
from routes.view_mor_routes import mor_bp
from routes.main_routes import main_bp
from routes.revisi_routes import revisi_bp
from routes.admin_user_routes import admin_user_bp

login_manager.user_loader(load_user)

# Daftar blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(hm_bp)
app.register_blueprint(absen_bp)
app.register_blueprint(hauling_bp)
app.register_blueprint(rom_bp)
app.register_blueprint(mor_bp)
app.register_blueprint(main_bp)
app.register_blueprint(revisi_bp)
app.register_blueprint(admin_user_bp)

@app.route('/')
def index():
    return "Flask on IIS is running!"

if __name__=='__main__':
    #app.run(debug=True)
    HOST = environ.get('SERVER_HOST', '0.0.0.0')  # default: bisa diakses dari jaringan lokal
    PORT = int(environ.get('SERVER_PORT', '5000'))  # default: port 5000

    print("== ROUTE TERDAFTAR ==")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:30s} -> {rule}")

    print(f"\nAplikasi berjalan di: http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
    