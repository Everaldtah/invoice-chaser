"""
Demo seeder — adds sample invoices to test the app.
Run: python seed_demo.py
"""
import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "invoices.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            invoice_number TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'unpaid',
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_reminded_at TEXT
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            sent_at TEXT DEFAULT (datetime('now')),
            days_overdue INTEGER,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
    """)
    conn.commit()
    return conn

samples = [
    ("Acme Corp", "billing@acme.com", "INV-001", 3500.00, "USD", -45, -15, "unpaid", "Website redesign project"),
    ("TechStart Inc", "accounts@techstart.io", "INV-002", 1200.00, "USD", -30, -2, "unpaid", "Monthly retainer - May 2026"),
    ("GreenLeaf LLC", "finance@greenleaf.co", "INV-003", 850.00, "USD", -60, -30, "unpaid", "SEO consulting"),
    ("Nova Agency", "pay@nova.agency", "INV-004", 5000.00, "USD", -20, 10, "unpaid", "Branding package"),
    ("Bright Ideas Co", "admin@brightideas.com", "INV-005", 2300.00, "USD", -90, -60, "paid", "Mobile app development"),
]

conn = init_db()
today = datetime.now().date()

for name, email, num, amount, curr, issue_offset, due_offset, status, desc in samples:
    issue = today + timedelta(days=issue_offset)
    due = today + timedelta(days=due_offset)
    try:
        conn.execute(
            """INSERT INTO invoices (client_name, client_email, invoice_number, amount, currency, issue_date, due_date, status, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, email, num, amount, curr, issue.isoformat(), due.isoformat(), status, desc)
        )
        print(f"  Added: {num} - {name} (${amount} - {status})")
    except sqlite3.IntegrityError:
        print(f"  Skipped (exists): {num}")

conn.commit()
conn.close()
print("\nDemo data loaded! Run: python main.py")
