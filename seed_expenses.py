"""Seed realistic dummy expenses for a given user.

Usage: python seed_expenses.py <user_id> <count> <months>
"""
import random
import sys
from datetime import date, timedelta

from database.db import get_db


# Category definitions: (name, weight, (min_amt, max_amt), [descriptions])
CATEGORIES = [
    (
        "Food",
        30,
        (50, 800),
        [
            "Chai and samosa at local tapri",
            "Lunch thali at restaurant",
            "Dinner biryani",
            "Groceries from D-Mart",
            "Breakfast idli dosa",
            "Swiggy order",
            "Zomato dinner",
            "Mumbai pav bhaji",
            "Chole bhature at Haldiram",
            "Filter coffee at Cafe",
            "Vada pav and cutting chai",
            "Fresh vegetables from sabziwala",
            "Milk and bread from kirana store",
            "Maggi at roadside stall",
            "Paneer butter masala with naan",
        ],
    ),
    (
        "Transport",
        18,
        (20, 500),
        [
            "Uber auto to office",
            "Ola cab ride",
            "Petrol refill",
            "Metro card recharge",
            "BMTC bus pass",
            "Rapido bike ride",
            "Train ticket local",
            "Auto rickshaw fare",
            "Diesel for scooter",
            "Parking charges at mall",
            "Cab to airport",
            "State transport bus ticket",
        ],
    ),
    (
        "Bills",
        12,
        (200, 3000),
        [
            "Electricity bill BSES",
            "Airtel mobile recharge",
            "Jio Fiber broadband bill",
            "LPG cylinder refill",
            "Water tanker",
            "Gas bill Adani",
            "Tata Sky DTH recharge",
            "Society maintenance charge",
            "Insurance premium quarterly",
            "Credit card bill payment",
        ],
    ),
    (
        "Health",
        5,
        (100, 2000),
        [
            "Pharmacy at Apollo",
            "Doctor consultation fee",
            "Blood test at pathology lab",
            "Dental cleaning",
            "Ayurvedic medicines",
            "Eye checkup at Lenskart",
            "Vitamin supplements",
            "Gym monthly membership",
            "Yoga class fee",
        ],
    ),
    (
        "Entertainment",
        7,
        (100, 1500),
        [
            "PVR movie tickets",
            "Netflix monthly subscription",
            "Spotify Premium plan",
            "Book from Crossword",
            "Stand-up comedy show",
            "Disney+ Hotstar subscription",
            "Concert ticket",
            "Board game cafe visit",
        ],
    ),
    (
        "Shopping",
        13,
        (200, 5000),
        [
            "Amazon order - headphones",
            "Flipkart sale - t-shirt",
            "Myntra kurta purchase",
            "Lifestyle footwear",
            "Westside clothing haul",
            "Nykaa cosmetics",
            "Decathlon sports gear",
            "IKEA home essentials",
            "Croma electronics",
            "Reliance Digital phone cover",
        ],
    ),
    (
        "Other",
        15,
        (50, 1000),
        [
            "Salon haircut and beard trim",
            "Laundry dry cleaning",
            "Gift wrapping supplies",
            "Stationery from shop",
            "Petrol for generator",
            "Donation at temple",
            "Courier delivery charges",
            "Newspaper and magazine",
            "Watch battery replacement",
            "Mobile screen guard",
        ],
    ),
]


def pick_category():
    names = [c[0] for c in CATEGORIES]
    weights = [c[1] for c in CATEGORIES]
    return random.choices(names, weights=weights, k=1)[0]


def random_amount(category_name):
    for name, _weight, (lo, hi), _descs in CATEGORIES:
        if name == category_name:
            return round(random.uniform(lo, hi), 2)
    return 0.0


def random_description(category_name):
    for name, _w, _amt, descs in CATEGORIES:
        if name == category_name:
            return random.choice(descs)
    return ""


def random_dates(count, months):
    today = date.today()
    span_days = months * 30
    earliest = today - timedelta(days=span_days)
    return [
        (earliest + timedelta(days=random.randint(0, span_days))).isoformat()
        for _ in range(count)
    ]


def main():
    if len(sys.argv) != 4:
        print("Usage: python seed_expenses.py <user_id> <count> <months>")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
    except ValueError:
        print("Usage: python seed_expenses.py <user_id> <count> <months>")
        sys.exit(1)

    if count <= 0 or months <= 0:
        print("count and months must be positive integers")
        sys.exit(1)

    # Verify user exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            print(f"No user found with id {user_id}.")
            sys.exit(1)

        random.seed()  # nondeterministic
        dates = random_dates(count, months)

        rows = []
        for d in dates:
            cat = pick_category()
            rows.append(
                (
                    user_id,
                    random_amount(cat),
                    cat,
                    d,
                    random_description(cat),
                )
            )

        try:
            cursor.execute("BEGIN")
            cursor.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            inserted = cursor.rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Insert failed, rolled back: {e}")
            sys.exit(1)

        # Confirmation stats
        cursor.execute(
            "SELECT MIN(date) AS min_d, MAX(date) AS max_d "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        )
        stats = cursor.fetchone()
        min_d = stats["min_d"]
        max_d = stats["max_d"]

        print(f"Inserted {inserted} expenses for user_id={user_id}")
        print(f"Date range: {min_d} to {max_d}")
        print("Sample of inserted records:")
        cursor.execute(
            "SELECT id, date, category, amount, description "
            "FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (user_id,),
        )
        for row in cursor.fetchall():
            print(
                f"  id={row['id']} | {row['date']} | {row['category']:<14} "
                f"| Rs {row['amount']:>7.2f} | {row['description']}"
            )


if __name__ == "__main__":
    main()
