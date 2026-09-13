import os
import uuid
from datetime import datetime, date
from calendar import month_name

from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy import extract

from extensions import db
from models.expense import Expense
from services.ocr_service import extract_text, OCRError
from services.expense_parser import parse_receipt_text, CATEGORIES

expense_bp = Blueprint("expenses", __name__)


@expense_bp.before_request
def require_login():
    if current_user.is_authenticated:
        return None
    if request.path == "/":
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required."}), 401
    return current_app.login_manager.unauthorized()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE_MB = 8


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Page routes (server-rendered templates)
# ---------------------------------------------------------------------------

@expense_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("dashboard.html")
    return render_template("index.html")


@expense_bp.route("/add")
def add_expense_page():
    return render_template("add_expense.html", categories=CATEGORIES)


@expense_bp.route("/expenses-page")
def expenses_page():
    return render_template("expenses.html", categories=CATEGORIES)


@expense_bp.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# CRUD API
# ---------------------------------------------------------------------------

@expense_bp.route("/api/expenses", methods=["GET"])
def get_expenses():
    query = Expense.query.filter(Expense.user_id == current_user.id)

    category = request.args.get("category")
    if category and category != "All":
        query = query.filter(Expense.category == category)

    month = request.args.get("month")  # 1-12
    if month:
        try:
            query = query.filter(extract("month", Expense.date) == int(month))
        except ValueError:
            pass

    year = request.args.get("year")
    if year:
        try:
            query = query.filter(extract("year", Expense.date) == int(year))
        except ValueError:
            pass

    search = request.args.get("search")
    if search:
        query = query.filter(Expense.merchant.ilike(f"%{search}%"))

    sort = request.args.get("sort", "date_desc")
    if sort == "amount_asc":
        query = query.order_by(Expense.amount.asc())
    elif sort == "amount_desc":
        query = query.order_by(Expense.amount.desc())
    elif sort == "date_asc":
        query = query.order_by(Expense.date.asc())
    else:
        query = query.order_by(Expense.date.desc())

    expenses = query.all()
    return jsonify([e.to_dict() for e in expenses])


@expense_bp.route("/api/expenses/<int:expense_id>", methods=["GET"])
def get_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    return jsonify(expense.to_dict())


@expense_bp.route("/api/expenses", methods=["POST"])
def create_expense():
    data = request.get_json(silent=True) or request.form

    if not data or "amount" not in data or not str(data.get("amount")).strip():
        return jsonify({"error": "Amount could not be detected. Please enter the amount manually."}), 400

    try:
        amount = float(data["amount"])
    except (TypeError, ValueError):
        return jsonify({"error": "Amount must be a valid number."}), 400

    date_str = data.get("date")
    try:
        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format."}), 400

    expense = Expense(
        amount=amount,
        category=data.get("category") or "Other",
        merchant=data.get("merchant"),
        date=expense_date,
        description=data.get("description"),
        receipt_image=data.get("receipt_image"),
        user_id=current_user.id,
    )

    try:
        db.session.add(expense)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Something went wrong while saving your expense. Please try again."}), 500

    return jsonify(expense.to_dict()), 201


@expense_bp.route("/api/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or request.form

    if "amount" in data and str(data.get("amount")).strip():
        try:
            expense.amount = float(data["amount"])
        except (TypeError, ValueError):
            return jsonify({"error": "Amount must be a valid number."}), 400

    if "category" in data:
        expense.category = data.get("category") or expense.category
    if "merchant" in data:
        expense.merchant = data.get("merchant")
    if "description" in data:
        expense.description = data.get("description")
    if data.get("date"):
        try:
            expense.date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format."}), 400

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Something went wrong while updating your expense. Please try again."}), 500

    return jsonify(expense.to_dict())


@expense_bp.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(expense)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Something went wrong while deleting your expense. Please try again."}), 500
    return jsonify({"deleted": True, "id": expense_id})


# ---------------------------------------------------------------------------
# Receipt upload + OCR
# ---------------------------------------------------------------------------

@expense_bp.route("/api/receipts/extract", methods=["POST"])
def extract_receipt():
    if "receipt" not in request.files:
        return jsonify({"error": "No file uploaded. Please choose a receipt image."}), 400

    file = request.files["receipt"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Please upload a JPG, JPEG, or PNG image."}), 400

    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        return jsonify({"error": f"Image is too large. Please upload a file under {MAX_FILE_SIZE_MB}MB."}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, unique_name)
    file.save(save_path)

    try:
        raw_text = extract_text(save_path)
    except OCRError as e:
        return jsonify({"error": str(e), "receipt_image": unique_name}), 422
    except Exception:
        return jsonify({"error": "We couldn't process this receipt. Please try a clearer image or enter the expense manually."}), 500

    parsed = parse_receipt_text(raw_text)
    parsed["receipt_image"] = unique_name

    if parsed.get("amount") is None:
        parsed["warning"] = "Amount could not be detected. Please enter the amount manually."

    return jsonify(parsed)


# ---------------------------------------------------------------------------
# Dashboard summary + chart data
# ---------------------------------------------------------------------------

@expense_bp.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    total = sum(e.amount for e in expenses)

    today = date.today()
    this_month_total = sum(
        e.amount for e in expenses if e.date and e.date.month == today.month and e.date.year == today.year
    )

    category_totals = {}
    for e in expenses:
        category_totals[e.category] = category_totals.get(e.category, 0) + e.amount

    highest_category = max(category_totals, key=category_totals.get) if category_totals else None

    return jsonify({
        "total_expenses": round(total, 2),
        "this_month": round(this_month_total, 2),
        "highest_category": highest_category,
        "number_of_expenses": len(expenses),
        "category_totals": {k: round(v, 2) for k, v in category_totals.items()},
    })


@expense_bp.route("/api/dashboard/monthly", methods=["GET"])
def dashboard_monthly():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    monthly_totals = {}
    for e in expenses:
        if not e.date:
            continue
        key = f"{e.date.year}-{e.date.month:02d}"
        monthly_totals[key] = monthly_totals.get(key, 0) + e.amount

    sorted_keys = sorted(monthly_totals.keys())
    labels = []
    values = []
    for key in sorted_keys:
        year, month = key.split("-")
        labels.append(f"{month_name[int(month)][:3]} {year}")
        values.append(round(monthly_totals[key], 2))

    return jsonify({"labels": labels, "values": values})


@expense_bp.route("/api/dashboard/recent", methods=["GET"])
def dashboard_recent():
    limit = int(request.args.get("limit", 5))
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
        Expense.date.desc(), Expense.created_at.desc()
    ).limit(limit).all()
    return jsonify([e.to_dict() for e in expenses])


@expense_bp.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(CATEGORIES)
