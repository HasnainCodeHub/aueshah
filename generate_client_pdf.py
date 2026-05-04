"""Generate the client setup PDF — concise, steps-only, no explanations."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT

OUT = r"I:\Local Disk J\Clinets\aueshah\Aueshah_Client_Setup.pdf"

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=0.7*inch, rightMargin=0.7*inch,
    topMargin=0.7*inch, bottomMargin=0.7*inch,
)

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=12, textColor=colors.HexColor("#1a1a1a"))
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#8B0000"))
body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=11, leading=15, spaceAfter=4)
step = ParagraphStyle("step", parent=body, leftIndent=14)
send = ParagraphStyle("send", parent=body, fontSize=11, leading=15, textColor=colors.HexColor("#0b5394"), spaceBefore=4, spaceAfter=8)
check = ParagraphStyle("check", parent=body, leftIndent=14, spaceAfter=3)

story = []

story.append(Paragraph("Aueshah AI Concierge — Account Setup", h1))
story.append(Paragraph("Create 4 free accounts. Copy the credentials. Send them back.", body))
story.append(Spacer(1, 6))

# 1. NEON
story.append(Paragraph("1. Neon (Database)", h2))
steps = [
    "Go to https://neon.tech and sign up (Google login works).",
    "Project name: <b>aueshah-concierge</b>.",
    "Region: London or Frankfurt.",
    "On the dashboard, click <b>Connection Details</b>.",
    "Copy the full connection string (starts with <b>postgresql://</b>).",
]
story.append(ListFlowable([ListItem(Paragraph(s, step)) for s in steps], bulletType="1"))
story.append(Paragraph("<b>Send me:</b> the connection string.", send))

# 2. UPSTASH
story.append(Paragraph("2. Upstash (Redis)", h2))
steps = [
    "Go to https://upstash.com and sign up.",
    "Click <b>Create Database</b>.",
    "Name: <b>aueshah-rate-limiter</b>. Region: EU-West-1 (Ireland).",
    "Open the database, scroll to <b>Connect to your database</b>.",
    "Copy the <b>Redis Connect URL</b> (starts with <b>redis://default:...</b>).",
]
story.append(ListFlowable([ListItem(Paragraph(s, step)) for s in steps], bulletType="1"))
story.append(Paragraph("<b>Send me:</b> the Redis URL.", send))

# 3. QDRANT
story.append(Paragraph("3. Qdrant (AI Knowledge Base)", h2))
steps = [
    "Go to https://cloud.qdrant.io and sign up.",
    "Click <b>Create Cluster</b>. Name: <b>aueshah-concierge</b>.",
    "Choose <b>Free Tier</b>. Region: EU-West-1 (Ireland).",
    "Open the cluster, go to <b>API Keys</b>, click <b>Create API Key</b>.",
    "Copy the <b>Cluster URL</b> and the <b>API Key</b>.",
]
story.append(ListFlowable([ListItem(Paragraph(s, step)) for s in steps], bulletType="1"))
story.append(Paragraph("<b>Send me:</b> the Cluster URL and API Key.", send))

# 4. RESEND (single API-key signup — no Single Sender Verification needed at this stage)
story.append(Paragraph("4. Resend (Email)", h2))
steps = [
    "Go to https://resend.com and sign up (Google login works).",
    "Verify your email from the inbox link Resend sends you.",
    "In the dashboard: <b>API Keys → Create API Key</b>.",
    "Name: <b>aueshah-concierge</b>. Permission: <b>Full access</b>. Domain: leave default.",
    "Copy the API key immediately (starts with <b>re_</b>) — it is shown only once.",
    "(Optional, later) <b>Domains → Add Domain</b> → enter <b>aueshah.com</b>, follow the DNS steps. Until that's done, emails send from the sandbox sender <b>onboarding@resend.dev</b>.",
]
story.append(ListFlowable([ListItem(Paragraph(s, step)) for s in steps], bulletType="1"))
story.append(Paragraph("<b>Send me:</b> the API key (starts with <b>re_</b>).", send))

story.append(Spacer(1, 10))

# FINAL CHECKLIST
story.append(Paragraph("Send Back — Checklist", h2))
checklist = [
    "Neon connection string",
    "Upstash Redis URL",
    "Qdrant Cluster URL + API key",
    "Resend API key (starts with re_)",
    "Concierge team email(s) for appointment / Noor alerts",
]
for c in checklist:
    story.append(Paragraph(f"☐ {c}", check))

doc.build(story)
print(f"Wrote {OUT}")
