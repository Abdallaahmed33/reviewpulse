# 📊 ReviewPulse

**Updated, production-style version** of my ITI graduation project [AI Customer Feedback Intelligence](https://github.com/Abdallaahmed33/ai-customer-feedback-intelligence).

The original system was a notebook + trained ML models + a static HTML dashboard + a small Flask demo. ReviewPulse is the same problem, rebuilt as a real app: ingest live reviews, score sentiment, cluster complaints, and explore everything in a dashboard.

![CI](https://github.com/Abdallaahmed33/reviewpulse/actions/workflows/ci.yml/badge.svg)

## What changed vs the original

| Original (ITI) | ReviewPulse (this repo) |
|---|---|
| Jupyter notebook on a fixed CSV (~22k clothing reviews) | FastAPI app: one review or bulk CSV upload |
| Logistic Regression / Random Forest / Naive Bayes | Hugging Face multilingual sentiment (Arabic + English) or a lexicon fallback |
| K-Means complaint categories in the notebook | TF-IDF + KMeans on **your** negative reviews, on demand |
| Static `dashboard.html` | Live Streamlit dashboard (JWT login) |
| Flask `app.py` / CLI `predict.py` | REST API with auth, Swagger (`/docs`), admin user management |
| Saved `.pkl` artifacts | PostgreSQL (SQLite locally), GitHub Actions CI, pytest |

Original write-up and models: [ai-customer-feedback-intelligence](https://github.com/Abdallaahmed33/ai-customer-feedback-intelligence)

## Features
- **FastAPI** REST API with JWT authentication and Swagger docs (`/docs`)
- **Sentiment analysis**: Hugging Face multilingual model (Arabic + English) or a lightweight lexicon fallback
- **Complaint clustering**: TF-IDF + KMeans groups negative reviews into named topics
- **Streamlit dashboard**: sentiment distribution, trend over time, top complaint topics
- **PostgreSQL** (SQLite for local dev), GitHub Actions CI, pytest suite

## Architecture
```
CSV / API  ->  FastAPI  ->  NLP (sentiment + clustering)  ->  PostgreSQL
                                   ^
                    Streamlit dashboard (JWT)
```

## Screenshots

### Dashboard overview
![ReviewPulse dashboard showing sentiment totals and complaint topics](Screenshots/Screenshot%20%28102%29.png)

### Sentiment trend
![ReviewPulse dashboard showing the sentiment trend over time](Screenshots/Screenshot%20%28103%29.png)

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload            # API  -> http://localhost:8000/docs
streamlit run dashboard.py               # UI   -> http://localhost:8501
pytest                                   # tests
```
To use the optional Hugging Face model, install its dependencies:
```bash
pip install transformers torch
```
Then set `USE_TRANSFORMER` in the same terminal session where you start the API.

PowerShell:
```powershell
$env:USE_TRANSFORMER = "1"
uvicorn app.main:app --reload
```

## Admin account management
Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` before starting the API. On first startup, the API creates that admin account; the password must be at least 12 characters. Existing databases are updated with an `is_admin` column automatically. The admin endpoints require a JWT for that account:
- `GET /admin/users` lists accounts and their review counts
- `DELETE /admin/users/{user_id}` deletes an account and its reviews

An admin cannot delete their own account or the last admin. Set both variables in the same shell session before starting the API.

## API
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/token` | Get JWT |
| POST | `/reviews` | Analyze one review |
| POST | `/reviews/upload` | Bulk CSV (`text` column) |
| GET | `/reviews` | List, filter by sentiment |
| GET | `/insights` | Counts, trend, top complaint topics |


Built by [Abdalla Ahmed](https://github.com/Abdallaahmed33)
