import requests
from flask import request, jsonify
from shopmate import app,datetime,timedelta
from shopmate.routes.recommend import search_serpapi   # reuse same function
import google.generativeai as genai
import os

CACHE = {}
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

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

@app.route("/get_price", methods=["POST"])
def get_price():
    data = request.get_json() or {}
    product = data.get("product")

    if not product:
        return jsonify({"success": False, "error": "Product name is required"}), 400

    results = search_serpapi(product)

    if not results:
        return jsonify({
            "success": False,
            "error": "No product data found."
        }), 404

    # Keep only meaningful entries
    results = [p for p in results if p.get("price")]

    if not results:
        return jsonify({
            "success": False,
            "error": "No price data available."
        }), 404

    # Top 10 results
    top_products = results[:10]
    return jsonify({
        "success": True,
        "product": product,
        "price_data": top_products,
    }), 200
