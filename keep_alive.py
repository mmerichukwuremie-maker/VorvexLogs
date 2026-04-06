from flask import Flask, render_template
from threading import Thread
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    conn = sqlite3.connect('transactions.db')
    c = conn.cursor()

    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    transactions = c.fetchall()

    conn.close()

    return render_template("dashboard.html", transactions=transactions)

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
