# utils/mongo_client.py

from pymongo import MongoClient
from config import MONGO_URI, DATABASE_NAME

def get_mongo_client():
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    return db