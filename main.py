"""
Invoice Chaser - Automated invoice payment reminder system
"""
import os
import sqlite3
import smtplib
import threading
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import Optional
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Invoice Chaser", description="Automated invoice payment reminder system")

DB_PATH = os.getenv("DB_PATH", "invoices.db")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
APP_NAME = os.getenv("APP_NAME", "Invoice Chaser")

templates = Jinja2Templates(directory="templates")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


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
    conn.close()


def send_email(to_email: str, subject: str, body_html: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        print(f"[EMAIL MOCK] To: {to_email}, Subject: {subject}")
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def build_reminder_email(invoice: dict, days_overdue: int) -> str:
    urgency = "friendly" if days_overdue < 14 else ("firm" if days_overdue < 30 else "final")
    tone_map = {
        "friendly": "Just a friendly reminder that",
        "firm": "We wanted to follow up — ",
        "final": "This is a final notice that",
    }
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
    <h2 style="color:#e74c3c;">Payment Reminder</h2>
    <p>Dear {invoice['client_name']},</p>
    <p>{tone_map[urgency]} invoice <strong>{invoice['invoice_number']}</strong>
    {"is now " + str(days_overdue) + " days overdue" if days_overdue > 0 else "is due today"}.</p>
    <div style="background:#f8f9fa;padding:15px;border-radius:8px;margin:20px 0;">
        <table style="width:100%;">
            <tr><td><strong>Invoice #:</strong></td><td>{invoice['invoice_number']}</td></tr>
            <tr><td><strong>Amount Due:</strong></td><td><strong style="color:#e74c3c;">{invoice['currency']} {invoice['amount']:,.2f}</strong></td></tr>
            <tr><td><strong>Due Date:</strong></td><td>{invoice['due_date']}</td></tr>
            {"<tr><td><strong>Description:</strong></td><td>" + str(invoice.get('description','')) + "</td></tr>" if invoice.get('description') else ""}
        </table>
    </div>
    <p>Please process this payment at your earliest convenience.</p>
    <p>If you've already sent payment, please disregard this notice.</p>
    <p>Thank you for your business!</p>
    <hr/><p style="color:#888;font-size:12px;">Sent by {APP_NAME}</p>
    </body></html>
    """


def check_and_send_reminders():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    today = datetime.now().date()
    invoices = conn.execute(
        "SELECT * FROM invoices WHERE status = 'unpaid'"
    ).fetchall()

    for inv in invoices:
        due = datetime.strptime(inv["due_date"], "%Y-%m-%d").date()
        days_overdue = (today - due).days
        reminder_intervals = [0, 7, 14, 30, 60]

        last_reminded = None
        if inv["last_reminded_at"]:
            last_reminded = datetime.strptime(inv["last_reminded_at"][:10], "%Y-%m-%d").date()

        should_remind = False
        for interval in reminder_intervals:
            check_date = due + timedelta(days=interval)
            if today == check_date and (last_reminded is None or last_reminded < check_date):
                should_remind = True
                break

        if should_remind:
            subject = f"Payment Reminder: Invoice {inv['invoice_number']} - {inv['currency']} {inv['amount']:,.2f}"
            body = build_reminder_email(dict(inv), max(0, days_overdue))
            if send_email(inv["client_email"], subject, body):
                conn.execute(
                    "UPDATE invoices SET last_reminded_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), inv["id"])
                )
                conn.execute(
                    "INSERT INTO reminders (invoice_id, days_overdue) VALUES (?, ?)",
                    (inv["id"], max(0, days_overdue))
                )
                conn.commit()
                print(f"Reminder sent for invoice {inv['invoice_number']} to {inv['client_email']}")

    conn.close()


def reminder_scheduler():
    while True:
        try:
            check_and_send_reminders()
        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(3600)  # Check every hour


# ─── API Routes ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: sqlite3.Connection = Depends(get_db)):
    invoices = db.execute(
        "SELECT *, julianday('now') - julianday(due_date) as days_overdue FROM invoices ORDER BY due_date ASC"
    ).fetchall()
    stats = db.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='unpaid' THEN 1 ELSE 0 END) as unpaid_count,
            SUM(CASE WHEN status='paid' THEN 1 ELSE 0 END) as paid_count,
            SUM(CASE WHEN status='unpaid' THEN amount ELSE 0 END) as unpaid_total,
            SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) as paid_total
        FROM invoices
    """).fetchone()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "invoices": invoices, "stats": stats
    })


@app.post("/invoices", response_class=RedirectResponse)
async def create_invoice(
    client_name: str = Form(...),
    client_email: str = Form(...),
    invoice_number: str = Form(...),
    amount: float = Form(...),
    currency: str = Form("USD"),
    issue_date: str = Form(...),
    due_date: str = Form(...),
    description: str = Form(""),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        db.execute(
            """INSERT INTO invoices (client_name, client_email, invoice_number, amount, currency, issue_date, due_date, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_name, client_email, invoice_number, amount, currency, issue_date, due_date, description)
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Invoice number already exists")
    return RedirectResponse("/", status_code=302)


@app.post("/invoices/{invoice_id}/mark-paid", response_class=RedirectResponse)
async def mark_paid(invoice_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
    db.commit()
    return RedirectResponse("/", status_code=302)


@app.post("/invoices/{invoice_id}/delete", response_class=RedirectResponse)
async def delete_invoice(invoice_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    db.commit()
    return RedirectResponse("/", status_code=302)


@app.post("/invoices/{invoice_id}/remind")
async def send_reminder(invoice_id: int, db: sqlite3.Connection = Depends(get_db)):
    inv = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv["status"] == "paid":
        raise HTTPException(400, "Invoice already paid")
    inv = dict(inv)
    due = datetime.strptime(inv["due_date"], "%Y-%m-%d").date()
    days_overdue = max(0, (datetime.now().date() - due).days)
    subject = f"Payment Reminder: Invoice {inv['invoice_number']} - {inv['currency']} {inv['amount']:,.2f}"
    body = build_reminder_email(inv, days_overdue)
    sent = send_email(inv["client_email"], subject, body)
    if sent:
        db.execute("UPDATE invoices SET last_reminded_at = ? WHERE id = ?", (datetime.now().isoformat(), invoice_id))
        db.execute("INSERT INTO reminders (invoice_id, days_overdue) VALUES (?, ?)", (invoice_id, days_overdue))
        db.commit()
    return {"success": sent, "message": "Reminder sent" if sent else "Failed to send reminder"}


@app.get("/api/invoices")
async def list_invoices(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM invoices ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats")
async def get_stats(db: sqlite3.Connection = Depends(get_db)):
    stats = db.execute("""
        SELECT
            COUNT(*) as total_invoices,
            SUM(CASE WHEN status='unpaid' THEN amount ELSE 0 END) as outstanding_amount,
            SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) as collected_amount,
            SUM(CASE WHEN status='unpaid' AND julianday('now') > julianday(due_date) THEN 1 ELSE 0 END) as overdue_count
        FROM invoices
    """).fetchone()
    return dict(stats)


if __name__ == "__main__":
    init_db()
    scheduler_thread = threading.Thread(target=reminder_scheduler, daemon=True)
    scheduler_thread.start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
