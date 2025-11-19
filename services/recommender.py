from models import UserEvents, Products
from nlp.embeddings import model
import numpy as np

def recommend_for_user(user_id, k=10):
    # 1) collaborative: find popular products in recent events
    events = list(UserEvents.find({"type":"view"}).sort("ts",-1).limit(500))
    popular = {}
    for e in events:
        pid = e.get("product_id")
        popular[pid] = popular.get(pid,0)+1
    popular_sorted = sorted(popular.items(), key=lambda x:-x[1])[:k]
    recs = []
    for pid,_ in popular_sorted:
        p = Products.find_one({"_id": pid})
        if p:
            recs.append(p)
    # 2) embed-based personal: take last queries and do semantic match
    return recs
