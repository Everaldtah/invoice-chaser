# Invoice Chaser

> Stop losing money to late payments. Invoice Chaser automatically sends payment reminders to clients at exactly the right moment.

---

## The Problem

Freelancers and small agencies collectively lose billions annually to late or forgotten payments. Chasing invoices manually is awkward, time-consuming, and often forgotten. Most accounting tools (FreshBooks, QuickBooks) are overpriced and bloated for solo operators.

**Invoice Chaser does one thing well**: it remembers to follow up so you don't have to.

---

## Features

- **Automatic Reminders** — Sends email reminders at day 0 (due), +7, +14, +30, +60 days overdue
- **Escalating Tone** — Friendly → Firm → Final notice, based on how overdue the invoice is
- **Web Dashboard** — Track all invoices, outstanding amounts, and payment status at a glance
- **Manual Nudge** — Send an immediate reminder with one click
- **Mark as Paid** — Keep your records clean
- **Stats Overview** — Total outstanding, collected, overdue counts
- **SMTP Email** — Works with Gmail, SendGrid, Mailgun, or any SMTP provider

---

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI
- **Database**: SQLite (zero-setup, file-based)
- **Templating**: Jinja2 (server-rendered HTML)
- **Email**: Python `smtplib` (SMTP)
- **Scheduling**: Background thread (hourly checks)

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/Everaldtah/invoice-chaser.git
cd invoice-chaser

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your SMTP credentials

# 5. (Optional) Load demo data
python seed_demo.py

# 6. Start the server
python main.py
```

Open http://localhost:8000 in your browser.

---

## Usage

### Creating an Invoice
1. Click **+ New Invoice**
2. Fill in client name, email, invoice number, amount, and due date
3. Submit — the system will automatically send reminders as the due date approaches

### Manual Reminders
Click **Remind** next to any unpaid invoice to send an immediate reminder email.

### Mark as Paid
Click **Mark Paid** when a client pays — removes it from the outstanding queue.

### Email Configuration
For Gmail:
1. Enable 2FA on your Google account
2. Generate an App Password: Google Account → Security → App Passwords
3. Add to `.env`: `SMTP_USER=you@gmail.com` and `SMTP_PASS=your_app_password`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard (HTML) |
| POST | `/invoices` | Create invoice |
| POST | `/invoices/{id}/remind` | Send manual reminder |
| POST | `/invoices/{id}/mark-paid` | Mark invoice as paid |
| POST | `/invoices/{id}/delete` | Delete invoice |
| GET | `/api/invoices` | List all invoices (JSON) |
| GET | `/api/stats` | Get summary stats (JSON) |

---

## Monetization Model

| Plan | Price | Features |
|------|-------|----------|
| **Free** | $0/mo | Up to 5 active invoices |
| **Solo** | $9/mo | Unlimited invoices, custom email templates |
| **Agency** | $29/mo | Multiple sender addresses, client portal links, CSV export |
| **White Label** | $99/mo | Custom branding, custom domain, multi-user |

**LTV projection**: Freelancers earning $50k+/year easily justify $9-29/mo to recover even one late payment per quarter.

---

## Traction Potential

- **TAM**: 59M+ freelancers in the US alone, most using manual invoicing
- **Pain intensity**: Getting paid late directly impacts cashflow — high urgency problem
- **Viral loop**: Clients receive reminder emails branded with your tool → referral opportunity
- **Expansion revenue**: Naturally grows with the user's invoice volume

---

## Environment Variables

See `.env.example` for all configurable options.
