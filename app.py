from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key"

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    # USERS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TEXT
        )
    ''')

    # TICKETS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            module TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            resolved_at TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()


# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")
            else:
                return redirect("/dashboard")
        else:
            return "Invalid Credentials"

    return render_template("login.html")

# SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name,email,password,role,created_at) VALUES (?,?,?,?,?)",
                (
                    name,
                    email,
                    password,
                    role,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            conn.commit()
            conn.close()

            return redirect("/")
        except:
            return "User already exists!"

    return render_template("signup.html")

# USER DASHBOARD
@app.route("/dashboard")
def dashboard():
    conn = get_db()
    tickets = conn.execute(
        "SELECT * FROM tickets WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", tickets=tickets)

# RAISE TICKET
@app.route("/raise", methods=["GET", "POST"])
def raise_ticket():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        module = request.form["module"]
        priority = request.form["priority"]

        conn = get_db()
        conn.execute('''
            INSERT INTO tickets 
            (title, description, module, priority, created_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            title,
            description,
            module,
            priority,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("raise_ticket.html")

# ADMIN DASHBOARD
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/")

    conn = get_db()
    tickets = conn.execute("SELECT * FROM tickets").fetchall()
    conn.close()

    total = len(tickets)
    open_count = len([t for t in tickets if t["status"] == "Open"])
    resolved_count = len([t for t in tickets if t["status"] == "Resolved"])
    high_priority = len([t for t in tickets if t["priority"] == "High"])

    ticket_list = []

    for ticket in tickets:
        sla = None

        if ticket["resolved_at"]:
            created = datetime.strptime(ticket["created_at"], "%Y-%m-%d %H:%M:%S")
            resolved = datetime.strptime(ticket["resolved_at"], "%Y-%m-%d %H:%M:%S")
            diff = resolved - created
            sla = round(diff.total_seconds() / 3600, 2)

        ticket_list.append({
            "id": ticket["id"],
            "title": ticket["title"],
            "module": ticket["module"],
            "priority": ticket["priority"],
            "status": ticket["status"],
            "created_at": ticket["created_at"],
            "sla": sla
        })

    return render_template(
        "admin_dashboard.html",
        tickets=ticket_list,
        total=total,
        open_count=open_count,
        resolved_count=resolved_count,
        high_priority=high_priority
    )

# RESOLVE TICKET
@app.route("/resolve/<int:id>")
def resolve_ticket(id):
    conn = get_db()
    conn.execute('''
        UPDATE tickets
        SET status=?, resolved_at=?
        WHERE id=?
    ''', (
        "Resolved",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        id
    ))
    conn.commit()
    conn.close()

    return redirect("/admin")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)