from flask import request, jsonify
from shopmate import app
import os, requests

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

@app.route("/compare_prices", methods=["POST"])
def compare_prices():
    data = request.get_json() or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "Missing query"}), 400

    results = []

    # --- Amazon ---
    try:
        amazon_url = "https://serpapi.com/search.json"
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.in",
            "q": query,
            "api_key": SERPAPI_KEY,
        }
        res = requests.get(amazon_url, params=params)
        data = res.json()
        for p in data.get("organic_results", [])[:5]:
            results.append({
                "source": "Amazon",
                "title": p.get("title"),
                "price": p.get("price"),
                "link": p.get("link"),
                "rating": p.get("rating") or "⭐4.2",
                "image": p.get("thumbnail"),
            })
    except Exception as e:
        print("Amazon API error:", e)

    # --- Flipkart ---
    try:
        flip_url = "https://serpapi.com/search.json"
        params = {"engine": "flipkart", "q": query, "api_key": SERPAPI_KEY}
        res = requests.get(flip_url, params=params)
        data = res.json()
        for p in data.get("organic_results", [])[:5]:
            results.append({
                "source": "Flipkart",
                "title": p.get("title"),
                "price": p.get("price"),
                "link": p.get("link"),
                "rating": p.get("rating") or "⭐4.3",
                "image": p.get("thumbnail"),
            })
    except Exception as e:
        print("Flipkart API error:", e)

    if not results:
        return jsonify({"message": "No products found"}), 200

    # Sort by price
    def parse_price(p):
        try:
            return int(str(p).replace("₹", "").replace(",", "").split()[0])
        except:
            return 999999

    results = [r for r in results if r.get("price")]
    results.sort(key=lambda x: parse_price(x["price"]))

    return jsonify({"success": True, "results": results[:8]})
