import os
import smtplib
from email.mime.text import MIMEText
from glob import glob

# Get the latest Claude analysis result
files = sorted(glob("scraped_data/*_storylines_ideas.txt"), reverse=True)
if not files:
    raise Exception("No Claude analysis result file found.")
analysis_file = files[0]

with open(analysis_file, "r", encoding="utf-8") as f:
    analysis_text = f.read()

# Email settings from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER")        # e.g. "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))# e.g. 587
EMAIL_USER = os.getenv("EMAIL_USER")          # your email address
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # your app password (never your real password!)
EMAIL_TO = os.getenv("EMAIL_TO")              # destination email address

subject = "Claude News Analysis Results"
msg = MIMEText(analysis_text)
msg['Subject'] = subject
msg['From'] = EMAIL_USER
msg['To'] = EMAIL_TO

# Send email
with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())

print("Email sent!")
