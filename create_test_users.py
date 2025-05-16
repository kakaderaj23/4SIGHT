from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

# Load MONGO_URI from .env
load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# Connect to AuthDB
client = MongoClient(mongo_uri)
auth_db = client["AuthDB"]

# Define users
users = [
    {
        "employeeId": "EMP001",
        "userID": "Adwyte",
        "password": "man123",
        "userType": "manager"
    },
    {
        "employeeId": "EMP002",
        "userID": "Vikram",
        "password": "man123",
        "userType": "manager"
    },
    {
        "employeeId": "EMP003",
        "userID": "Prajwal",
        "password": "op123",
        "userType": "operator"
    },
    {
        "employeeId": "EMP004",
        "userID": "Raj",
        "password": "op123",
        "userType": "operator"
    },
    {
        "employeeId": "EMP005",
        "userID": "Atharva",
        "password": "op123",
        "userType": "operator"
    }
]

# Insert users
for u in users:
    existing = auth_db.users.find_one({"userID": u["userID"]})
    if existing:
        # Update userType and password if changed
        auth_db.users.update_one(
            {"userID": u["userID"]},
            {
                "$set": {
                    "userType": u["userType"],
                    "passwordHash": generate_password_hash(u["password"]),
                    "employeeId": u["employeeId"]
                }
            }
        )
        print(f"User {u['userID']} already existed — updated info.")
    else:
        auth_db.users.insert_one({
            "employeeId": u["employeeId"],
            "userID": u["userID"],
            "passwordHash": generate_password_hash(u["password"]),
            "userType": u["userType"],
            "lastLogin": None
        })
        print(f"User {u['userID']} created successfully.")

