import os
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import inspect, text

from extensions import db, login_manager
from models.user import User
from routes.expense_routes import expense_bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def create_app():
    app = Flask(__name__)

    database_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB hard cap
    app.config["TESSERACT_CMD"] = os.environ.get("TESSERACT_CMD")

    db.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(expense_bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("expenses.index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = db.session.scalar(db.select(User).where(User.username == username))
            if user and user.check_password(password):
                login_user(user)
                return redirect(request.args.get("next") or url_for("expenses.index"))
            return render_template("login.html", error="Invalid username or password."), 401
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("expenses.dashboard_page"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if len(username) < 3:
                return render_template("register.html", error="Username must be at least 3 characters."), 400
            if len(password) < 8:
                return render_template("register.html", error="Password must be at least 8 characters."), 400
            if password != confirm_password:
                return render_template("register.html", error="Passwords do not match."), 400
            if db.session.scalar(db.select(User).where(User.username == username)):
                return render_template("register.html", error="That username is already registered."), 409

            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("expenses.dashboard_page"))

        return render_template("register.html")

    @app.post("/logout")
    def logout():
        logout_user()
        return redirect(url_for("login"))

    with app.app_context():
        from models.expense import Expense  # noqa: F401
        db.create_all()

        expense_columns = {column["name"] for column in inspect(db.engine).get_columns("expenses")}
        if "user_id" not in expense_columns:
            db.session.execute(text("ALTER TABLE expenses ADD COLUMN user_id INTEGER"))
            db.session.commit()

        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if admin_username and admin_password and not db.session.scalar(
            db.select(User).where(User.username == admin_username)
        ):
            admin = User(username=admin_username)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()

        if admin_username:
            admin = db.session.scalar(db.select(User).where(User.username == admin_username))
            if admin:
                db.session.execute(
                    text("UPDATE expenses SET user_id = :user_id WHERE user_id IS NULL"),
                    {"user_id": admin.id},
                )
                db.session.commit()

    # Friendly error handlers (Phase 13 — no raw Python/SQL errors to the user)
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "Uploaded file is too large."}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Something went wrong on our end. Please try again."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
