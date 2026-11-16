from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "abc123"


def get_db():
    return sqlite3.connect("database.db")


def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        amount REAL,
        date TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS subscriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        amount REAL,
        due_date TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        rating INTEGER,
        message TEXT,
        date TEXT
    )""")

    con.commit()
    con.close()



init_db()


# ================= HOME PAGE =================
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")





# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        con = get_db()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            (user, pw, "user")
        )
        con.commit()
        con.close()

        flash("Account created successfully. Please login.", "success")
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        con = get_db()
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (user, pw)
        )
        data = cur.fetchone()
        con.close()

        if data:
            session["user_id"] = data[0]
            session["username"] = data[1]
            session["role"] = data[3]

            flash("Login successful", "success")

            if data[3] == "admin":
                return redirect("/admin")

            return redirect("/dashboard")

        flash("Invalid username or password", "danger")

    return render_template("login.html")


# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/login")

    con = get_db()
    cur = con.cursor()

    users = cur.execute("SELECT * FROM users").fetchall()
    total_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_expenses = cur.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    con.close()

    return render_template(
        "admin_dashboard.html",
        users=users,
        total_users=total_users,
        total_expenses=total_expenses
    )


# ================= USER DASHBOARD =================
@app.route("/dashboard")

def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    uid = session["user_id"]

    con = get_db()
    cur = con.cursor()

    # ---------- EXPENSE SUMMARY ----------
    total_spent = cur.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id=?",
        (uid,)
    ).fetchone()[0] or 0

    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    month_str = datetime.now().strftime("%Y-%m")

    daily_expense = cur.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id=? AND date=?",
        (uid, today_str)
    ).fetchone()[0] or 0

    monthly_expense = cur.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id=? AND strftime('%Y-%m', date)=?",
        (uid, month_str)
    ).fetchone()[0] or 0

    category_expenses = cur.execute(
        "SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category",
        (uid,)
    ).fetchall()

    recent_expenses = cur.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC LIMIT 10",
        (uid,)
    ).fetchall()

    # ---------- SUBSCRIPTION REMINDERS ----------
    next_week = today + timedelta(days=7)
    next_week_str = next_week.strftime("%Y-%m-%d")

    due_today = cur.execute(
        "SELECT name, amount, due_date FROM subscriptions WHERE user_id=? AND due_date=?",
        (uid, today_str)
    ).fetchall()

    upcoming = cur.execute(
        "SELECT name, amount, due_date FROM subscriptions WHERE user_id=? AND due_date>? AND due_date<=?",
        (uid, today_str, next_week_str)
    ).fetchall()

    con.close()

    # ---------- SHOW NOTIFICATIONS ----------
    if due_today:
        flash(f"{len(due_today)} subscription(s) due TODAY!", "danger")

    if upcoming:
        flash(f"{len(upcoming)} subscription(s) due within the next 7 days", "warning")

    total_savings = 5000  # static example

    return render_template(
        "user_dashboard.html",
        total_spent=total_spent,
        total_savings=total_savings,
        daily_expense=daily_expense,
        monthly_expense=monthly_expense,
        category_expenses=category_expenses,
        recent_expenses=recent_expenses,
        due_today=due_today,
        upcoming=upcoming
    )


# ================= ADD EXPENSE =================
@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        uid = session["user_id"]
        category = request.form["category"]
        amount = request.form["amount"]
        date_today = datetime.now().strftime("%Y-%m-%d")

        con = get_db()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO expenses(user_id,category,amount,date) VALUES(?,?,?,?)",
            (uid, category, amount, date_today)
        )
        con.commit()
        con.close()

        flash("Expense added successfully", "success")
        return redirect("/dashboard")

    return render_template("add_expense.html")


# ================= SUBSCRIPTIONS =================
@app.route("/subscriptions", methods=["GET", "POST"])
def subscriptions():
    if "user_id" not in session:
        return redirect("/login")

    uid = session["user_id"]

    con = get_db()
    cur = con.cursor()

    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        date = request.form["due"]

        cur.execute(
            "INSERT INTO subscriptions(user_id,name,amount,due_date) VALUES(?,?,?,?)",
            (uid, name, amount, date)
        )
        con.commit()

        flash("Subscription added successfully", "success")

    subs = cur.execute(
        "SELECT * FROM subscriptions WHERE user_id=?",
        (uid,)
    ).fetchall()

    con.close()

    return render_template("subscriptions.html", subs=subs)


 
@app.route("/feedback", methods=["GET","POST"])
def feedback():
    if "user_id" not in session:
        return redirect("/login")

    uid = session["user_id"]

    con = get_db()
    cur = con.cursor()

    if request.method == "POST":
        rating = request.form["rating"]
        message = request.form["message"]

        cur.execute(
            "INSERT INTO feedback(user_id,rating,message,date) VALUES(?,?,?,?)",
            (uid, rating, message, datetime.now().date())
        )
        con.commit()
        con.close()

        flash("Thank you for your feedback!", "success")
        return redirect("/dashboard")

    # Show last feedback submitted by user
    fb = cur.execute(
        "SELECT rating,message,date FROM feedback WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (uid,)
    ).fetchall()

    con.close()

    return render_template("feedback.html", feedback_list=fb)   


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(debug=True)
