import datetime
import os
import re

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    EmailAlreadyExistsError,
    create_user,
    find_user_by_email,
    get_db,
    init_db,
    seed_db,
)

app = Flask(__name__)

# ------------------------------------------------------------------ #
# Session / cookie config                                             #
# ------------------------------------------------------------------ #

app.config["SECRET_KEY"] = (
    os.environ.get("SPENDLY_SECRET_KEY") or "dev-secret-key-change-me"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Map free-text category names stored in the DB to lowercase slug classes
# used by the templates for badge / dot / bar colouring.
CATEGORY_SLUG = {
    "Food":          "food",
    "Transport":     "transport",
    "Travel":        "transport",
    "Shopping":      "shopping",
    "Bills":         "bills",
    "Health":        "health",
    "Entertainment": "entertainment",
    "Other":         "other",
}


def _slug(category: str) -> str:
    """Return the CSS class slug for a free-text category, or 'other'."""
    return CATEGORY_SLUG.get(category, "other")


def _fmt_amount(value) -> str:
    """Format a numeric amount as a comma-separated rupee string."""
    return f"{float(value):,.2f}"


def _fmt_date(iso: str) -> str:
    """Format an ISO date string as '02 Jun 2026' for display."""
    try:
        return datetime.date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def _greeting() -> str:
    """Return 'morning' / 'afternoon' / 'evening' based on local hour."""
    h = datetime.datetime.now().hour
    if h < 12:
        return "morning"
    if h < 17:
        return "afternoon"
    return "evening"

# ------------------------------------------------------------------ #
# Database initialisation                                             #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name:
            return render_template(
                "register.html", error="Please enter your name."
            )
        if not email or not EMAIL_REGEX.match(email) or len(email) > 254:
            return render_template(
                "register.html", error="Please enter a valid email address."
            )
        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters long.",
            )

        try:
            user_id = create_user(name, email, password)
        except EmailAlreadyExistsError:
            return render_template(
                "register.html",
                error="An account with that email already exists.",
            )

        session.clear()
        session["user_id"] = user_id
        session["name"] = name
        return redirect(url_for("profile"))

    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Single generic failure path to avoid leaking which field is
        # wrong (account-enumeration defence).
        generic_error = "Invalid email or password."

        user = find_user_by_email(email) if email else None
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error=generic_error)

        session.clear()
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        return redirect(url_for("profile"))

    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    full_name = session.get("name") or ""
    first_name = full_name.split(" ", 1)[0] or full_name or "there"

    with get_db() as conn:
        # User info
        user_row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        initials = "".join(part[0].upper() for part in full_name.split()[:2]) or "?"
        member_since = _fmt_date(user_row["created_at"][:10]) if user_row else "—"

        # Summary stats (hardcoded-style aggregation over the real DB)
        txn_row = conn.execute(
            "SELECT COUNT(*) AS c, COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        txn_count = int(txn_row["c"] or 0)
        total_spent = float(txn_row["total"] or 0)

        today = datetime.date.today()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        month_start_iso = today.replace(day=1).isoformat()
        next_month_iso = next_month.isoformat()

        top_row = conn.execute(
            "SELECT category, SUM(amount) AS s "
            "FROM expenses WHERE user_id = ? AND date >= ? AND date < ? "
            "GROUP BY category ORDER BY s DESC LIMIT 1",
            (user_id, month_start_iso, next_month_iso),
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"
        top_category_amount = _fmt_amount(top_row["s"]) if top_row else "0.00"

        # Transaction history (all rows for the user, newest first)
        recent_rows = conn.execute(
            "SELECT id, date, category, amount, description "
            "FROM expenses WHERE user_id = ? "
            "ORDER BY date DESC, id DESC",
            (user_id,),
        ).fetchall()
        transactions = [
            {
                "id": r["id"],
                "date": _fmt_date(r["date"]),
                "category": r["category"],
                "category_class": _slug(r["category"]),
                "amount": _fmt_amount(r["amount"]),
                "description": r["description"] or "",
            }
            for r in recent_rows
        ]

        # Category breakdown (all-time, sorted by total)
        cat_rows = conn.execute(
            "SELECT category, SUM(amount) AS s "
            "FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY s DESC",
            (user_id,),
        ).fetchall()
        max_amt = max((float(c["s"]) for c in cat_rows), default=1) or 1
        categories = [
            {
                "name": c["category"],
                "amount": _fmt_amount(c["s"]),
                "percent": round((float(c["s"]) / max_amt) * 100),
                "color_class": _slug(c["category"]),
            }
            for c in cat_rows
        ]

    stats = {
        "total_spent": _fmt_amount(total_spent),
        "txn_count": txn_count,
        "top_category": top_category,
        "top_category_amount": top_category_amount,
    }
    user = {
        "name": user_row["name"] if user_row else full_name,
        "initials": initials,
        "email": user_row["email"] if user_row else "",
        "member_since": member_since,
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    # Step 7 will validate the form and insert the row.
    return render_template("add_expense.html", form={})


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    # Step 8 will load the row, validate, and update.
    return render_template("edit_expense.html", expense={"id": id})


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    # Step 9 will delete the row and redirect.
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
