"""Sentiment analysis + complaint clustering.

Uses a Hugging Face model if USE_TRANSFORMER=1 (needs `transformers` + `torch`),
otherwise a light lexicon-based scorer (fast, no GPU, good for CI).
"""
import os, re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

POS = {"good", "great", "excellent", "love", "amazing", "fast", "perfect", "happy", "best", "awesome", "helpful", "easy"}
NEG = {"bad", "terrible", "slow", "worst", "hate", "broken", "awful", "poor", "late", "refund", "disappointed", "crash", "expensive", "rude"}

_pipe = None


def _transformer():
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline("sentiment-analysis", model="cardiffnlp/twitter-xlm-roberta-base-sentiment")
    return _pipe


def analyze(text: str) -> tuple[str, float]:
    if os.getenv("USE_TRANSFORMER") == "1":
        r = _transformer()(text[:512])[0]
        return r["label"].lower(), float(r["score"])
    words = re.findall(r"[a-z']+", text.lower())
    p, n = sum(w in POS for w in words), sum(w in NEG for w in words)
    if p == n:
        return "neutral", 0.5
    return ("positive" if p > n else "negative"), round(max(p, n) / (p + n), 2)


def cluster_complaints(texts: list[str], k: int = 3, top_terms: int = 4) -> list[dict]:
    """Group negative reviews into topics, each named by its top TF-IDF terms."""
    if len(texts) < 2:
        return []
    k = min(k, len(texts))
    vec = TfidfVectorizer(stop_words="english", max_features=500)
    X = vec.fit_transform(texts)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    terms = vec.get_feature_names_out()
    counts = Counter(km.labels_)
    out = []
    for i in range(k):
        idx = km.cluster_centers_[i].argsort()[::-1][:top_terms]
        out.append({"topic": ", ".join(terms[j] for j in idx), "count": counts[i]})
    return sorted(out, key=lambda c: -c["count"])
