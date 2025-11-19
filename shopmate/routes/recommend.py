import requests
from datetime import datetime, timedelta
from flask import request, jsonify
from shopmate import app, db, os
from shopmate.models import UserPreference

# ---------------------------------------------------------------------
# 🔑 API Keys
# ---------------------------------------------------------------------
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# ---------------------------------------------------------------------
# 🧠 Simple in-memory cache (1 hour)
# ---------------------------------------------------------------------
CACHE = {}


# ---------------------------------------------------------------------
# 🔍 Use ONLY SerpAPI (Google Shopping)
# ---------------------------------------------------------------------
def search_serpapi(query):
    """Fetch product results using SerpAPI only."""
    
    # Cache check
    if query in CACHE and CACHE[query]["expires"] > datetime.now():
        return CACHE[query]["data"]

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_KEY,
        "gl": "in"
    }

    try:
        res = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
        data = res.json()

        products = []
        for item in data.get("shopping_results", []):
            products.append({
                "title": item.get("title"),
                "price": item.get("price"),
                "link": item.get("product_link"),
                "thumbnail": item.get("thumbnail"),
                "source": item.get("source"),     # Example: Google, Amazon, Flipkart
                "rating": item.get("rating"),
                "reviews": item.get("reviews")
            })

        # Cache for 1 hour
        CACHE[query] = {
            "data": products,
            "expires": datetime.now() + timedelta(hours=1)
        }

        return products

    except Exception as e:
        print("⚠️ SerpAPI error:", e)
        return []


# ---------------------------------------------------------------------
# 🎯 Recommendation Route (ONLY SerpAPI)
# ---------------------------------------------------------------------
@app.route("/recommend", methods=["POST"])
def recommend_products():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    query = data.get("query", "").lower()

    if not user_id or not query:
        return jsonify({"error": "Missing user_id or query"}), 400

    # Save user preference
    pref = UserPreference(
        user_id=user_id,
        category="general",
        keyword=query
    )
    db.session.add(pref)
    db.session.commit()

    # Fetch products using SerpAPI only
    products = search_serpapi(query)

    return jsonify({
        "success": True,
        "query": query,
        "recommendations": products[:10]   # return top 10 clean results
    }), 200
