"""
Expense Parser
--------------
Turns raw OCR text into structured expense fields:
    merchant, date, amount, category

This is intentionally rule-based (regex + keyword heuristics) — no AI/LLM involved,
per the current phase of the project.
"""

import re
from datetime import datetime


# --- Category rules -------------------------------------------------------

CATEGORY_KEYWORDS = {
    "Travel": ["uber", "ola", "rapido", "taxi", "cab", "fuel", "petrol", "diesel", "metro", "irctc", "flight", "airlines"],
    "Food": ["swiggy", "zomato", "restaurant", "cafe", "coffee", "food", "eatery", "bakery", "dhaba", "hotel"],
    "Shopping": ["amazon", "flipkart", "myntra", "decathlon", "mall", "store", "mart", "retail", "shop"],
    "Bills": ["electricity", "water bill", "broadband", "recharge", "airtel", "jio", "vodafone", "bsnl", "gas"],
    "Entertainment": ["movie", "cinema", "pvr", "inox", "netflix", "spotify", "hotstar", "bookmyshow"],
    "Medical": ["pharmacy", "hospital", "clinic", "medical", "medicine", "apollo", "chemist"],
    "Education": ["school", "college", "university", "course", "tuition", "books", "udemy", "coursera"],
}

CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Entertainment", "Medical", "Education", "Other"]


# --- Amount extraction ------------------------------------------------------

# The ₹ glyph and nearby currency symbols routinely get OCR'd as stray letters
# (B, 8, R, etc.) rather than dropped cleanly. Rather than requiring an exact
# currency token, we allow a short run of "junk" characters between the
# keyword/colon and the actual digits.
_JUNK = r"[^\d]{0,4}"

AMOUNT_PATTERNS = [
    rf"grand\s*total[:\-]?{_JUNK}([\d,]+(?:\.\d{{1,2}})?)",
    rf"total\s*amount[:\-]?{_JUNK}([\d,]+(?:\.\d{{1,2}})?)",
    rf"amount\s*due[:\-]?{_JUNK}([\d,]+(?:\.\d{{1,2}})?)",
    rf"\btotal\b[:\-]?{_JUNK}([\d,]+(?:\.\d{{1,2}})?)",
    rf"(?:rs\.?|inr|₹){_JUNK}([\d,]+(?:\.\d{{1,2}})?)",
]

# Fallback: individual line-item prices, used to sum a subtotal when no
# total/grand-total keyword is found at all.
LINE_ITEM_PATTERN = re.compile(r"^(?P<label>[a-zA-Z][a-zA-Z .]*?)\s+(?:rs\.?|inr|₹)?\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*$")

# Words that mean a line is a total/summary row, not a purchasable item —
# used to avoid double-counting when falling back to summing line items.
_TOTAL_LINE_WORDS = ("total", "subtotal", "amount due", "grand total", "tax", "gst", "delivery", "fee", "discount")


def extract_amount(text: str):
    lowered = text.lower()
    for pattern in AMOUNT_PATTERNS:
        matches = re.findall(pattern, lowered, re.IGNORECASE)
        if matches:
            # Take the last match for "total"-style patterns (totals usually appear at the bottom)
            raw = matches[-1].replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue

    # No total/keyword found anywhere — fall back to summing plain
    # "label   amount" lines (e.g. "Paracetamol   50"), skipping anything
    # that looks like a summary row itself.
    total = 0.0
    found_any = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(word in stripped.lower() for word in _TOTAL_LINE_WORDS):
            continue
        m = LINE_ITEM_PATTERN.match(stripped)
        if m:
            try:
                total += float(m.group("amount").replace(",", ""))
                found_any = True
            except ValueError:
                continue

    return round(total, 2) if found_any else None


# --- Date extraction ---------------------------------------------------------

DATE_PATTERNS = [
    (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", "%d/%m/%Y"),
    (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b", "%d/%m/%y"),
    (r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})\b", None),
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def extract_date(text: str):
    lowered = text.lower()

    # Numeric formats: dd/mm/yyyy or dd-mm-yyyy (and 2-digit year variants)
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", lowered)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(year, month, day).date()
        except ValueError:
            pass

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b", lowered)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), 2000 + int(m.group(3))
        try:
            return datetime(year, month, day).date()
        except ValueError:
            pass

    # Textual month formats: "13 Sep 2026"
    m = re.search(r"\b(\d{1,2})\s+([a-z]{3,9})\s+(\d{4})\b", lowered)
    if m:
        day = int(m.group(1))
        month_key = m.group(2)[:3]
        year = int(m.group(3))
        if month_key in MONTH_MAP:
            try:
                return datetime(year, MONTH_MAP[month_key], day).date()
            except ValueError:
                pass

    return None


# --- Merchant extraction ------------------------------------------------------

def extract_merchant(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        # Skip lines that are mostly numbers/dates/symbols
        letters = sum(c.isalpha() for c in line)
        if letters >= 3 and not re.search(r"^\d", line):
            # Title-case it for a cleaner display
            return line.title()[:120]
    return None


# --- Category extraction -------------------------------------------------------

def extract_category(text: str, merchant: str = None):
    haystack = (text + " " + (merchant or "")).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in haystack:
                return category
    return "Other"


# --- Main entry point ----------------------------------------------------------

def parse_receipt_text(text: str) -> dict:
    """Given raw OCR text, return a dict of extracted expense fields."""
    merchant = extract_merchant(text)
    amount = extract_amount(text)
    date_val = extract_date(text)
    category = extract_category(text, merchant)

    return {
        "merchant": merchant,
        "amount": amount,
        "date": date_val.isoformat() if date_val else None,
        "category": category,
        "raw_text": text,
    }
