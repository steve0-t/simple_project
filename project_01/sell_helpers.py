from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from helpers import apology, lookup, usd

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


def check_inputs(selected_stock, shares):
    if not selected_stock:
        return "Must select stock"
    if not shares:
        return "Must select shares"
    return None

def io_sells(shares, hold, user_id, selected_stock):

    # Determine status of shares after selling, execute proper command
    if (shares - hold == 0):
        db.execute("DELETE FROM transactions_? WHERE symbol = ?", user_id, selected_stock)
    else:
        db.execute("UPDATE transactions_? SET shares = shares - ? WHERE symbol = ?", user_id, shares, selected_stock)

    # Update user's balance
    price = lookup(selected_stock)['price'] * shares
    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", price, user_id)
