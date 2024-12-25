from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import shutil
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from bcrypt import hashpw, gensalt, checkpw
import uuid
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Получаем путь к текущей директории

# Configure allowed file extensions and upload folder
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'local_database.db')}"  # Локальная БД
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Отключаем уведомления
app.secret_key = "your_secret_key"

db = SQLAlchemy(app)

BACKUP_DIR = os.path.join(BASE_DIR, "backups")  # Директория для резервных копий

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(1), default='u')  # Тип пользователя: u - обычный, a - админ

    def set_password(self, password):
        self.password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

    def check_password(self, password):
        return checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

class Apartment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    rooms = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    images = db.Column(db.PickleType, default=[])  # Store images as a list of filenames (or paths)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def backup_database():
    # Убедимся, что директория для бэкапов существует
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    # Формируем имя файла бэкапа с текущей датой и временем
    backup_file = os.path.join(
        BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )

    # Копируем базу данных
    try:
        shutil.copy(app.config['SQLALCHEMY_DATABASE_URI'][10:], backup_file)
        print(f"Бэкап базы данных создан: {backup_file}")
    except Exception as e:
        print(f"Ошибка создания бэкапа: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Запускаем функцию бэкапа каждые 24 часа
    scheduler.add_job(backup_database, 'interval', minutes=30)
    scheduler.start()
    print("Планировщик задач запущен.")

# Маршруты
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
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

        if User.query.filter_by(username=username).first():
            flash("Пользователь с таким логином уже существует!", "error")
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("Регистрация прошла успешно! Войдите в систему.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/", methods=["GET", "POST"])
def dashboard():
    username = session.get('username')
    user = None

    if username:
        # Попробуем найти пользователя в базе данных, если он авторизован
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Пользователь не найден!", "error")
            session.pop('username', None)  # Удаляем невалидную сессию

    # Получаем данные о квартирах
    apartments_rent = Apartment.query.filter_by(type='rent').all()
    apartments_buy = Apartment.query.filter_by(type='buy').all()

    # Передаем тип пользователя (если он есть) или None
    user_type = user.type if user else None

    return render_template(
        "dashboard.html",
        username=username,
        user_type=user_type,
        apartments_rent=apartments_rent,
        apartments_buy=apartments_buy
    )


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    username = session.get('username')

    if not username:
        flash("Необходимо войти в систему!", "error")
        return redirect(url_for("login"))

    user = User.query.filter_by(username=username).first()
    if not user or user.type != 'a':
        flash("Доступ запрещен!", "error")
        return redirect(url_for('dashboard', username=username))

    apartments = Apartment.query.all()
    return render_template("admin_panel.html", apartments=apartments)


@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_apartment(id):
    apartment = Apartment.query.get_or_404(id)

    # Удаление связанных фотографий
    if apartment.images:  # Проверяем, есть ли изображения
        for image in apartment.images:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)  # Удаляем файл
                except Exception as e:
                    flash(f"Ошибка удаления файла {image}: {e}", "error")

    # Удаление записи из базы данных
    db.session.delete(apartment)
    db.session.commit()
    flash("Квартира и связанные фотографии успешно удалены!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def edit_apartment(id):
    username = session.get('username')

    if not username:
        flash("Необходимо войти в систему!", "error")
        return redirect(url_for("login"))

    user = User.query.filter_by(username=username).first()
    if not user or user.type != 'a':
        flash("Доступ запрещен!", "error")
        return redirect(url_for('dashboard'))

    apartment = Apartment.query.get_or_404(id)

    if request.method == "POST":
        apartment.address = request.form.get("address")
        apartment.rooms = request.form.get("rooms")
        apartment.price = request.form.get("price")
        apartment.description = request.form.get("description")
        apartment.title = request.form.get("title")
        apartment.type = request.form.get("type")
        db.session.commit()
        flash("Квартира успешно обновлена!", "success")
        return redirect(url_for("admin_panel"))

    return render_template("edit_apartment.html", apartment=apartment)

@app.route("/admin/add", methods=["GET", "POST"])
def add_apartment():
    username = session.get('username')

    if not username:
        flash("Необходимо войти в систему!", "error")
        return redirect(url_for("login"))

    user = User.query.filter_by(username=username).first()
    if not user or user.type != 'a':
        flash("Доступ запрещен!", "error")
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        new_apartment = Apartment(
            address=request.form.get("address"),
            rooms=request.form.get("rooms"),
            price=request.form.get("price"),
            description=request.form.get("description"),
            title=request.form.get("title"),
            type=request.form.get("type")
        )

        # Handle image uploads
        image_files = request.files.getlist('images')  # Get the list of files
        image_paths = []

        for image in image_files:
            if len(image_paths) >= 6:
                break  # Прерываем цикл, если уже сохранено 6 файлов

            if image and allowed_file(image.filename):
                # Создаём уникальное имя файла
                ext = os.path.splitext(image.filename)[1]  # Получаем расширение файла
                unique_filename = f"{uuid.uuid4().hex}{ext}"  # Генерируем уникальное имя
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

                # Сохраняем файл
                image.save(filepath)
                image_paths.append(unique_filename)  # Сохраняем только имя файла

        # Save image paths to the database (up to 6 images)
        new_apartment.images = image_paths[:6]  # Limit to 6 images
        db.session.add(new_apartment)
        db.session.commit()

        flash("Квартира успешно добавлена!", "success")
        return redirect(url_for("admin_panel"))

    return render_template("add_apartment.html")

@app.route("/logout")
def logout():
    session.pop('username', None)  # Удаляем пользователя из сессии
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("dashboard"))

@app.route("/search", methods=["GET", "POST"])
def search():
    filters = {}
    if request.method == "POST":
        filters["type"] = request.form.get("type")
        filters["rooms"] = request.form.get("rooms")
        filters["price_min"] = request.form.get("price_min")
        filters["price_max"] = request.form.get("price_max")

    query = Apartment.query
    if filters.get("type"):
        query = query.filter_by(type=filters["type"])
    if filters.get("rooms"):
        query = query.filter_by(rooms=filters["rooms"])
    if filters.get("price_min"):
        query = query.filter(Apartment.price >= float(filters["price_min"]))
    if filters.get("price_max"):
        query = query.filter(Apartment.price <= float(filters["price_max"]))

    apartments = query.all()
    return render_template("search_results.html", apartments=apartments)

@app.route("/apartment/<int:apartment_id>")
def apartment_detail(apartment_id):
    apartment = Apartment.query.get_or_404(apartment_id)
    return render_template("apartment_detail.html", apartment=apartment)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    start_scheduler()
    app.run(debug=True)