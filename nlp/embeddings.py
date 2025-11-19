from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import os
MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)
index = None
product_embeddings_map = {}  # id -> vector

def build_index(products):
    global index, product_embeddings_map
    texts = [p['title']+" "+(p.get("description","")) for p in products]
    vectors = model.encode(texts, convert_to_numpy=True)
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)
    for i,p in enumerate(products):
        product_embeddings_map[i] = p
    return index

def query_similar(text, k=10):
    vec = model.encode([text], convert_to_numpy=True)
    D, I = index.search(vec, k)
    return [product_embeddings_map[i] for i in I[0] if i in product_embeddings_map]
