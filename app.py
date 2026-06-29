from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import pandas as pd

app = Flask(__name__)
app.secret_key = "123456"

# 建立資料庫
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            month TEXT,
            budget_amount INTEGER
        )
        """)

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    keyword = request.args.get("keyword")
    category = request.args.get("category")
    sort = request.args.get("sort")

    where_clause = "WHERE user_id=?"
    params = [session["user_id"]]

    if start_date:
        where_clause += " AND date >= ?"
        params.append(start_date)
    if end_date:
        where_clause += " AND date <= ?"
        params.append(end_date)
    # 關鍵字搜尋（搜尋備註）
    if keyword:
        where_clause += " AND note LIKE ?"
        params.append(f"%{keyword}%")
    if category and category != "全部":
        where_clause += " AND category=?"
        params.append(category)
    order_clause = "ORDER BY id DESC"
    if sort == "amount_desc":
        order_clause = "ORDER BY amount DESC"

    elif sort == "amount_asc":
        order_clause = "ORDER BY amount ASC"

    elif sort == "date_asc":
        order_clause = "ORDER BY date ASC"

    elif sort == "date_desc":
        order_clause = "ORDER BY date DESC"
    
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    # 取得所有資料
    query = f"""
    SELECT *
    FROM expense
    {where_clause}
    {order_clause}
    """
    c.execute(query, params)
    data = c.fetchall()

    # 計算總支出
    query = f"""
    SELECT SUM(amount)
    FROM expense
    {where_clause}
    """
    c.execute(query, params)
    total = c.fetchone()[0]

    if total is None:
        total = 0

    # 分類統計
    query = f"""
    SELECT category, SUM(amount)
    FROM expense
    {where_clause}
    GROUP BY category
    """
    c.execute(query, params)
    category_stats = c.fetchall()

    c.execute(f"""
    SELECT category, SUM(amount) as total
    FROM expense
    {where_clause}
    GROUP BY category
    ORDER BY total DESC
    LIMIT 3
    """, params)

    top_categories = c.fetchall()

    query = f"""
    SELECT
        substr(date,1,7),
        SUM(amount)
    FROM expense
    {where_clause}
    GROUP BY substr(date,1,7)
    ORDER BY substr(date,1,7)
    """
    c.execute(query, params)
    monthly_stats = c.fetchall()

    query = f"""
    SELECT COUNT(*)
    FROM expense
    {where_clause}
    """
    c.execute(query, params)
    expense_count = c.fetchone()[0]

    query = f"""
    SELECT AVG(amount)
    FROM expense
    {where_clause}
    """
    c.execute(query, params)
    avg_amount = c.fetchone()[0]

    if avg_amount is None:
        avg_amount = 0
    else:
        avg_amount = round(avg_amount, 2)

    query = f"""
    SELECT category, SUM(amount) as total
    FROM expense
    {where_clause}
    GROUP BY category
    ORDER BY total DESC
    LIMIT 1
    """
    c.execute(query, params)
    top_category = c.fetchone()
    if top_category:
        top_category = top_category[0]
    else:
        top_category = "無資料"
        
    query = f"""
    SELECT
        substr(date,1,7) as month,
        SUM(amount) as total
    FROM expense
    {where_clause}
    GROUP BY month
    ORDER BY total DESC
    LIMIT 1
    """
    c.execute(query, params)
    top_month = c.fetchone()
    if top_month:
        top_month = top_month[0]
    else:
        top_month = "無資料"

    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")
    c.execute("""
    SELECT budget_amount
    FROM budget
    WHERE user_id=?
    AND month=?
    ORDER BY id DESC
    LIMIT 1
    """, (
        session["user_id"],
        current_month
    ))
    budget = c.fetchone()
    if budget:
        budget = budget[0]
    else:
        budget = 0 
    if budget > 0:
        budget_percent = min(
            round(total / budget * 100),
            100
        )
    else:
        budget_percent = 0
    
    conn.close()

    return render_template(
        "index.html",
        data=data,
        total=total,
        category_stats=category_stats,
        monthly_stats=monthly_stats,
        expense_count=expense_count,
        avg_amount=avg_amount,
        top_category=top_category,
        top_month=top_month,
        top_categories=top_categories,
        start_date=start_date,
        end_date=end_date,
        budget=budget,
        budget_percent=budget_percent,
        keyword=keyword,
        category=category,
        sort=sort,
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

@app.route("/export")
def export():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("expense.db")

    query = """
    SELECT
        amount AS 金額,
        category AS 類別,
        date AS 日期,
        note AS 備註
    FROM expense
    WHERE user_id=?
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(session["user_id"],)
    )

    conn.close()

    filename = f"{session['user']}_expenses.csv"

    df.to_csv(
        filename,
        index=False,
        encoding="utf-8-sig"
    )

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/budget", methods=["GET", "POST"])
def budget():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        month = request.form["month"]
        amount = request.form["amount"]

        conn = sqlite3.connect("expense.db")
        c = conn.cursor()

        c.execute("""
        INSERT INTO budget
        (user_id, month, budget_amount)
        VALUES (?, ?, ?)
        """, (
            session["user_id"],
            month,
            amount
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("budget.html")

if __name__ == "__main__":
    app.run(debug=True)