from flask import Flask
import os

app = Flask(__name__)
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), '..', 'config.py'))

# Must come after app creation
from app import routes
from flask_login import LoginManager
from app.models import load_user as user_loader_func


login_manager = LoginManager()
login_manager.login_view = 'login'  # redirect unauthorized users here
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return user_loader_func(user_id)

from flask_login import LoginManager
from app.models import load_user as user_loader_func


login_manager = LoginManager()
login_manager.login_view = 'login'  # redirect unauthorized users here
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return user_loader_func(user_id)

