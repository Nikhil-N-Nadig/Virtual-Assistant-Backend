import spacy
nlp = spacy.load("en_core_web_sm")

def parse_intent(text):
    doc = nlp(text)
    intent = {"text": text, "filters": {}, "intent": "search"}
    # simple rules: price range, sort by, category
    for ent in doc.ents:
        if ent.label_ in ("MONEY",):
            intent["filters"]["price_mention"] = ent.text
    if "cheapest" in text or "lowest price" in text:
        intent["filters"]["sort"] = "price_asc"
    if "best" in text or "best seller" in text:
        intent["filters"]["sort"] = "rating_desc"
    # language detection fallback (use langdetect if needed)
    return intent
