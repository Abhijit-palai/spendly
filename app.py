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
        return redirect(url_for("dashboard"))

    if session.get("user_id"):
        return redirect(url_for("dashboard"))
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
        return redirect(url_for("dashboard"))

    if session.get("user_id"):
        return redirect(url_for("dashboard"))
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
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
