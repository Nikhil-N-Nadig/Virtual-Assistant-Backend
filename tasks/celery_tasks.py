from celery import Celery
from config import REDIS_URL
import requests
from models import PriceAlerts, Users
from services.product_search import search_products

celery = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)

@celery.task
def check_price_alert(alert_id):
    alert = PriceAlerts.find_one({"_id": alert_id})
    if not alert: return
    # find product current price (basic search by title)
    results = search_products(alert['product_query'])
    if not results: return
    best = min(results, key=lambda p: float(p.get("price", 1e9)))
    if float(best.get("price", 1e9)) <= float(alert['target_price']):
        user = Users.find_one({"_id": alert['user_id']})
        # TODO: send email or push notification
        PriceAlerts.update_one({"_id": alert_id}, {"$set":{"triggered": True, "notified_at": None}})
