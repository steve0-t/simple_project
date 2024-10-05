from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from helpers import apology, lookup, usd

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


def create_history(user_id):
    db.execute("""
        CREATE TABLE IF NOT EXISTS history_? (
            transaction_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price NUMERIC NOT NULL,
            amount NUMERIC NOT NULL,
            date_and_time TIMESTAMP DEFAULT (datetime('now', '+2 hours'))
        )
    """, user_id)


def io_history(user_id, transaction_type, symbol, price, amount):
    db.execute("""
        INSERT INTO history_? (transaction_type, symbol, price, amount)
        VALUES (?, ?, ?, ?)
    """, user_id, transaction_type, symbol, price, amount)
