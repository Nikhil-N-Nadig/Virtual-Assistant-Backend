# shopmate/routes/price.py
import os
import io
import json
import time
import math
import random
import base64
import traceback
from datetime import datetime, timedelta

import requests
from flask import request, jsonify
from shopmate import app  # ensure this is your Flask instance

# ML + plotting
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt
from PIL import Image

# ---------------------------
# Config / Keys / Cache
# ---------------------------
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # optional (not required)
CACHE = {}

# ---------------------------
# Helpers: SerpAPI current price
# ---------------------------
def serpapi_get_current_price(product_name):
    """Try to fetch current price (number) from SerpAPI Google Shopping results."""
    if not SERPAPI_KEY:
        return None

    params = {
        "engine": "google_shopping",
        "q": product_name,
        "api_key": SERPAPI_KEY,
        "gl": "in",
        "num": 5
    }
    try:
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
        d = r.json()
        for item in d.get("shopping_results", []):
            price = item.get("price")
            if price:
                if isinstance(price, (int, float)):
                    return float(price)
                if isinstance(price, str):
                    s = price.replace("₹", "").replace(",", "").strip()
                    try:
                        return float(s)
                    except:
                        pass
                if isinstance(price, dict):
                    val = price.get("value") or price.get("amount")
                    try:
                        return float(val)
                    except:
                        pass
        return None
    except Exception as e:
        print("SerpAPI price fetch error:", e)
        return None

# ---------------------------
# Helpers: Category detection (simple heuristics)
# ---------------------------
def detect_category(product_name: str) -> str:
    name = (product_name or "").lower()
    if any(k in name for k in ["laptop", "macbook", "dell", "hp", "asus", "lenovo", "notebook", "desktop"]):
        return "laptop"
    if any(k in name for k in ["phone", "mobile", "iphone", "samsung", "xiaomi", "oneplus", "pixel", "realme"]):
        return "mobile"
    if any(k in name for k in ["camera", "dslr", "canon", "nikon", "sony camera"]):
        return "camera"
    if any(k in name for k in ["headphone", "earbuds", "earphones", "speaker", "audio"]):
        return "accessory"
    if any(k in name for k in ["shirt", "jeans", "dress", "tshirt", "trouser", "clothing"]):
        return "clothing"
    return "electronics"

# ---------------------------
# Synthetic history - OPTION C (mixed trend with random shocks)
# ---------------------------
def generate_synthetic_history(current_price: float, category: str, days=60, seed=None):
    """
    Mixed trend with random shocks:
    - Some stable days
    - Some sudden jumps/dips (shocks)
    - Seasonal/weekly patterns depending on category
    - Ensures the latest day approximately matches current_price (if available)
    Returns list of dicts [{"date": ISO, "price": float}, ...] chronological oldest->newest
    """
    if seed is None:
        seed = int(time.time()) % (2**32 - 1)
    rnd = random.Random(seed)

    # Category-driven params (baseline daily volatility, shock probability, seasonal amplitude)
    params = {
        "laptop":    {"vol": 0.03, "shock_p": 0.04, "shock_scale": 0.12, "seasonal": 0.02},
        "mobile":    {"vol": 0.04, "shock_p": 0.07, "shock_scale": 0.18, "seasonal": 0.03},
        "camera":    {"vol": 0.035, "shock_p": 0.05, "shock_scale": 0.12, "seasonal": 0.02},
        "accessory": {"vol": 0.02, "shock_p": 0.03, "shock_scale": 0.08, "seasonal": 0.01},
        "clothing":  {"vol": 0.01, "shock_p": 0.02, "shock_scale": 0.06, "seasonal": 0.015},
        "electronics":{"vol": 0.035, "shock_p": 0.04, "shock_scale":0.12, "seasonal":0.015},
    }
    cfg = params.get(category, params["electronics"])

    # If current price unknown, pick heuristics baseline
    if not current_price or current_price <= 0:
        defaults = {
            "laptop": 60000,
            "mobile": 20000,
            "camera": 35000,
            "accessory": 1500,
            "clothing": 1200,
            "electronics": 8000
        }
        current_price = defaults.get(category, 3000)

    # We'll simulate forward in time (oldest -> newest) to produce realistic shocks
    prices = []
    base = float(current_price)
    # pick a small underlying trend direction randomly (-1,0,1) weighted
    trend_dir = rnd.choices([-1, 0, 1], weights=[0.25, 0.35, 0.4])[0]
    trend_strength = rnd.uniform(0.0005, 0.004) * (1 if trend_dir >= 0 else -1)

    # Start some days before with a baseline around current_price
    # Start value = current_price * (1 + small random offset between -5%..+5%)
    start = base * (1 + rnd.uniform(-0.05, 0.05))
    price = start

    for i in range(days):
        day_of_week = (i % 7)
        # seasonal effect: weekly or monthly depending on category
        seasonal = math.sin(2 * math.pi * i / (7 if category == "mobile" else 30)) * cfg["seasonal"] * rnd.uniform(0.5, 1.2)

        # small day-to-day random move
        daily_move = rnd.uniform(-cfg["vol"], cfg["vol"]) + seasonal + trend_strength

        # sometimes apply a shock (discount or spike)
        shock = 0.0
        if rnd.random() < cfg["shock_p"]:
            # shock direction negative for discounts more often
            shock_dir = rnd.choices([-1, 1], weights=[0.7, 0.3])[0]
            shock = shock_dir * rnd.uniform(cfg["shock_scale"] * 0.5, cfg["shock_scale"]) * (1 if rnd.random() > 0.2 else 0.5)

        # new price
        price = max(0.01, price * (1 + daily_move + shock))

        # small smoothing to avoid unrealistic huge jumps: mix with previous
        if len(prices) >= 2:
            price = 0.6 * price + 0.4 * prices[-1]["price"]

        prices.append({"date": (datetime.utcnow().date() - timedelta(days=days-1-i)).isoformat(), "price": round(price, 2)})

    # Ensure last day roughly matches current price: scale factor
    if len(prices) >= 1 and current_price:
        last_price = prices[-1]["price"]
        if last_price <= 0:
            last_price = current_price
        scale = (current_price / last_price) if last_price > 0 else 1.0
        # Apply gentle scaling to whole series (not to lose relative fluctuations)
        for item in prices:
            item["price"] = round(max(0.01, item["price"] * scale), 2)

    return prices

def train_rf_and_predict(history, future_days=60, seed=None):
    """
    history: list of {date, price} chronological oldest->newest
    returns model, predictions list of {date, predicted_price}
    Adds small randomized uncertainty to predictions so they are not identical.
    """
    if seed is None:
        seed = int(time.time()) % (2**32 - 1)
    rnd = random.Random(seed)

    # DataFrame
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])
    df["day_idx"] = (df["date"] - df["date"].min()).dt.days
    X = df[["day_idx"]].to_numpy()
    y = df["price"].to_numpy()

    # Fit RandomForest with modest size for speed
    model = RandomForestRegressor(n_estimators=150, random_state=42)
    model.fit(X, y)

    last_idx = int(df["day_idx"].max())
    future_idx = np.arange(last_idx + 1, last_idx + 1 + future_days).reshape(-1, 1)
    preds = model.predict(future_idx)

    # Add controlled jitter to produce uncertainty & fluctuation
    jitter_scale = max(0.01, np.std(y) * 0.02)
    predictions = []
    for i, p in enumerate(preds):
        jitter = rnd.uniform(-jitter_scale, jitter_scale)
        predicted = max(0.01, float(p + jitter))
        date = (df["date"].max().date() + timedelta(days=i+1)).isoformat()
        predictions.append({"date": date, "predicted_price": round(predicted, 2)})

    return model, predictions

def create_price_chart_svg(history, predictions=None, title="Price Trend"):
    """
    history: list of {"date","price"} chronological
    predictions: list of {"date","predicted_price"} chronological
    returns svg_base64, png_base64, thumb_base64
    """
    hist_dates = [datetime.fromisoformat(d["date"]) for d in history]
    hist_prices = [d["price"] for d in history]

    plt.figure(figsize=(8, 3.6))
    plt.plot(hist_dates, hist_prices, label="Historical", linewidth=2)

    if predictions:
        pred_dates = [datetime.fromisoformat(p["date"]) for p in predictions]
        pred_prices = [p["predicted_price"] for p in predictions]
        plt.plot(pred_dates, pred_prices, label="Predicted", linestyle="--", linewidth=2)

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.grid(alpha=0.2)
    plt.legend()
    plt.tight_layout()

    # Save SVG
    svg_buffer = io.BytesIO()
    plt.savefig(svg_buffer, format="svg")
    svg_data = svg_buffer.getvalue()
    svg_base64 = base64.b64encode(svg_data).decode("utf-8")

    # Save PNG
    png_buffer = io.BytesIO()
    plt.savefig(png_buffer, format="png", dpi=150)
    png_data = png_buffer.getvalue()
    png_base64 = base64.b64encode(png_data).decode("utf-8")

    # Create thumbnail from PNG
    try:
        img = Image.open(io.BytesIO(png_data))
        img.thumbnail((480, 240))
        thumb_buf = io.BytesIO()
        img.save(thumb_buf, format="PNG")
        thumb_b64 = base64.b64encode(thumb_buf.getvalue()).decode("utf-8")
    except Exception:
        thumb_b64 = ""

    plt.close()
    return svg_base64, png_base64, thumb_b64

# ---------------------------
# Internal helper price_history (non-Flask wrapper)
# ---------------------------
def price_history_route_inner(product, category=None, use_serpapi=True):
    try:
        if not product:
            return {"success": False, "error": "product required"}

        category = category or detect_category(product)
        cache_key = f"hist::{product.lower()}::{category}"
        now = time.time()
        if cache_key in CACHE and CACHE[cache_key]["expires"] > now:
            return {"success": True, **CACHE[cache_key]["data"]}

        # Try to fetch current price (best-effort)
        current_price = None
        if use_serpapi and SERPAPI_KEY:
            try:
                current_price = serpapi_get_current_price(product)
            except Exception:
                current_price = None

        # Generate synthetic mixed-trend history (OPTION C)
        history = generate_synthetic_history(current_price, category, days=60)

        svg_b64, png_b64, thumb_b64 = create_price_chart_svg(history, title=f"{product} — last 60 days")

        result = {
            "product": product,
            "category": category,
            "history": history,
            "svg_base64": svg_b64,
            "png_base64": png_b64,
            "thumb_base64": thumb_b64
        }

        # cache for 10 minutes
        CACHE[cache_key] = {"data": result, "expires": now + 600}
        return {"success": True, **result}
    except Exception as e:
        print("price_history inner failed:", e)
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ---------------------------
# Route: /price_history
# ---------------------------
@app.route("/price_history", methods=["POST"])
def price_history_route():
    """
    POST body:
      { "product": "Samsung Galaxy Foo", "category": (optional), "use_serpapi": true/false (default true) }
    Response JSON:
      {
        success: True,
        product: "...",
        category: "...",
        history: [{date, price}, ...],
        svg_base64, png_base64, thumb_base64
      }
    """
    data = request.get_json() or {}
    product = data.get("product")
    if not product:
        return jsonify({"success": False, "error": "product required"}), 400

    category = data.get("category") or detect_category(product)
    use_serpapi = data.get("use_serpapi", True)

    resp = price_history_route_inner(product, category, use_serpapi)
    if not resp.get("success"):
        return jsonify({"success": False, "error": resp.get("error", "failed to generate history")}), 500

    return jsonify({"success": True, **resp}), 200

# ---------------------------
# Route: /predict_future_price
# ---------------------------
@app.route("/predict_future_price", methods=["POST"])
def predict_future_price_route():
    """
    POST body:
      { "product": "...", "asin": "...", "future_days": 60, "category": (optional), "use_serpapi": true/false }
    Response JSON:
      {
        success: True,
        product: "...",
        category: "...",
        history: [...],
        predictions: [{date, predicted_price}, ...],
        model_info: {...},
        svg_base64, png_base64, thumb_base64
      }
    """
    data = request.get_json() or {}
    product = data.get("product")
    asin = data.get("asin")
    future_days = int(data.get("future_days", 60))
    if future_days <= 0:
        return jsonify({"success": False, "error": "future_days must be > 0"}), 400

    product_name = product or asin
    if not product_name:
        return jsonify({"success": False, "error": "product or asin required"}), 400

    category = data.get("category") or detect_category(product_name)
    use_serpapi = data.get("use_serpapi", True)

    # Generate or fetch history via inner helper
    hist_resp = price_history_route_inner(product_name, category, use_serpapi)
    if not hist_resp.get("success"):
        return jsonify({"success": False, "error": "could not generate history"}), 500

    history = hist_resp["history"]

    # Train model & predict
    try:
        model, predictions = train_rf_and_predict(history, future_days=future_days)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": "model training failed"}), 500

    # Create chart with both history + predictions
    svg_b64, png_b64, thumb_b64 = create_price_chart_svg(history, predictions=predictions, title=f"{product_name} — history + {future_days}d forecast")

    model_info = {
        "model": "RandomForestRegressor",
        "n_estimators": getattr(model, "n_estimators", None),
        "trained_on_days": len(history)
    }

    # Optional lightweight analysis (simple summary) — avoid heavy LLM calls here
    # Quick human-friendly summary generated programmatically:
    try:
        hist_prices = [p["price"] for p in history]
        avg_hist = float(np.mean(hist_prices))
        last_price = float(history[-1]["price"])
        avg_pred = float(np.mean([p["predicted_price"] for p in predictions])) if predictions else None

        # trend quick description
        if avg_pred and avg_pred > last_price * 1.02:
            quick_trend = "predicted to rise moderately"
        elif avg_pred and avg_pred < last_price * 0.98:
            quick_trend = "predicted to fall moderately"
        else:
            quick_trend = "predicted to remain roughly stable"

        llm_summary = f"Quick analysis: the last observed price is ₹{last_price:.2f}. Over the historical window the average was ₹{avg_hist:.2f}. The forecast for the next {future_days} days is {quick_trend}."
    except Exception:
        llm_summary = ""

    return jsonify({
        "success": True,
        "product": product_name,
        "category": category,
        "history": history,
        "predictions": predictions,
        "model_info": model_info,
        "svg_base64": svg_b64,
        "png_base64": png_b64,
        "thumb_base64": thumb_b64,
        "llm_summary": llm_summary
    }), 200
