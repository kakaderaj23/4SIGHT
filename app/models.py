from flask_login import UserMixin
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

client = MongoClient(os.getenv("MONGO_URI"))
auth_db = client["AuthDB"]  # Auth database

class User(UserMixin):
    def __init__(self, _id, employeeId, userID, userType):
        self.id = str(_id)  # Flask-Login needs string ID
        self.employeeId = employeeId
        self.userID = userID
        self.userType = userType

def load_user(user_id):
    record = auth_db.users.find_one({"_id": ObjectId(user_id)})
    if record:
        return User(record['_id'], record['employeeId'], record['userID'], record['userType'])
    return None
