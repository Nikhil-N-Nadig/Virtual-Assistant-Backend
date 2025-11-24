from flask import request, jsonify, Response
from shopmate import app, db, datetime,allowed_url
from shopmate.models import Message, Conversation
from flask_cors import cross_origin

import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import FunctionDeclaration, Schema, Tool
from deep_translator import GoogleTranslator
import requests
import os, time, json, traceback, re

# CONFIG
GEN_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEN_KEY)
MODEL_NAME = "gemini-2.0-flash"
API_URL = "http://localhost:5000"  
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

MEMORY_TURNS = 6
TOOL_RETRY_COUNT = 2
TOOL_RETRY_DELAY = 1.0

# FUNCTION DECLS - note predict accepts asin OR product (future_days required)
recommend_decl = FunctionDeclaration(
    name="recommend_products",
    description="Recommends products based on the products mentioned in the user query.",
    parameters=Schema(
        type_="OBJECT",
        properties={"query": Schema(type_="STRING")},
        required=["query"]
    )
)

reviews_decl = FunctionDeclaration(
    name="analyze_reviews",
    description="Analyzes reviews for a given product.",
    parameters=Schema(
        type_="OBJECT",
        properties={
            "product": Schema(type_="STRING"),
            "language": Schema(type_="STRING")
        },
        required=["product"]
    )
)


get_price_decl = FunctionDeclaration(
    name="get_price",
    description="Fetches prices for a product using SerpAPI Google Shopping.",
    parameters=Schema(
        type_="OBJECT",
        properties={
            "product": Schema(type_="STRING")
        },
        required=["product"]
    )
)

price_history_decl = FunctionDeclaration(
    name="get_price_history",
    description="Returns 60-day synthetic price history and chart for a product.",
    parameters=Schema(
        type_="OBJECT",
        properties={"product": Schema(type_="STRING")},
        required=["product"]
    )
)

forecast_decl = FunctionDeclaration(
    name="predict_future_price",
    description="Predicts future product price using Hybrid ARIMA + RandomForest.",
    parameters=Schema(
        type_="OBJECT",
        properties={
            "product": Schema(type_="STRING"),
            "future_days": Schema(type_="NUMBER")
        },
        required=["product", "future_days"]
    )
)

set_reminder_decl = FunctionDeclaration(
    name="set_reminder",
    description="Creates an email reminder about products the user is viewing.",
    parameters=Schema(
        type_="OBJECT",
        properties={
            "products": Schema(type_="ARRAY", items=Schema(type_="OBJECT")),
            "send_time": Schema(type_="STRING", description="ISO datetime in UTC"),
            "note": Schema(type_="STRING")
        },
        required=[ "send_time"]
    )
)



tools = [Tool(function_declarations=[recommend_decl, reviews_decl,get_price_decl,price_history_decl,forecast_decl,set_reminder_decl])]

print("Initializing Gemini model...")
model = genai.GenerativeModel(model_name=MODEL_NAME, tools=tools)
try:
    model.generate_content("Hello.")  # prewarm
except Exception as e:
    print("Gemini prewarm failed:", e)

def translate_text(text, src, dest):
    try:
        return GoogleTranslator(source=src, target=dest).translate(text)
    except Exception:
        return text

def call_tool_with_retries(tool_fn, *args, **kwargs):
    last_exc = None
    for i in range(TOOL_RETRY_COUNT + 1):
        try:
            return tool_fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            print(f"Tool call failed (attempt {i+1}): {e}")
            time.sleep(TOOL_RETRY_DELAY)
    print("Tool permanently failed:", last_exc)
    return {"success": False, "error": "tool_failed"}

def recommend_products(query):
    payload = {
        "user_id": LAST_USER_ID,  
        "query": query
    }

    res = call_tool_with_retries(
        lambda p: requests.post(f"{API_URL}/recommend", json=p, timeout=30).json(),
        payload
    )

    return res if isinstance(res, dict) else {"success": False}

def get_price_history(product):
    payload = {"product": product}

    res = call_tool_with_retries(
        lambda p: requests.post(
            f"{API_URL}/price_history",
            json=p,
            timeout=60
        ).json(),
        payload
    )

    return res if isinstance(res, dict) else {"success": False}

def predict_future_price(product, future_days=60):
    payload = {
        "product": product,
        "future_days": int(future_days)
    }

    res = call_tool_with_retries(
        lambda p: requests.post(
            f"{API_URL}/predict_future_price",
            json=p,
            timeout=90
        ).json(),
        payload
    )

    return res if isinstance(res, dict) else {"success": False}

def set_reminder(products,send_time=None, note=None):
    from shopmate.models import Conversation, Message
    from shopmate import app, db

    if not LAST_USER_ID:
        return {"success": False, "error": "Missing LAST_USER_ID"}

    if not send_time:
        return {"success": False, "error": "send_time required"}

    try:
        with app.app_context():
            # User's latest conversation
            conv = (
                Conversation.query
                .filter_by(user_id=LAST_USER_ID)
                .order_by(Conversation.updated_at.desc())
                .first()
            )

            if not conv:
                return {"success": False, "error": "No conversation found for user"}

            # Latest messages (limit 20)
            msgs = (
                Message.query
                .filter_by(conversation_id=conv.id)
                .order_by(Message.timestamp.desc())
                .limit(20)
                .all()
            )

            extracted_products = []
            for msg in msgs:
                if msg.products:
                    # msg.products is already stored as JSON → directly use it
                    if isinstance(msg.products, list):
                        extracted_products.extend(msg.products)

            if not extracted_products:
                return {"success": False, "error": "No recent products found to set reminder"}

            # Take top 10 only
            products_to_send = extracted_products[:10]

    except Exception as e:
        return {"success": False, "error": f"DB error: {str(e)}"}

    payload = {
        "user_id": LAST_USER_ID,
        "products": products_to_send,
        "send_time": send_time,
        "note": note
    }

    res = call_tool_with_retries(
        lambda p: requests.post(
            f"{API_URL}/reminder",
            json=p,
            timeout=30
        ).json(),
        payload
    )

    return res if isinstance(res, dict) else {"success": False}

def analyze_reviews(product, language="en"):
    res = call_tool_with_retries(lambda p, l: requests.post(f"{API_URL}/analyze_reviews", json={"product": p, "language": l}, timeout=60).json(), product, language)
    return res if isinstance(res, dict) else {"success": False}


def get_price(product):
    res = call_tool_with_retries(
        lambda p: requests.post(
            f"{API_URL}/get_price",
            json={"product": p},
            timeout=30
        ).json(),
        product
    )
    return res if isinstance(res, dict) else {"success": False}


LOCAL_TOOLS = {
    "recommend_products": recommend_products,
    "analyze_reviews": analyze_reviews,
    "get_price": get_price,
    "get_price_history": get_price_history,
    "predict_future_price": predict_future_price,
    "set_reminder":set_reminder
}

# Memory helper
def get_recent_messages(conversation_id, limit=MEMORY_TURNS):
    msgs = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.id.desc()).limit(limit).all()
    msgs = list(reversed(msgs))
    return [{"role": m.role, "content": m.content} for m in msgs]

# Keywords heuristic
SHOPPING_KEYWORDS = re.compile(
    r"\b(buy|show|recommend|best|price|predict|prediction|future price|next month|next week|laptop|mobile|phone|headphone|camera|compare|deal|discount|offer|review|pros|cons|ratings)\b",
    re.I
)
def should_force_tool(user_text):
    return bool(SHOPPING_KEYWORDS.search(user_text))

# product formatting
def format_products_for_user(products):
    if not products:
        return "I couldn't find product listings right now.", []
    top = products[:5]
    bullets, cards = [], []
    for p in top:
        title = p.get("title") or p.get("name") or "Unnamed"
        price = p.get("price", "N/A")
        rating = p.get("rating", None)
        desc = f"{title} — {price}" + (f" — ⭐ {rating}" if rating else "")
        bullets.append(desc)
        cards.append({
            "title": title,
            "price": price,
            "rating": rating,
            "link": p.get("link"),
            "image": p.get("thumbnail") or p.get("image"),
            "source": p.get("source")
        })
    bullets=bullets[:5]
    summary = "Here are top picks:\n" + "\n".join([f"- {b}" for b in bullets])
    return summary, cards

def format_price_prediction_for_user(tool_result, fargs):
    predictions = tool_result.get("predictions", []) or tool_result.get("predictions", [])
    chart_urls = (tool_result.get("chart_urls") or {})
    if predictions:
        try:
            avg_future = sum([float(p.get("Predicted Price") or p.get("Predicted_Price") or p.get("predicted_price") or 0.0) for p in predictions]) / len(predictions)
        except Exception:
            avg_future = None
    else:
        avg_future = None
    summary_text = f"Predicted average price for next {int(fargs.get('future_days', 0))} days: {avg_future:.2f}" if avg_future else "Prediction generated."
    card = {
        "chart_svg": chart_urls.get("svg_base64"),
        "chart_png": chart_urls.get("png_base64"),
        "chart_thumb": chart_urls.get("thumb_base64"),
        "predictions": predictions
    }
    return summary_text, [card]



def generate_ai_response(user_msg, conversation_id, lang="en"):
    orig_lang = lang
    user_msg_en = translate_text(user_msg, src=lang, dest="en") if lang != "en" else user_msg
    memory = get_recent_messages(conversation_id) if conversation_id else []
    force_tool = should_force_tool(user_msg_en)

    contents = []
    for m in memory:
        contents.append({"role": m["role"], "parts": [{"text": m["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_msg_en}]})

    system_preface = "User requests shopping or price info — prefer calling tools." if force_tool else ""
    try:
        payload = system_preface + "\n" + user_msg_en if system_preface else user_msg_en
        initial = model.generate_content(contents if contents else payload)
    except Exception as e:
        traceback.print_exc()
        return {"response": "⚠ Sorry — AI temporarily unavailable.", "products": []}

    part = initial.candidates[0].content.parts[0]
    if hasattr(part, "function_call") and part.function_call:
        fn = part.function_call
        fname = fn.name
        fargs = fn.args or {}

        # ensure numeric casting
        if fname == "predict_price":
            fargs["future_days"] = int(float(fargs.get("future_days", 30)))

        try:
            tool_result = LOCAL_TOOLS[fname](**fargs) if fname in LOCAL_TOOLS else {"success": False}
        except Exception as e:
            print("Tool execution error:", e)
            return {"response": "⚠ Error running tool.", "products": []}

        result_payload = {
            "response": "",
            "products": [],
            "price_history": None,
            "price_prediction": None,
            "reviews": None
        }

        # format results
        if fname in ("recommend_products"):
            # Extract products
            products_raw = (
                tool_result.get("recommendations")
                or tool_result.get("results")
                or []
            )

            # Take top 5 results
            top_products = products_raw[:5]

            # Format cards for frontend
            summary_text, product_cards = format_products_for_user(top_products)
            result_payload["products"] = product_cards

            # Create a detailed comparison summary for LLM
            llm_comparison_prompt = f"""
            You are an expert shopping assistant.
            Create a professional, concise comparison summary for the user.

            Based ONLY on the tool results below (do NOT invent data),
            compare prices, ratings, and value for money across platforms.

            DO NOT list all products again.
            DO NOT repeat every item.
            DO NOT use bullets.
            DO NOT hallucinate product specs.

            Focus on:
            - which platform offers the lowest price
            - overall value comparison
            - notable differences
            - which option is best and why

            Here are the top product results (max 5):

            {json.dumps(top_products, indent=2)}
            """

            try:
                follow_up = model.generate_content(llm_comparison_prompt)
                summary_text = follow_up.text.strip()
            except Exception:
                print("Calling exception")

            result_payload["response"]=summary_text


        elif fname == "get_price":
            # Extract clean price list
            price_rows = tool_result.get("price_data") or []

            if not price_rows:
                summary_text = "I couldn't find price details for this product."
            else:
                # LLM Friendly Summary
                llm_price_summary_prompt = f"""
                    You are an expert shopping assistant.

                    Your task has TWO parts:

                    PART 1 — SHORT SUMMARY (4–6 lines)
                    - Compare price differences strictly based on the provided price data.
                    - Identify which platform offers the lowest price ("Best Deal").
                    - Comment on overall value and pricing gaps.
                    - Mention if prices seem stable or vary a lot.
                    - Do NOT list products here.
                    - Do NOT invent any missing details.
                    - No bullet points in this section.

                    PART 2 — STRUCTURED PRICE LIST (MANDATORY)
                    After the summary, write a section:

                    "Top Price Listings:"
                    Then list the TOP 5 products in this STRICT format:

                    1. <Product Title> — <Price> — <Source>

                    Rules for PART 2:
                    - Only use the items provided in the price data.
                    - Never fabricate prices, titles, or sources.
                    - If any field is missing, display "Unknown".
                    - Keep list clean and readable.

                    PART 3 — FINAL RECOMMENDATION (1–2 lines)
                    Give a quick suggestion:
                    - Which option is best for most buyers
                    - Who should choose budget vs. balanced option

                    Now use ONLY this data:
                    {json.dumps(price_rows, indent=2)}


                """

                try:
                    llm_resp = model.generate_content(llm_price_summary_prompt)
                    summary_text = (llm_resp.text or "").strip()
                except:
                    summary_text = "Here is a quick overview of price differences across platforms."

                # Format product cards cleanly (no links, no thumbnails)
            result_payload["response"]=summary_text


        elif fname == "analyze_reviews":
            # Raw backend summary from API
            backend_summary = tool_result.get("response") or "Here are review insights."

            review_data = tool_result.get("reviews") or {}
            counts = tool_result.get("counts", {})

            llm_summary_prompt = f"""
            You are an expert shopping assistant.

            Create a SHORT AND SWEET summary (3–5 lines max)
            describing the overall customer opinion about the product.

            STRICT RULES:
            - DO NOT repeat individual review lines.
            - DO NOT fabricate specs or fake details.
            - Use the reviews to generate a summary
            - Focus on clarity, quality, value, satisfaction, and concerns.
            - Sound confident and helpful.
            - No bullet points.

            {backend_summary}
            """

            try:
                llm_resp = model.generate_content(llm_summary_prompt)
                llm_summary = (llm_resp.text or "").strip()
            except:
                llm_summary = "Overall, customers shared a mixed experience based on the sentiment distribution."

            result_payload["response"] = backend_summary + "\n\n" + llm_summary
        
        elif fname == "get_price_history":
            # Extract synthetic history
            history_rows = tool_result.get("history") or []
            chart_svg = tool_result.get("svg_base64")
            chart_thumb = tool_result.get("thumb_base64")
            chart_png = tool_result.get("png_base64")
            category = tool_result.get("category")
            product_name = tool_result.get("product")

            if not history_rows:
                result_payload["response"] = "I couldn’t generate price history for this product."
            else:
                # LLM summary prompt
                llm_history_prompt = f"""
                You are an expert pricing analyst.

                Provide an overview of the price history trend
                for this product based ONLY on the data below.

                STRICT RULES:
                - Mention the product name and also the current price in rupees
                - Do NOT list the historical points.
                - Do NOT invent specifications.
                - Summarize the trend: stable, rising, falling, volatile.
                - Mention if prices seem seasonal or discount-based.
                - Tell whether the current price is above/below the trend.
                - Give a simple buyer recommendation.

                Price history data:
                {json.dumps(history_rows, indent=2)}
                """

                try:
                    llm_resp = model.generate_content(llm_history_prompt)
                    summary_text = (llm_resp.text or "").strip()
                except:
                    summary_text = "Here is the recent price trend for this product."

                result_payload["response"]=summary_text
                result_payload["price_history"] = {
                    "product": product_name,
                    "category": category,
                    "history": history_rows,
                    "svg_base64": chart_svg,
                    "png_base64": chart_png,
                    "thumb_base64": chart_thumb,
                    "llm_summary": summary_text
                }
        elif fname == "set_reminder":
            result_payload["response"] = "Your reminder has been set! I’ll notify you at the scheduled time 😊"

            # Extract data
            remind_output = tool_result

            # If tool failed
            if not remind_output.get("success"):
                result_payload["response"] = "⚠ I couldn't save the reminder."

        elif fname == "predict_future_price":
            predictions = tool_result.get("predictions") or []
            chart_svg = tool_result.get("chart_svg")
            chart_thumb = tool_result.get("chart_thumb")
            model_type = tool_result.get("model_used", "Hybrid Model")
            product= tool_result.get("product"),
            category= tool_result.get("category"),
            history= tool_result.get("history"),
            svg_base64= tool_result.get("svg_base64"),
            png_base64= tool_result.get("png_base64"),
            thumb_base64= tool_result.get("thumb_base64")

            if not predictions:
                result_payload["response"] = "I couldn't generate a future price forecast."
            else:
                # LLM summary prompt
                llm_forecast_prompt = f"""
                You are an expert price forecaster.

                Write a forecast summary 
                based ONLY on the predicted values below.
                Also mention the product data with the predicted price in rupees of product for the particular date

                RULES:
                - Identify trend direction: rising, stable, falling.
                - Mention volatility if visible.
                - Explain whether buying now or later is smarter.
                - Keep it simple and buyer-focused.

                Predicted values ({len(predictions)} days):
                {json.dumps(predictions, indent=2)}

                Model used: {model_type}
                """

                try:
                    llm_resp = model.generate_content(llm_forecast_prompt)
                    summary_text = (llm_resp.text or "").strip()
                except:
                    summary_text = "Here is your price forecast based on the trend."

                result_payload["price_prediction"] = {
                    "product": product,
                    "category": category,
                    "history": history,
                    "predictions": predictions,
                    "svg_base64": svg_base64,
                    "png_base64": png_base64,
                    "thumb_base64":thumb_base64,
                    "llm_summary": summary_text,
                    "model": model_type
                }

                result_payload["response"]=summary_text

        elif fname == "predict_price":
            summary_text, product_cards = format_price_prediction_for_user(tool_result, fargs)
            result_payload["response"] = summary_text
            result_payload["product"] = product_cards
        else:
            result_payload["response"] = "Here are the results."

        # send tool result back to Gemini for friendly reply
        try:
            if fname not in("recommend_products", "compare_prices","analyze_reviews","get_price","predict_future_price","get_price_history"):
                follow_up_contents = [
                    initial.candidates[0].content,
                    {"role": "user", "parts": [{"function_response": {"name": fname, "response": tool_result}}]}
                ]
                follow_up = model.generate_content(follow_up_contents)
                result_payload["response"] = follow_up.text.strip() if getattr(follow_up, "text", None) else summary_text
            else:
                result_payload["response"]=summary_text
        except Exception as e:
            print("Follow-up failed:", e)
            friendly = summary_text

        if orig_lang != "en":
            friendly = translate_text(friendly, "en", orig_lang)

        return result_payload


    # Normal response
    text_out = initial.text.strip() if getattr(initial, "text", None) else ""
    if not text_out:
        try:
            text_out = initial.candidates[0].content.parts[0].text or ""
        except:
            text_out = "I didn't understand. Can you rephrase?"
    if orig_lang != "en":
        text_out = translate_text(text_out, "en", orig_lang)
    return {"response": text_out, "products": []}

# Streaming & endpoints (same as earlier)
def stream_text_chunks(text, delay=0.04):
    for i in range(0, len(text), 40):
        chunk = text[i:i+40]
        yield chunk
        time.sleep(delay)

@app.route("/message_stream", methods=["POST"])
@cross_origin(origins=["http://localhost:5173",allowed_url])
def send_message_stream():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation_id")
        user_msg = data.get("message", "")
        lang = data.get("lang", "en-US").split("-")[0]

        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        db.session.add(Message(conversation_id=conversation_id, role="user", content=user_msg))
        db.session.commit()

        result = generate_ai_response(user_msg, conversation_id, lang)
        response_text = result["response"]
        products = result.get("products", [])

        db.session.add(Message(conversation_id=conversation_id, role="assistant", content=response_text))
        conversation.updated_at = datetime.utcnow()
        db.session.commit()

        def gen():
            meta = json.dumps({"type": "meta", "products": products})
            yield f"data: {meta}\n\n"
            for chunk in stream_text_chunks(response_text):
                data = json.dumps({"type": "text", "chunk": chunk})
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'type':'done'})}\n\n"

        return Response(gen(), mimetype="text/event-stream")

    except Exception as e:
        print("STREAM ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

@app.route("/message", methods=["POST"])
@cross_origin(origins=["http://localhost:5173",allowed_url])
def send_message():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation_id")
        
        user_msg = data.get("message", "")
        lang = data.get("lang", "en-US").split("-")[0]

        conversation = Conversation.query.get(conversation_id)
        global LAST_USER_ID
        LAST_USER_ID = conversation.user_id
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        db.session.add(Message(conversation_id=conversation_id, role="user", content=user_msg))
        db.session.commit()

        result = generate_ai_response(user_msg, conversation_id, lang)
        products = result.get("products", [])
        price_history = result.get("price_history") or None
        price_prediction = result.get("price_prediction") or None
        reviews = result.get("reviews") or None
        db.session.add(Message(
            conversation_id=conversation_id,
            role="assistant",
            content=result["response"],
            products=products,
            price_history=price_history,
            price_prediction=price_prediction,
            reviews=reviews
        ))
        conversation.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(result), 200

    except Exception as e:
        print("MESSAGE ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500





# llm_comparison_prompt = f"""
# You are an expert shopping assistant.
# Create a professional, concise comparison summary for the user.

# Based ONLY on the tool results below (do NOT invent data),
# compare prices, ratings, reliability, and value for money across platforms.

# DO NOT list every product again.
# DO NOT repeat item details.
# DO NOT hallucinate missing information.

# Focus on:
# - Which platform offers the lowest price ("Best Deal")
# - Which option is best overall considering price + rating ("Best Overall Choice")
# - Notable differences between platforms
# - Whether the pricing looks like a temporary discount or a consistent advantage
# - Platform trustworthiness (Amazon, Flipkart, etc.)
# - Category-aware judgment (electronics, clothing, accessories, etc.) based on keywords
# - What type of buyer this suits (budget, balanced, premium)

# At the end, include:
# - A short confidence note based strictly on the amount of available data.

# Here are the top product results (max 5), in JSON:
# {json.dumps(top_products, indent=2)}
# """
