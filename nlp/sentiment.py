from transformers import pipeline
sent_pipe = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

def analyze_sentiments(texts):
    # texts = list of review strings
    return sent_pipe(texts)
