import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Helper function for buy
from buy_helpers import validate_inputs, create_transactions, io_transactions, check_funds, update_balance
from sell_helpers import check_inputs, io_sells
from history import create_history, io_history


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']

    table_name = f"transactions_{user_id}"
    table_exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", table_name)

    if table_exists:
        all = db.execute("SELECT * FROM transactions_?", user_id)
        balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']
        print(f"VALUE OF LOOKUP: {lookup("grmn")}")
        prices = {}
        total = 0
        for stock in all:
            prices[f"{stock['symbol']}"] = lookup(stock['symbol'])['price']
            total += (prices[f"{stock['symbol']}"] * db.execute(
                "SELECT shares FROM transactions_? WHERE symbol = ?", user_id, stock['symbol'])[0]['shares'])
        return render_template("index.html", all=all, prices=prices, usd=usd, balance=balance, total=total)
    else:
        return render_template("index.html", usd=usd, balance=balance)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol").upper()
        shares = (request.form.get("shares"))

        error = validate_inputs(symbol, shares)
        if error:
            return render_template("buy.html", error=error), 400

        shares = float(shares)

        stock = lookup(symbol)
        total_price = stock["price"] * shares

        user_id = session["user_id"]
        user_balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']

        if not check_funds(user_balance, total_price):
            return apology("Insufficient funds")

        update_balance(user_id, user_balance - total_price)

        create_transactions(user_id)
        io_transactions(user_id, symbol, shares)

        create_history(user_id)
        io_history(user_id, "BOUGHT", symbol, total_price, shares)

        flash("Bought!", "success")
        return redirect("/")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_id = session["user_id"]
    table_name = f"transactions_{user_id}"
    table_exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", table_name)

    if table_exists:
        history = db.execute("SELECT * FROM history_? ORDER BY date_and_time DESC", user_id)
        return render_template("history.html", history=history, usd=usd)
    else:
        error = "No history yet"
        return render_template("history.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        try:
            stock = lookup(request.form.get("symbol"))
            stock['price'] = usd(stock['price'])
            return render_template("quote.html", stock=stock)
        except TypeError:
            error = "Invalid stock"
            return render_template("display.html", error=error), 400
    else:
        return render_template("display.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirmation")

        # Ensure username, password and confirm were submitted
        if not request.form.get("username"):
            error = "Username not provided"
            return render_template("register.html", error=error), 400
        if not password or not confirm:
            error = "Password not provided"
            return render_template("register.html", error=error), 400
        if password != confirm:
            error = "Passwords do not match"
            return render_template("register.html", error=error), 400

        # Hash user's password
        password = generate_password_hash(password)

        # Insert user into database
        try:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                       request.form.get("username"), password)
        except ValueError:
            return apology("user already exists")

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    user_id = session["user_id"]
    my_dict = db.execute("SELECT symbol, shares FROM transactions_?", user_id)
    stocks = {}

    for item in my_dict:
        stocks[item['symbol']] = item['shares']

    if request.method == "POST":
        selected_stock = request.form.get("stock")
        shares = request.form.get("shares")

        # Check if user submitted both inputs
        error = check_inputs(selected_stock, shares)
        if error:
            return render_template("sell.html", error=error, stocks=stocks), 400

        # Convert shares and find how many shares user hold's
        shares = float(shares)
        hold = db.execute("SELECT shares FROM transactions_? WHERE symbol = ?",
                          user_id, selected_stock)[0]['shares']

        # Check if user wants to sell legit amount
        if shares > hold:
            error = "Can't sell more shares than you own"
            return render_template("sell.html", error=error, stocks=stocks)

        io_sells(shares, hold, user_id, selected_stock)

        stock = lookup(selected_stock)
        total_price = stock["price"] * shares

        create_history(user_id)
        io_history(user_id, "SOLD", selected_stock, total_price, shares)

        flash("Sold!", "success")
        return redirect("/")

    else:
        return render_template("sell.html", stocks=stocks)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")

        user_id = session["user_id"]

        hash = db.execute("SELECT hash FROM users WHERE id = ?", user_id)[0]['hash']

        # Check if user filled all forms
        if not old_password or not new_password or not confirmation:
            error = "Must provide all passwords"
            return render_template("change_password.html", error=error)

        # Check if old password matches user's input
        if not check_password_hash(hash, old_password):
            error = "Old password is not valid"
            return render_template("change_password.html", error=error)

        # Check if new passwords match
        if new_password != confirmation:
            error = "Passwords do not match."
            return render_template("change_password.html", error=error)

        # Generate new hash
        new_password = generate_password_hash(new_password)

        try:
            db.execute("UPDATE users SET hash = ? WHERE id = ?", new_password, user_id)
            flash("Password changed successfully", "success")
            return redirect("/")
        except ValueError:
            error = "unexpected error"
            return render_template("change_password.html", error=error)
    else:
        return render_template("change_password.html")


@app.route("/add_balance", methods=["GET", "POST"])
@login_required
def add_balance():
    if request.method == "POST":
        digit = request.form.get("add")

        user_id = session["user_id"]

        if not digit:
            error = "Enter sum"
            return render_template("add_balance.html", error=error)

        try:
            digit = int(digit)
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", digit, user_id)
            flash("Update successful!", "success")
            return redirect("/")
        except ValueError:
            error = "Enter valid sum"
            return render_template("add_balance.html", error=error)
    else:
        return render_template("add_balance.html")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete_account():

    if request.method == "POST":
        user_id = session["user_id"]

        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure passwords were submitted
        if not password:
            error = "Enter password"
            return render_template("delete.html", error=error)
        if not confirmation:
            error = "Confirm the password"
            return render_template("delete.html", error=error)

        hash = db.execute("SELECT hash FROM users WHERE id = ?", user_id)[0]['hash']

        # Check if passwords are legit
        if not check_password_hash(hash, password):
            error = "Entered password is not valid"
            return render_template("delete.html", error=error)
        if not check_password_hash(hash, confirmation):
            error = "Entered confirmation is not valid"
            return render_template("delete.html", error=error)

        # Check if passwords match
        if password != confirmation:
            error = "Passwords do not match"
            return render_template("delete.html", error=error)

        db.execute("DROP TABLE IF EXISTS transactions_?", user_id)
        db.execute("DROP TABLE IF EXISTS history_?", user_id)
        db.execute("DELETE FROM users WHERE id = ?", user_id)

        flash("Account deleted successfully", "success")
        return redirect("/register")
    else:
        return render_template("delete.html")
