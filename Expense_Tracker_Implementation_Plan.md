# Expense Tracker — Implementation Plan

## 1. Project Overview

Build a web-based Expense Tracker that allows users to:

- Add expenses manually.
- Upload a photo of a bill/receipt.
- Extract text from the receipt using OCR.
- Identify important fields such as merchant, amount, date, and category.
- Store expenses in a database.
- View, edit, and delete expenses.
- Analyze spending using charts.
- Optionally add an AI-based expense categorization feature later.

---

## 2. Technology Stack

### Frontend

- **HTML** — page structure and forms
- **CSS** — styling and responsive design
- **JavaScript** — frontend interactions and API requests
- **Chart.js** — expense charts
- **Bootstrap** — optional UI components and responsive layout

### Backend

- **Python** — main programming language
- **Flask** — web framework and REST API
- **SQLite** — database
- **SQLAlchemy** — database ORM

### Receipt Processing

- **Tesseract OCR** — extract text from receipt images
- **OpenCV** — preprocess images to improve OCR accuracy

### Optional AI

- An LLM can later be added to classify expenses when rule-based categorization is insufficient.

---

## 3. High-Level Architecture

```text
User
  |
  v
Frontend
HTML + CSS + JavaScript
  |
  | HTTP requests
  v
Flask Backend
  |
  +--------------------+
  |                    |
  v                    v
SQLite Database      Receipt Processor
                     |
                     +--> OpenCV
                     |
                     +--> Tesseract OCR
                     |
                     +--> Python field extraction
  |
  v
Expense Dashboard
  |
  v
Chart.js
```

---

# 4. Implementation Phases

## Phase 1 — Set Up the Project

### Create the project structure

```text
expense-tracker/
│
├── app.py
├── requirements.txt
├── database.db
│
├── models/
│   └── expense.py
│
├── routes/
│   └── expense_routes.py
│
├── services/
│   ├── ocr_service.py
│   └── expense_parser.py
│
├── templates/
│   ├── index.html
│   ├── add_expense.html
│   ├── expenses.html
│   └── dashboard.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
└── uploads/
```

### Install Python packages

```bash
pip install flask flask-sqlalchemy opencv-python pytesseract pillow
```

Save dependencies:

```bash
pip freeze > requirements.txt
```

---

# 5. Phase 2 — Create the Database

Create an `Expense` model.

Suggested fields:

```text
id
amount
category
merchant
date
description
receipt_image
created_at
```

Example database record:

```text
ID          : 1
Amount      : 300
Category    : Food
Merchant    : Cafe XYZ
Date        : 2026-09-13
Description : Coffee and sandwich
Receipt     : receipt_001.jpg
```

Use SQLAlchemy so Python code can interact with SQLite without writing large amounts of raw SQL.

---

# 6. Phase 3 — Build the Basic Frontend

Create a dashboard containing:

### Summary cards

```text
Total Expenses     ₹12,450
This Month         ₹4,320
Highest Category   Food
Number of Expenses 27
```

### Expense table

| Date | Merchant | Category | Amount | Action |
|---|---|---|---:|---|
| 13 Sep | Cafe XYZ | Food | ₹300 | Edit/Delete |
| 12 Sep | Uber | Travel | ₹250 | Edit/Delete |

### Buttons

- Add Expense
- Upload Receipt
- View Dashboard
- Filter Expenses

Keep the first version simple. Functionality is more important than visual complexity.

---

# 7. Phase 4 — Implement CRUD Operations

CRUD means:

- **Create** — add an expense
- **Read** — view expenses
- **Update** — edit an expense
- **Delete** — remove an expense

Create Flask routes such as:

```text
GET    /expenses
POST   /expenses
PUT    /expenses/<id>
DELETE /expenses/<id>
```

Also create a normal HTML form for manual expense entry.

---

# 8. Phase 5 — Receipt Upload

Add an upload form:

```text
Upload Receipt
[ Choose File ]

[ Extract Expense ]
```

The frontend sends the image to Flask using `multipart/form-data`.

Backend steps:

```text
Receive image
     ↓
Validate file type
     ↓
Save image temporarily
     ↓
Send image to OCR pipeline
```

Allow common image formats such as:

```text
.jpg
.jpeg
.png
```

Add basic file-size and file-type validation.

---

# 9. Phase 6 — Image Preprocessing with OpenCV

Receipt photos are not always clean.

Use OpenCV to improve the image before OCR.

Basic pipeline:

```text
Original Image
      ↓
Resize
      ↓
Convert to Grayscale
      ↓
Noise Reduction
      ↓
Thresholding
      ↓
Processed Image
```

The goal is to make text easier for Tesseract to recognize.

Do not overcomplicate this initially. Start with grayscale + thresholding and improve only if OCR accuracy is poor.

---

# 10. Phase 7 — OCR with Tesseract

Pass the processed receipt image to Tesseract.

Example OCR output:

```text
CAFE XYZ
13/09/2026

Coffee       120
Sandwich     180

TOTAL        300
```

Tesseract's job is only to convert the image into text.

It does **not** automatically understand that `300` is the expense amount.

That interpretation is the next step.

---

# 11. Phase 8 — Extract Expense Information

Create an `expense_parser.py` module.

Input:

```text
CAFE XYZ
13/09/2026
Coffee 120
Sandwich 180
TOTAL 300
```

Output:

```text
Merchant = Cafe XYZ
Date = 13/09/2026
Amount = 300
Category = Food
```

### Amount extraction

Search for patterns such as:

```text
TOTAL 300
Total: ₹300
Grand Total ₹300
Amount Due: ₹300
```

Use Python regular expressions to detect monetary values.

### Date extraction

Detect common date formats:

```text
13/09/2026
13-09-2026
13 Sep 2026
```

### Merchant extraction

Initially, use the first meaningful line or receipt-specific heuristics.

### Category extraction

Start with rule-based classification.

Example:

```text
Uber → Travel
Swiggy → Food
Restaurant → Food
Amazon → Shopping
Pharmacy → Medical
```

Keep the category list small initially:

```text
Food
Travel
Shopping
Bills
Entertainment
Medical
Education
Other
```

---

# 12. Phase 9 — Confirmation Screen

Do NOT immediately save OCR results.

Show the user what the system extracted:

```text
--------------------------------
Review Expense
--------------------------------

Merchant : Cafe XYZ
Amount   : ₹300
Date     : 13/09/2026
Category : Food

[ Edit ]       [ Save Expense ]
--------------------------------
```

This is important because OCR can make mistakes.

The user can correct the fields before saving.

---

# 13. Phase 10 — Dashboard and Charts

Use Chart.js.

Create:

### Category-wise spending

Example:

```text
Food          ₹4,200
Travel        ₹2,100
Shopping      ₹3,500
Bills         ₹2,650
```

Display this as a **pie chart**.

### Monthly spending

Display monthly totals as a **bar or line chart**.

Example:

```text
June       ₹8,200
July       ₹9,500
August    ₹11,200
September  ₹4,320
```

### Recent expenses

Show the latest transactions below the charts.

---

# 14. Phase 11 — Filters and Search

Add:

- Category filter
- Date filter
- Month filter
- Amount sorting
- Merchant search

Example:

```text
Category: [ Food ▼ ]
Month:    [ September ▼ ]
Search:   [ Cafe ]

[ Apply Filters ]
```

This makes the application feel like a real usable product rather than a basic CRUD assignment.

---

# 15. Phase 12 — Optional AI Feature

Add AI only after the complete non-AI application works.

### AI expense categorization

Instead of only using rules:

```text
"Decathlon Bangalore ₹2,499"
```

AI could classify it as:

```text
Category: Shopping
Reason: Purchase from a retail sporting-goods store.
```

Another possibility:

### Spending insights

Use historical expenses to generate:

```text
Your food spending increased by 18% this month.

You spent ₹4,200 on food.

Consider setting a monthly food budget of ₹3,500.
```

Keep this as an optional feature. The core project should work without AI.

---

# 16. Phase 13 — Error Handling

Handle common situations:

### Invalid image

```text
Please upload a JPG, JPEG, or PNG image.
```

### OCR failure

```text
We couldn't read this receipt clearly.
Please upload a clearer image or enter the expense manually.
```

### Missing amount

```text
Amount could not be detected.
Please enter the amount manually.
```

### Database error

Show a friendly error rather than exposing Python/SQL errors to the user.

---

# 17. Phase 14 — Testing

Test each feature independently.

### Manual expense

- Add expense
- View expense
- Edit expense
- Delete expense

### Receipt OCR

Test:

- Clear receipt
- Blurry receipt
- Different fonts
- ₹ symbol
- Different date formats
- Multiple items
- Missing total

### Dashboard

Check:

- Correct total
- Correct category totals
- Correct monthly totals
- Filters

---

# 18. Phase 15 — Final UI Polish

After functionality is complete:

- Make dashboard responsive.
- Improve spacing and typography.
- Add icons.
- Add loading indicator during OCR.
- Add success/error notifications.
- Make receipt confirmation easy to edit.
- Ensure the application works on both desktop and mobile.

Do not spend most of the project time on CSS.

---

# 19. Recommended Development Order

Follow this exact order:

```text
1. Set up Flask
        ↓
2. Create SQLite database
        ↓
3. Create Expense model
        ↓
4. Build manual Add Expense
        ↓
5. Implement CRUD
        ↓
6. Build expense table
        ↓
7. Build dashboard
        ↓
8. Add Chart.js
        ↓
9. Add receipt upload
        ↓
10. Add OpenCV preprocessing
        ↓
11. Add Tesseract OCR
        ↓
12. Build receipt parser
        ↓
13. Add confirmation/edit screen
        ↓
14. Improve category detection
        ↓
15. Add filters/search
        ↓
16. Testing
        ↓
17. UI polish
        ↓
18. Optional AI feature
```

---

# 20. Minimum Viable Project

If you have very limited time, complete these first:

### Must Have

- [x] Flask application
- [x] SQLite database
- [x] Add expense
- [x] View expenses
- [x] Edit/delete expense
- [x] Receipt image upload
- [x] OCR text extraction
- [x] Amount/date/merchant extraction
- [x] Expense categories
- [x] Dashboard
- [x] One or two charts

### Nice to Have

- [ ] Search
- [ ] Filters
- [ ] OpenCV preprocessing
- [ ] AI categorization
- [ ] AI spending recommendations
- [ ] Login/user accounts

---

# 21. What You Should Be Able to Explain in an Interview

Prepare answers for these questions:

### Why Flask?

> Flask is a lightweight Python web framework. I chose it because the project has a relatively small backend and I wanted to keep the architecture simple.

### Why SQLite?

> SQLite is lightweight, serverless and sufficient for a small personal expense-tracking application.

### What is OCR?

> OCR stands for Optical Character Recognition. It converts text present in an image into machine-readable text.

### Why Tesseract?

> Tesseract is an open-source OCR engine that can extract text from receipt images.

### Why OpenCV?

> OpenCV can preprocess receipt images by resizing, converting to grayscale and reducing noise, which can improve OCR results.

### Where is the backend?

> Flask handles the server-side logic, API endpoints, receipt processing and communication with the SQLite database.

### Where is the frontend?

> HTML and CSS provide the interface, JavaScript handles client-side interactions, and Chart.js displays expense analytics.

### Is the project AI?

> The basic version is not necessarily AI-based. It uses OCR and rule-based processing. I can optionally add an AI model for intelligent expense categorization and spending insights.

---

# 22. Final Project Goal

The finished application should provide this user experience:

```text
                 EXPENSE TRACKER
                       |
        +--------------+--------------+
        |                             |
   Add Manually                  Upload Receipt
        |                             |
        |                         OCR Processing
        |                             |
        +-------------+---------------+
                      |
                Review Details
                      |
                      v
                Save Expense
                      |
                      v
                 SQLite DB
                      |
                      v
                 Dashboard
                      |
          +-----------+-----------+
          |                       |
     Expense Table          Charts/Insights
```

## Suggested project title

**Smart Expense Tracker with Receipt OCR**

This title accurately describes the main differentiator while keeping the project technically manageable.
