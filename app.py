from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "expenses.db")

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_pw = generate_password_hash(password)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists!"
        conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        else:
            return "Invalid username or password!"
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    
    cursor.execute("SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC", (user_id,))
    expenses = cursor.fetchall()

    
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (user_id,))
    entries = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(amount) FROM expenses
        WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') AND user_id=?
    """, (user_id,))
    monthly_total = cursor.fetchone()[0] or 0

   
    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id=?
        GROUP BY category
    """, (user_id,))
    category_data = cursor.fetchall()
    categories = [row[0] for row in category_data] if category_data else []
    amounts = [row[1] for row in category_data] if category_data else []

    conn.close()
    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        entries=entries,
        monthly_total=monthly_total,
        categories=categories,
        amounts=amounts
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    user_id = session["user_id"]
    title = request.form["title"]
    amount = float(request.form["amount"])
    category = request.form["category"]
    type_value = request.form["type"]
    date = request.form["date"]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (title, amount, category, type, date, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (title, amount, category, type_value, date, user_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/delete/<int:id>")
@login_required
def delete(id):
    user_id = session["user_id"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (id, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    user_id = session["user_id"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        amount = float(request.form["amount"])
        category = request.form["category"]
        type_value = request.form["type"]
        date = request.form["date"]

        cursor.execute("""
            UPDATE expenses
            SET title=?, amount=?, category=?, type=?, date=?
            WHERE id=? AND user_id=?
        """, (title, amount, category, type_value, date, id, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    
    cursor.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (id, user_id))
    expense = cursor.fetchone()
    conn.close()
    return render_template("edit.html", expense=expense)




if __name__ == "__main__":
    app.run(debug=True)