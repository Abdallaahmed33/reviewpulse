import os
import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="ReviewPulse", page_icon="📊", layout="wide")
st.title("📊 ReviewPulse")


def show_error(r):
    try:
        detail = r.json().get("detail", r.text)
        if isinstance(detail, list):
            detail = "; ".join(d.get("msg", "") for d in detail)
    except Exception:
        detail = r.text
    st.error(detail)


if "token" not in st.session_state:
    st.session_state.token = None

if not st.session_state.token:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    c1, c2 = st.columns(2)
    if c1.button("Login"):
        r = requests.post(f"{API}/auth/token", data={"username": u, "password": p})
        if r.ok:
            st.session_state.token = r.json()["access_token"]
            st.rerun()
        else:
            show_error(r)
    if c2.button("Register"):
        r = requests.post(f"{API}/auth/register", json={"username": u, "password": p})
        if r.ok:
            st.success("Registered, now login")
        else:
            show_error(r)
    st.stop()

H = {"Authorization": f"Bearer {st.session_state.token}"}

with st.sidebar:
    st.header("Add reviews")
    f = st.file_uploader("CSV with a 'text' column", type="csv")
    if f and st.button("Upload"):
        r = requests.post(f"{API}/reviews/upload", files={"file": f.getvalue()}, headers=H)
        if r.ok:
            st.success(f"Imported {r.json().get('imported')}")
        else:
            show_error(r)
    txt = st.text_area("Or a single review")
    if txt and st.button("Analyze"):
        r = requests.post(f"{API}/reviews", json={"text": txt}, headers=H)
        if r.ok:
            st.info(f"{r.json()['sentiment']} ({r.json()['score']})")
        else:
            show_error(r)
    if st.button("Logout"):
        st.session_state.token = None
        st.rerun()

d = requests.get(f"{API}/insights", headers=H).json()
if not d.get("total"):
    st.info("No reviews yet. Upload `sample_reviews.csv` from the sidebar.")
    st.stop()

m = st.columns(4)
m[0].metric("Total", d["total"])
for i, s in enumerate(["positive", "neutral", "negative"], 1):
    m[i].metric(s.title(), d["sentiment_counts"].get(s, 0))

a, b = st.columns(2)
a.subheader("Sentiment distribution")
a.bar_chart(pd.Series(d["sentiment_counts"]))
b.subheader("Top complaint topics")
b.dataframe(pd.DataFrame(d["top_complaints"]))
st.subheader("Sentiment trend")
st.line_chart(pd.DataFrame(d["trend"]).set_index("date").fillna(0))