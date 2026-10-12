"""Generate a synthetic customer-review dataset (600 rows over 60 days).

Includes a deliberate "bad release" window where app-crash complaints spike,
so the dashboard trend and complaint clusters have something to show.
Run:  python scripts/generate_reviews.py
"""
import csv, random
from datetime import date, timedelta

random.seed(42)
START, DAYS, N = date(2026, 8, 1), 60, 600

POSITIVE = [
    "Great product and fast delivery, I love it",
    "Excellent quality, best purchase this year",
    "Amazing value, perfect for my needs",
    "Easy to use and the support team was very helpful",
    "Awesome service, I am very happy with the order",
    "Fast shipping and great packaging",
    "Good price and excellent customer service",
    "Love the new design, it is perfect",
]
NEUTRAL = [
    "The package arrived on Tuesday",
    "I ordered the blue version in size medium",
    "Received the item and tested it for a week",
    "The box contains the device and a charger",
    "Ordered two units for the office",
    "Delivery tracking showed the parcel at the depot",
]
NEG = {
    "delivery": [
        "Delivery was slow and late again",
        "Shipping is slow and the parcel arrived late",
        "Terrible shipping, slow delivery and no tracking updates",
        "Late delivery, worst shipping experience",
    ],
    "support": [
        "Terrible customer support, very rude staff",
        "Awful experience, support never replied",
        "Rude support agent and no refund",
        "Support was slow and unhelpful, very disappointed",
    ],
    "app": [
        "The app keeps crash every time I open it",
        "App crash after the update, very disappointed",
        "Terrible update, the app crash on login",
        "Bad release, app is slow and crash all the time",
    ],
    "quality": [
        "Package arrived broken, I want a refund",
        "Poor quality, the screen was broken",
        "Bad packaging and the item is broken",
        "Poor build quality, disappointed",
    ],
    "price": [
        "Too expensive for what you get",
        "Expensive and poor value, I want a refund",
        "Bad pricing, very expensive shipping",
    ],
}


def pick(day_idx: int) -> str:
    # Days 28-35: bad app release -> negative spike dominated by app crashes
    if 28 <= day_idx <= 35:
        r = random.random()
        if r < 0.55:
            return random.choice(NEG["app"])
        if r < 0.75:
            return random.choice(NEG["support"])
        return random.choice(POSITIVE + NEUTRAL)
    r = random.random()
    if r < 0.48:
        return random.choice(POSITIVE)
    if r < 0.68:
        return random.choice(NEUTRAL)
    return random.choice(NEG[random.choice(["delivery", "delivery", "support", "quality", "price", "app"])])


rows = []
for _ in range(N):
    d = random.randrange(DAYS)
    rows.append(((START + timedelta(days=d)).isoformat(), pick(d)))
rows.sort()

with open("data/reviews_large.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "text"])
    w.writerows(rows)
print(f"Wrote {len(rows)} rows to data/reviews_large.csv")
