from flask import Flask, render_template, request, flash, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

DATABASE = "users.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user["password"] == password:
            return redirect(url_for('dashboard', username=username))
        else:
            flash("Неверный логин или пароль!", "error")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Пароли не совпадают!", "error")
            return render_template("register.html")

        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            flash("Регистрация прошла успешно! Войдите в систему.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Пользователь с таким логином уже существует!", "error")

    return render_template("register.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    username = request.args.get("username", "Гость")

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    apartments_rent = conn.execute("SELECT * FROM apartments WHERE type = 'rent'").fetchall()
    apartments_buy = conn.execute("SELECT * FROM apartments WHERE type = 'buy'").fetchall()
    conn.close()

    if not user:
        flash("Пользователь не найден!", "error")
        return redirect(url_for("login"))

    user_type = user["type"]

    return render_template(
        "dashboard.html",
        username=username,
        user_type=user_type,
        apartments_rent=apartments_rent,
        apartments_buy=apartments_buy
    )

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    username = request.args.get("username", "Гость")

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

#    if not user or user["type"] != 'a':
#        flash("Доступ запрещен!", "error")
#        return redirect(url_for('dashboard', username=username))

    conn = get_db_connection()
    apartments = conn.execute("SELECT * FROM apartments").fetchall()
    conn.close()

    return render_template("admin_panel.html", apartments=apartments)

@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_apartment(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM apartments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Квартира успешно удалена!", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def edit_apartment(id):
    conn = get_db_connection()
    apartment = conn.execute("SELECT * FROM apartments WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        address = request.form.get("address")
        rooms = request.form.get("rooms")
        price = request.form.get("price")
        description = request.form.get("description")

        conn.execute(
            "UPDATE apartments SET address = ?, rooms = ?, price = ?, description = ? WHERE id = ?",
            (address, rooms, price, description, id)
        )
        conn.commit()
        conn.close()
        flash("Квартира успешно обновлена!", "success")
        return redirect(url_for("admin_panel"))

    conn.close()
    return render_template("edit_apartment.html", apartment=apartment)

@app.route("/admin/add", methods=["GET", "POST"])
def add_apartment():
    if request.method == "POST":
        address = request.form.get("address")
        rooms = request.form.get("rooms")
        price = request.form.get("price")
        description = request.form.get("description")

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO apartments (address, rooms, price, description) VALUES (?, ?, ?, ?)",
            (address, rooms, price, description)
        )
        conn.commit()
        conn.close()
        flash("Квартира успешно добавлена!", "success")
        return redirect(url_for("admin_panel"))

    return render_template("add_apartment.html")

if __name__ == "__main__":
    app.run(debug=True)
