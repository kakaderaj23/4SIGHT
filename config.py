import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
SENSOR_INTERVAL = 5
SIMULATION_TIMEOUT = 300
