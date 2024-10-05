from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from helpers import apology, lookup, usd

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


def check_funds(user_cash, total_price):
    return user_cash >= total_price


def update_balance(user_id, new_balance):
    db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, user_id)


def validate_inputs(symbol, shares):
    if not symbol or not lookup(symbol):
        return "Invalid symbol"
    if not shares or '/' in shares or not shares.isdigit() or float(shares) < 1:
        return "Invalid number of shares"
    return None


def create_transactions(user_id):
    db.execute("""
        CREATE TABLE IF NOT EXISTS transactions_? (
            symbol TEXT NOT NULL,
            shares NUMERIC NOT NULL,
            first_purchase TIMESTAMP DEFAULT (datetime('now', '+2 hours')),
            last_update TIMESTAMP DEFAULT (datetime('now', '+2 hours')),
            PRIMARY KEY (symbol)
        )
    """, user_id)


def io_transactions(user_id, symbol, shares):
    db.execute("""
        INSERT INTO transactions_? (symbol, shares)
        VALUES (?, ?)
        ON CONFLICT(symbol) DO UPDATE SET shares = shares + ?, last_update = CURRENT_TIMESTAMP
    """, user_id, symbol, shares, shares)
