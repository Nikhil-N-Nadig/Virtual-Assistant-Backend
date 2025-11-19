import requests
from config import SERPAPI_KEY
# Example: use SerpAPI or custom scrapers (be mindful of ToS).
SERP_URL = "https://serpapi.com/search.json"

def search_products(query, intent=None):
    if SERPAPI_KEY:
        params = {
            "engine":"google_shopping",
            "q": query,
            "api_key": SERPAPI_KEY,
            "gl": "in"
        }
        r = requests.get(SERP_URL, params=params)
        data = r.json()
        # map to unified product format
        prods = []
        for item in data.get("shopping_results", []):
            prods.append({
                "title": item.get("title"),
                "price": item.get("price"), 
                "currency": item.get("currency"),
                "link": item.get("link"),
                "source": item.get("source"),
                "thumbnail": item.get("thumbnail"),
                "rating": item.get("rating")
            })
        return prods
    else:
        # fallback: local DB lookup (Products collection)
        from models import Products
        q = {"$text": {"$search": query}} if query else {}
        res = list(Products.find(q).limit(50))
        return res
