import os, smtplib
from email.mime.text import MIMEText
from glob import glob

candidates = (
    sorted(glob("analysis/claude_analysis_*.txt"), reverse=True) or
    sorted(glob("scraped_data/*_claude_analysis.txt"), reverse=True)
)

if not candidates:
    os.system("pwd; printf '\n-- ls -la --\n'; ls -la; "
              "printf '\n-- ls -la analysis --\n'; ls -la analysis || true; "
              "printf '\n-- ls -la scraped_data --\n'; ls -la scraped_data || true")
    raise Exception("No Claude analysis result file found.")

analysis_file = candidates[0]
with open(analysis_file, "r", encoding="utf-8") as f:
    analysis_text = f.read()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

msg = MIMEText(analysis_text)
msg['Subject'] = "Claude News Analysis Results"
msg['From'] = EMAIL_USER
msg['To'] = EMAIL_TO

with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())

print(f"Email sent with file: {analysis_file}")
