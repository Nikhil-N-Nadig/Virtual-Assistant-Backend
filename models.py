from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client.virtualshop

Users = db.users
Products = db.products
PriceAlerts = db.price_alerts
UserEvents = db.user_events  # actions for recommendations
