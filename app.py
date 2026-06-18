from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "123456"

# 建立資料庫（只會第一次建立）
def init_db():
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS expense (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            category TEXT,
            date TEXT,
            note TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    # 取得所有資料
    c.execute(
        "SELECT * FROM expense WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    )
    data = c.fetchall()

    # 計算總支出
    c.execute(
        "SELECT SUM(amount) FROM expense WHERE user_id=?",
        (session["user_id"],)
    )
    total = c.fetchone()[0]

    if total is None:
        total = 0

    # 分類統計
    c.execute("""
        SELECT category, SUM(amount)
        FROM expense
        WHERE user_id=?
        GROUP BY category
    """, (session["user_id"],))
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
    if "user" not in session:
        return redirect("/login")
    amount = request.form['amount']
    category = request.form['category']
    date = request.form['date']
    note = request.form['note']

    conn = sqlite3.connect('expense.db')
    c = conn.cursor()

    user_id = session["user_id"]

    c.execute("""
        INSERT INTO expense (user_id, amount, category, date, note)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, category, date, note))

    conn.commit()
    conn.close()

    return redirect('/')

@app.route("/delete/<int:id>")
def delete(id):
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute(
        "DELETE FROM expense WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/edit/<int:id>")
def edit(id):
    if "user" not in session:
        return redirect("/login")
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute(
        "SELECT * FROM expense WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )
    row = c.fetchone()

    conn.close()

    return render_template("edit.html", row=row)

@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    if "user" not in session:
        return redirect("/login")
    amount = request.form["amount"]
    category = request.form["category"]
    date = request.form["date"]
    note = request.form["note"]

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("""
        UPDATE expense
        SET amount=?, category=?, date=?, note=?
        WHERE id=? AND user_id=?
        """, (
            amount,
            category,
            date,
            note,
            id,
            session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("expense.db")
        c = conn.cursor()

        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, password))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("expense.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username, password))

        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            session["user_id"] = user[0]

            return redirect("/")
        else:
            return "登入失敗"

    return render_template("login.html")
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)