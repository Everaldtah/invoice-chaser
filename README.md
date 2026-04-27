# invoice-chaser

> Automated invoice follow-up system with escalating email reminders for freelancers and agencies.

## The Problem

Freelancers lose an average of **$50,000/year** to late or unpaid invoices, and the awkward manual follow-up process causes them to under-chase. Most accounting tools (FreshBooks, Wave) have basic reminders — but they're rigid, ugly, and don't escalate intelligently.

**invoice-chaser** automates the entire follow-up lifecycle: gentle reminders on due date, firm follow-ups at 7 days, urgent notices at 14 days, and final legal-tone notices at 30 days — all with beautiful HTML emails.

## Features

- **4-level escalating reminders** — tone escalates from friendly → firm → urgent → final notice
- **Auto-chaser cron job** — runs daily at 9 AM, automatically sends the right level to each overdue invoice
- **Manual trigger** — trigger any reminder level on demand via API
- **Client management** — store client contacts and invoice history
- **Dashboard stats** — total outstanding, overdue amount, reminders sent
- **Payment link support** — inject a "Pay Now" button into every email
- **Beautiful HTML templates** — color-coded by urgency level

## Tech Stack

- Node.js 18+ / Express
- better-sqlite3 (zero-config local DB)
- Nodemailer (email delivery via SMTP)
- Handlebars (email templates)
- node-cron (scheduled auto-chasing)

## Installation

```bash
git clone https://github.com/Everaldtah/invoice-chaser.git
cd invoice-chaser
npm install

cp .env.example .env
# Edit .env — configure your SMTP credentials

npm start
```

## Usage

### Register your account
```bash
curl -X POST http://localhost:3000/users/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@yourdomain.com", "name": "Your Name"}'
# Returns: { "api_token": "xxx", "user_id": "xxx" }
```

### Add a client
```bash
curl -X POST http://localhost:3000/clients \
  -H "X-Api-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "email": "billing@acme.com", "company": "Acme"}'
```

### Create an invoice
```bash
curl -X POST http://localhost:3000/invoices \
  -H "X-Api-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "CLIENT_ID",
    "invoice_number": "INV-001",
    "amount": 2500.00,
    "due_date": "2026-05-01",
    "description": "Website redesign — Phase 1"
  }'
```

### Manually send a reminder
```bash
curl -X POST http://localhost:3000/invoices/INVOICE_ID/remind \
  -H "X-Api-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"level": 2}'
```

### View dashboard
```bash
curl http://localhost:3000/dashboard -H "X-Api-Token: YOUR_TOKEN"
```

### Mark invoice as paid
```bash
curl -X PATCH http://localhost:3000/invoices/INVOICE_ID/status \
  -H "X-Api-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "paid"}'
```

## Reminder Escalation Schedule

| Level | Trigger | Subject Line | Tone |
|-------|---------|-------------|------|
| 1 | Due date | "Friendly reminder: Invoice due today" | Warm |
| 2 | 7 days overdue | "Follow-up: Invoice 7 days overdue" | Firm |
| 3 | 14 days overdue | "URGENT: Invoice 14 days overdue" | Urgent |
| 4 | 30 days overdue | "Final notice: payment required" | Legal |

## Monetization Model

| Plan | Price | Limits |
|------|-------|--------|
| Free | $0 | 5 active invoices |
| Freelancer | $12/mo | 50 invoices, 1 user |
| Agency | $39/mo | Unlimited invoices, 5 users, white-label emails |
| Enterprise | $99/mo | Custom SMTP, API access, integrations |

**Revenue drivers:** Target freelancers, consultants, and small agencies. Integrate with Stripe, QuickBooks, FreshBooks for upsell. "Remind me when invoice is late" is a $0 → paid conversion trigger.

## License

MIT
