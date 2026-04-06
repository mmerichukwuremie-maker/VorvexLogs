from flask import Flask
from threading import Thread
import sqlite3

app = Flask('')

@app.route('/')
def home():
    conn = sqlite3.connect('transactions.db')
    c = conn.cursor()

    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()

    html = "<h1>Vornex Dashboard</h1><table border=1>"
    html += "<tr><th>ID</th><th>Type</th><th>Amount</th><th>From</th><th>To</th><th>Time</th></tr>"

    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]} {r[3]}</td><td>{r[5]}</td><td>{r[6]}</td><td>{r[7]}</td></tr>"

    html += "</table>"

    conn.close()
    return html

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
