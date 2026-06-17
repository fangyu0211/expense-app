from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# 建立資料庫（只會第一次建立）
def init_db():
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS expense (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount INTEGER,
            category TEXT,
            date TEXT,
            note TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    # 取得所有資料
    c.execute("SELECT * FROM expense ORDER BY id DESC")
    data = c.fetchall()

    # 計算總支出
    c.execute("SELECT SUM(amount) FROM expense")
    total = c.fetchone()[0]

    if total is None:
        total = 0

    # 分類統計
    c.execute("""
        SELECT category, SUM(amount)
        FROM expense
        GROUP BY category
    """)
    category_stats = c.fetchall()

    conn.close()

    return render_template(
        "index.html",
        data=data,
        total=total,
        category_stats=category_stats
    )

@app.route('/add', methods=['POST'])
def add():
    amount = request.form['amount']
    category = request.form['category']
    date = request.form['date']
    note = request.form['note']

    conn = sqlite3.connect('expense.db')
    c = conn.cursor()

    c.execute("""
        INSERT INTO expense (amount, category, date, note)
        VALUES (?, ?, ?, ?)
    """, (amount, category, date, note))

    conn.commit()
    conn.close()

    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)