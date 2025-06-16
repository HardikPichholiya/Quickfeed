from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
import os

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///quickfeed.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from web.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from web.routes import main
    from web.auth import auth
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    
    # Register SocketIO events
    from web.routes import register_socketio_events
    register_socketio_events(socketio)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app