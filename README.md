# Smart Expense Tracker (Receipt OCR)

SpendSense is a web-based expense management application that uses OCR to extract transaction details from receipt images and provides spending analytics through an interactive dashboard.

## Setup

```bash
pip install -r requirements.txt
```

Tesseract OCR must be installed on your system separately:
- Ubuntu/Debian: `sudo apt install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki and add it to PATH

For Windows, `TESSERACT_CMD` may be set to the full path of `tesseract.exe` if it
is not on `PATH`.

## Run

```bash
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

The first account is created from `ADMIN_USERNAME` and `ADMIN_PASSWORD` when the
application starts. Set both values before starting the server. Set a strong
`SECRET_KEY` for any non-local environment.

## Production deployment

PostgreSQL is selected with `DATABASE_URL` from the environment or a local
`.env` file; both `postgres://...` and
`postgresql://...` URLs are accepted. The PostgreSQL driver is included in
`requirements.txt`.

Example environment:

```text
DATABASE_URL=postgresql://user:password@host:5432/expense_tracker
SECRET_KEY=replace-with-a-long-random-value
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
```

Install dependencies and run behind a reverse proxy with:

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

To verify the Supabase connection directly, run `python main.py`. Never commit
`.env`; use a secret manager or deployment environment variables in production.

The deployment image or host must also install the Tesseract executable. The
current startup creates missing tables, but it does not migrate an existing
database schema; use a migration tool before applying future model changes.

## Project structure

- `app.py` — Flask app factory + entry point
- `extensions.py` — shared SQLAlchemy and login extensions
- `models/user.py` — login user model
- `models/expense.py` — Expense model
- `routes/expense_routes.py` — pages + REST API (CRUD, receipt OCR, dashboard data)
- `services/ocr_service.py` — OpenCV preprocessing + Tesseract text extraction
- `services/expense_parser.py` — regex/keyword based field + category extraction
- `templates/` — HTML pages (Bootstrap)
- `static/` — CSS and JS (vanilla JS + Chart.js)
- `uploads/` — saved receipt images

## What's implemented (Phases 1–11, 13–14 of the plan)

- Manual add / edit / delete expenses
- Receipt upload -> OpenCV preprocessing -> Tesseract OCR -> rule-based field
  extraction (merchant, amount, date, category) -> confirmation/edit screen -> save
- Dashboard: summary cards, category pie chart, monthly bar chart, recent expenses
- Filters: category, month, merchant search, sorting
- Friendly error handling for bad uploads, OCR failures, missing amounts, and
  server/DB errors

## Not included yet (by request)

- Phase 12 (optional AI categorization / AI spending insights) has been left out
  entirely. The rule-based `expense_parser.py` keyword map can be extended anytime
  without needing an LLM.

## Next steps if you want to keep going

- Phase 15 (UI polish): icons, tighter spacing/typography, better mobile layout
- More testing per Phase 14 (blurry receipts, missing totals, multiple items)
- Optionally add user accounts/login (currently single-user, no auth)
