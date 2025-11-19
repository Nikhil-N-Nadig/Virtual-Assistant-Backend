from transformers import pipeline
summ = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize_reviews(reviews, max_length=60):
    joined = " ".join(reviews)
    out = summ(joined, max_length=max_length, min_length=20, do_sample=False)
    return out[0]['summary_text']
