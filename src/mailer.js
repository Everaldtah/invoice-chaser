const nodemailer = require("nodemailer");
const Handlebars = require("handlebars");
const fs = require("fs");
const path = require("path");

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || "smtp.ethereal.email",
  port: parseInt(process.env.SMTP_PORT || "587"),
  secure: false,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

function loadTemplate(name) {
  const filePath = path.join(__dirname, "templates", `${name}.html`);
  return fs.readFileSync(filePath, "utf8");
}

const REMINDER_CONFIGS = [
  {
    level: 1,
    daysOverdue: 0,
    subject: "Friendly reminder: Invoice {{invoiceNumber}} due today",
    template: "reminder_gentle",
    tone: "friendly",
  },
  {
    level: 2,
    daysOverdue: 7,
    subject: "Follow-up: Invoice {{invoiceNumber}} is 7 days overdue",
    template: "reminder_followup",
    tone: "firm",
  },
  {
    level: 3,
    daysOverdue: 14,
    subject: "URGENT: Invoice {{invoiceNumber}} is 14 days overdue",
    template: "reminder_urgent",
    tone: "urgent",
  },
  {
    level: 4,
    daysOverdue: 30,
    subject: "Final notice: Invoice {{invoiceNumber}} — payment required",
    template: "reminder_final",
    tone: "final",
  },
];

async function sendReminder(invoice, client, level, fromName, fromEmail) {
  const config = REMINDER_CONFIGS.find((r) => r.level === level);
  if (!config) throw new Error(`Unknown reminder level: ${level}`);

  const templateSrc = loadTemplate(config.template);
  const template = Handlebars.compile(templateSrc);

  const context = {
    clientName: client.name,
    invoiceNumber: invoice.invoice_number,
    amount: invoice.amount.toFixed(2),
    currency: invoice.currency,
    dueDate: invoice.due_date,
    issuedDate: invoice.issued_date,
    description: invoice.description,
    daysOverdue: config.daysOverdue,
    fromName,
    fromEmail,
    paymentLink: process.env.PAYMENT_BASE_URL
      ? `${process.env.PAYMENT_BASE_URL}/pay/${invoice.id}`
      : null,
  };

  const html = template(context);
  const subjectTemplate = Handlebars.compile(config.subject);
  const subject = subjectTemplate({ invoiceNumber: invoice.invoice_number });

  const info = await transporter.sendMail({
    from: `"${fromName}" <${fromEmail || process.env.SMTP_USER}>`,
    to: client.email,
    subject,
    html,
  });

  return { messageId: info.messageId, subject, to: client.email };
}

async function verifyConnection() {
  try {
    await transporter.verify();
    return true;
  } catch {
    return false;
  }
}

module.exports = { sendReminder, verifyConnection, REMINDER_CONFIGS };
