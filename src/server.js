require("dotenv").config();
const express = require("express");
const { v4: uuidv4 } = require("uuid");
const cron = require("node-cron");
const db = require("./database");
const { sendReminder, verifyConnection, REMINDER_CONFIGS } = require("./mailer");

const app = express();
app.use(express.json());

// ── Auth middleware ────────────────────────────────────────────────────────

function auth(req, res, next) {
  const token = req.headers["x-api-token"] || req.headers["authorization"]?.replace("Bearer ", "");
  if (!token) return res.status(401).json({ error: "Missing API token" });

  const user = db.prepare("SELECT * FROM users WHERE api_token = ?").get(token);
  if (!user) return res.status(401).json({ error: "Invalid API token" });

  req.user = user;
  next();
}

// ── Users ─────────────────────────────────────────────────────────────────

app.post("/users/register", (req, res) => {
  const { email, name } = req.body;
  if (!email) return res.status(400).json({ error: "Email required" });

  const existing = db.prepare("SELECT * FROM users WHERE email = ?").get(email);
  if (existing) return res.json({ api_token: existing.api_token, user_id: existing.id });

  const user = { id: uuidv4(), email, name: name || email, api_token: uuidv4(), plan: "free" };
  db.prepare("INSERT INTO users (id, email, name, api_token, plan) VALUES (?, ?, ?, ?, ?)").run(
    user.id, user.email, user.name, user.api_token, user.plan
  );
  res.status(201).json({ api_token: user.api_token, user_id: user.id, message: "Account created" });
});

// ── Clients ───────────────────────────────────────────────────────────────

app.post("/clients", auth, (req, res) => {
  const { name, email, company } = req.body;
  if (!name || !email) return res.status(400).json({ error: "Name and email required" });

  const id = uuidv4();
  db.prepare("INSERT INTO clients (id, name, email, company) VALUES (?, ?, ?, ?)").run(id, name, email, company || null);
  res.status(201).json({ id, name, email, company });
});

app.get("/clients", auth, (req, res) => {
  const clients = db.prepare("SELECT * FROM clients ORDER BY created_at DESC").all();
  res.json(clients);
});

app.get("/clients/:id", auth, (req, res) => {
  const client = db.prepare("SELECT * FROM clients WHERE id = ?").get(req.params.id);
  if (!client) return res.status(404).json({ error: "Client not found" });
  res.json(client);
});

// ── Invoices ──────────────────────────────────────────────────────────────

app.post("/invoices", auth, (req, res) => {
  const { client_id, invoice_number, amount, currency, due_date, issued_date, description } = req.body;
  if (!client_id || !amount || !due_date) {
    return res.status(400).json({ error: "client_id, amount, and due_date required" });
  }

  const client = db.prepare("SELECT * FROM clients WHERE id = ?").get(client_id);
  if (!client) return res.status(404).json({ error: "Client not found" });

  const id = uuidv4();
  const invNum = invoice_number || `INV-${Date.now()}`;
  const issued = issued_date || new Date().toISOString().split("T")[0];

  db.prepare(
    "INSERT INTO invoices (id, client_id, invoice_number, amount, currency, due_date, issued_date, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
  ).run(id, client_id, invNum, amount, currency || "USD", due_date, issued, description || null);

  res.status(201).json({ id, invoice_number: invNum, amount, currency: currency || "USD", due_date, status: "pending" });
});

app.get("/invoices", auth, (req, res) => {
  const { status } = req.query;
  const query = status
    ? "SELECT i.*, c.name as client_name, c.email as client_email FROM invoices i JOIN clients c ON i.client_id = c.id WHERE i.status = ? ORDER BY i.due_date ASC"
    : "SELECT i.*, c.name as client_name, c.email as client_email FROM invoices i JOIN clients c ON i.client_id = c.id ORDER BY i.due_date ASC";
  const invoices = status ? db.prepare(query).all(status) : db.prepare(query).all();
  res.json(invoices);
});

app.patch("/invoices/:id/status", auth, (req, res) => {
  const { status } = req.body;
  const valid = ["pending", "paid", "cancelled", "overdue"];
  if (!valid.includes(status)) return res.status(400).json({ error: `Status must be one of: ${valid.join(", ")}` });

  db.prepare("UPDATE invoices SET status = ? WHERE id = ?").run(status, req.params.id);
  res.json({ id: req.params.id, status });
});

app.get("/invoices/:id/reminders", auth, (req, res) => {
  const reminders = db.prepare("SELECT * FROM reminders WHERE invoice_id = ? ORDER BY sent_at DESC").all(req.params.id);
  res.json(reminders);
});

// ── Manual reminder trigger ────────────────────────────────────────────────

app.post("/invoices/:id/remind", auth, async (req, res) => {
  const invoice = db.prepare("SELECT i.*, c.name as client_name, c.email as client_email FROM invoices i JOIN clients c ON i.client_id = c.id WHERE i.id = ?").get(req.params.id);
  if (!invoice) return res.status(404).json({ error: "Invoice not found" });
  if (invoice.status === "paid") return res.status(400).json({ error: "Invoice already paid" });

  const level = req.body.level || 1;
  const client = { name: invoice.client_name, email: invoice.client_email };

  try {
    const result = await sendReminder(invoice, client, level, req.user.name, req.user.email);
    const remId = uuidv4();
    db.prepare("INSERT INTO reminders (id, invoice_id, sent_at, level, email_to, subject) VALUES (?, ?, ?, ?, ?, ?)").run(
      remId, invoice.id, new Date().toISOString(), level, client.email, result.subject
    );
    res.json({ message: "Reminder sent", level, to: client.email, subject: result.subject });
  } catch (err) {
    res.status(500).json({ error: "Failed to send reminder", detail: err.message });
  }
});

// ── Dashboard stats ────────────────────────────────────────────────────────

app.get("/dashboard", auth, (req, res) => {
  const total = db.prepare("SELECT COUNT(*) as n, SUM(amount) as sum FROM invoices").get();
  const pending = db.prepare("SELECT COUNT(*) as n, SUM(amount) as sum FROM invoices WHERE status = 'pending'").get();
  const overdue = db.prepare("SELECT COUNT(*) as n, SUM(amount) as sum FROM invoices WHERE status = 'pending' AND due_date < date('now')").get();
  const paid = db.prepare("SELECT COUNT(*) as n, SUM(amount) as sum FROM invoices WHERE status = 'paid'").get();
  const reminders_sent = db.prepare("SELECT COUNT(*) as n FROM reminders").get();

  res.json({
    total_invoices: total.n,
    total_value: total.sum || 0,
    pending: { count: pending.n, value: pending.sum || 0 },
    overdue: { count: overdue.n, value: overdue.sum || 0 },
    paid: { count: paid.n, value: paid.sum || 0 },
    reminders_sent: reminders_sent.n,
  });
});

app.get("/health", (req, res) => res.json({ status: "ok" }));

// ── Auto-chaser cron ──────────────────────────────────────────────────────

cron.schedule("0 9 * * 1-5", async () => {
  console.log("[auto-chaser] Running scheduled reminder check...");
  const today = new Date().toISOString().split("T")[0];

  const overdue = db.prepare(`
    SELECT i.*, c.name as client_name, c.email as client_email, u.name as user_name, u.email as user_email
    FROM invoices i
    JOIN clients c ON i.client_id = c.id
    JOIN users u ON u.id = (SELECT id FROM users LIMIT 1)
    WHERE i.status = 'pending' AND i.due_date <= date('now')
  `).all();

  for (const invoice of overdue) {
    const daysOverdue = Math.floor((Date.now() - new Date(invoice.due_date).getTime()) / 86400000);
    const remindersSent = db.prepare("SELECT COUNT(*) as n FROM reminders WHERE invoice_id = ?").get(invoice.id).n;

    let level = null;
    if (daysOverdue === 0 && remindersSent === 0) level = 1;
    else if (daysOverdue >= 7 && remindersSent < 2) level = 2;
    else if (daysOverdue >= 14 && remindersSent < 3) level = 3;
    else if (daysOverdue >= 30 && remindersSent < 4) level = 4;

    if (level) {
      try {
        const client = { name: invoice.client_name, email: invoice.client_email };
        const result = await sendReminder(invoice, client, level, invoice.user_name, invoice.user_email);
        const remId = uuidv4();
        db.prepare("INSERT INTO reminders (id, invoice_id, sent_at, level, email_to, subject) VALUES (?, ?, ?, ?, ?, ?)").run(
          remId, invoice.id, new Date().toISOString(), level, client.email, result.subject
        );
        db.prepare("UPDATE invoices SET status = 'overdue' WHERE id = ? AND status = 'pending'").run(invoice.id);
        console.log(`  ✓ Sent level-${level} reminder for invoice ${invoice.invoice_number} to ${client.email}`);
      } catch (err) {
        console.error(`  ✗ Failed for ${invoice.id}:`, err.message);
      }
    }
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Invoice Chaser running on port ${PORT}`);
  verifyConnection().then((ok) => console.log(`SMTP: ${ok ? "✓ connected" : "✗ not configured"}`));
});
