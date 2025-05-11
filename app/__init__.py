from flask import Flask
import os

app = Flask(__name__)
app.config.from_pyfile(os.path.join(os.path.dirname(__file__), '..', 'config.py'))

# Must come after app creation
from app import routes
