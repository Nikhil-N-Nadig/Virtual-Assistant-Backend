# from flask import request, jsonify
# from shopmate import app
# # from transformers import pipeline
# from textblob import TextBlob
# from googleapiclient.discovery import build
# from langdetect import detect
# from sentence_transformers import SentenceTransformer, util
# import torch, requests, re, os, random, io, base64, time
# from deep_translator import GoogleTranslator
# from PIL import Image
# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt

# # from transformers import AutoTokenizer, AutoModel
# # import torch


# print("🔄 Loading models for review analysis...")
# sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
# embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
# embedding_model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
# print("✅ Models loaded successfully.")

# YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# def clean_text(text: str) -> str:
#     text = re.sub(r"http\S+|www\S+|@\S+|#\S+", "", text)
#     text = re.sub(r"[^A-Za-z0-9\s.,!?']", " ", text)
#     text = re.sub(r"\s+", " ", text).strip()
#     return text

# def translate_text(text: str, source: str, target: str) -> str:
#     try:
#         return GoogleTranslator(source=source, target=target).translate(text)
#     except:
#         return text

# def is_valid_review(text: str) -> bool:
#     text = text.lower().strip()

#     if len(text.split()) < 6:
#         return False

#     keywords = [
#         "good", "bad", "great", "amazing", "worst", "excellent",
#         "terrible", "love", "hate", "battery", "camera", "price",
#         "quality", "performance", "design", "review", "issue"
#     ]

#     if not any(k in text for k in keywords):
#         return False

#     try:
#         if detect(text) != "en":
#             return False
#     except:
#         pass

#     return True

# reference_reviews = [
#     "The product quality is great",
#     "Battery life could be better",
#     "Camera is amazing for this price",
#     "Not worth the money",
#     "Performance is smooth and fast",
#     "The build feels premium",
#     "Customer service was terrible",
#     "Got damaged during delivery",
#     "Sound quality is impressive",
#     "Heating issue after long use",
# ]
# reference_embeddings = embedding_model.encode(reference_reviews, convert_to_tensor=True)

# def semantic_review_filter(comments, threshold=0.45):
#     if not comments:
#         return []
#     comment_embeddings = embedding_model.encode(comments, convert_to_tensor=True)
#     cosine_scores = util.cos_sim(comment_embeddings, reference_embeddings)
#     valid = []
#     for i, scores in enumerate(cosine_scores):
#         if torch.max(scores).item() > threshold:
#             valid.append(comments[i])
#     return valid

# def fetch_youtube_comments(video_id, max_total=200):
#     comments = []
#     youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

#     request = youtube.commentThreads().list(
#         part="snippet",
#         videoId=video_id,
#         maxResults=100,
#         textFormat="plainText"
#     )

#     while request and len(comments) < max_total:
#         response = request.execute()
#         for item in response.get("items", []):
#             text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
#             comments.append(clean_text(text))
#         request = youtube.commentThreads().list_next(request, response)

#     return comments[:max_total]

# def create_sentiment_pie_chart_svg(positive_count, negative_count, neutral_count):
#     labels = []
#     sizes = []
#     if positive_count:
#         labels.append(f"Positive ({positive_count})"); sizes.append(positive_count)
#     if negative_count:
#         labels.append(f"Negative ({negative_count})"); sizes.append(negative_count)
#     if neutral_count:
#         labels.append(f"Neutral ({neutral_count})"); sizes.append(neutral_count)

#     # Ensure at least one slice to avoid matplotlib errors
#     if not sizes:
#         labels = ["No data"]
#         sizes = [1]

#     fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
#     # use default colors (do not force custom palette)
#     wedges, texts, autotexts = ax.pie(
#         sizes,
#         labels=labels,
#         autopct=lambda pct: f"{int(round(pct * sum(sizes) / 100.0))}",
#         startangle=90,
#         wedgeprops=dict(width=0.5)
#     )
#     ax.axis("equal")
#     plt.tight_layout()

#     # SVG bytes
#     svg_buf = io.BytesIO()
#     fig.savefig(svg_buf, format="svg")
#     svg_bytes = svg_buf.getvalue()
#     svg_b64 = base64.b64encode(svg_bytes).decode("utf-8")
#     svg_buf.close()

#     # Also produce a small PNG thumbnail (base64) for quick display
#     png_buf = io.BytesIO()
#     fig.savefig(png_buf, format="png", dpi=150)
#     png_buf.seek(0)
#     try:
#         img = Image.open(png_buf)
#         img.thumbnail((280, 180), Image.LANCZOS)
#         thumb_buf = io.BytesIO()
#         img.save(thumb_buf, format="PNG", optimize=True)
#         thumb_b64 = base64.b64encode(thumb_buf.getvalue()).decode("utf-8")
#         thumb_buf.close()
#     except Exception:
#         thumb_b64 = None
#     png_buf.close()
#     plt.close(fig)

#     return svg_b64, thumb_b64

# @app.route("/analyze_reviews", methods=["POST"])
# def analyze_reviews():
#     data = request.get_json() or {}
#     product = data.get("product")
#     detailed = data.get("detailed", False)
#     language = data.get("language", "en")

#     if not product:
#         return jsonify({"error": "Product name required"}), 400

#     all_comments = []

#     # Fetch YouTube comments
#     try:
#         youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
#         search = youtube.search().list(
#             q=product + " review",
#             part="id",
#             type="video",
#             maxResults=1
#         ).execute()

#         if search.get("items"):
#             video_id = search["items"][0]["id"]["videoId"]
#             yt_comments = fetch_youtube_comments(
#                 video_id,
#                 max_total=(300 if detailed else 120)
#             )
#             all_comments.extend(yt_comments)

#     except Exception as e:
#         print("YouTube fetch error:", e)

#     # Fallback short samples if none found
#     if not all_comments:
#         all_comments = [
#             f"{product} is good overall.",
#             f"Battery could be improved on {product}.",
#             f"{product} feels premium and worth the money.",
#             f"Camera quality of {product} is disappointing."
#         ]

#     # Clean + Filter
#     cleaned = [clean_text(c) for c in all_comments if is_valid_review(clean_text(c))]
#     filtered = semantic_review_filter(cleaned)
#     comments = filtered or cleaned
#     # dedupe and keep reasonably long comments
#     comments = list(dict.fromkeys(comments))
#     comments = [c for c in comments if len(c.split()) >= 5]

#     # Sentiment Analysis
#     sentiments = []
#     for comment in comments:
#         try:
#             model_sent = sentiment_analyzer(comment[:500])[0]["label"]
#         except Exception:
#             model_sent = "NEUTRAL"
#         blob_polarity = TextBlob(comment).sentiment.polarity
#         blob_sent = "POSITIVE" if blob_polarity > 0.1 else ("NEGATIVE" if blob_polarity < -0.1 else "NEUTRAL")
#         final = model_sent if model_sent == blob_sent else "NEUTRAL"
#         sentiments.append((comment, final))

#     positive = [c for c, s in sentiments if s == "POSITIVE"]
#     negative = [c for c, s in sentiments if s == "NEGATIVE"]
#     neutral = [c for c, s in sentiments if s == "NEUTRAL"]

#     # Build textual summary
#     summary = f"🧠 Here’s what people are saying about **{product}**:\n\n"
#     if positive: summary += "🟢 **What users loved:**\n" + "\n".join([f"• {p}" for p in positive[:5]]) + "\n\n"
#     if negative: summary += "🔴 **Common complaints:**\n" + "\n".join([f"• {n}" for n in negative[:5]]) + "\n\n"
#     if neutral:  summary += "⚪ **Neutral points:**\n" + "\n".join([f"• {n}" for n in neutral[:5]]) + "\n"


#     # Translate summary if requested
#     if language != "en":
#         try:
#             summary = translate_text(summary, "en", language)
#         except Exception:
#             pass

#     # Return structured response including chart images (base64)
#     return jsonify({
#         "success": True,
#         "response": summary,
#         "counts": {"positive": len(positive), "negative": len(negative), "neutral": len(neutral)},
#         # "sentiment_chart_svg_base64": svg_b64,
#         # "sentiment_chart_thumb_base64": thumb_b64,
#         "comments_sample": {
#             "positive": positive[:5],
#             "negative": negative[:5],
#             "neutral": neutral[:5]
#         }
#     }), 200
