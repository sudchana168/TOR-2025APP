from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from . import models, database
from email.header import Header

# Email Configuration
# Email Configuration
def clean_env(value):
    if value:
        return value.replace('\xa0', ' ').strip()
    return value

SMTP_SERVER = clean_env(os.getenv("MAIL_SERVER", "smtp.gmail.com"))
SMTP_PORT = int(clean_env(os.getenv("MAIL_PORT", "587")))
SMTP_USERNAME = clean_env(os.getenv("MAIL_USERNAME"))
SMTP_PASSWORD = clean_env(os.getenv("MAIL_PASSWORD"))
SMTP_FROM = clean_env(os.getenv("MAIL_FROM"))
DATE_ALERT = clean_env(os.getenv("DATE_ALERT"))
DATE_ALERT = int(clean_env(os.getenv("DATE_ALERT")))
print("DATE_ALERT : ")
print(DATE_ALERT)



def send_email(to_email: str, subject: str, body: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("SMTP credentials not set. Skipping email.")
        print(f"Would have sent email to {to_email}: {subject}")
        print(f"Would have sent email to {to_email}: {subject}")
    # Sanitize inputs
    subject = clean_env(subject)
    body = clean_env(body)
    to_email = clean_env(to_email)
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_FROM
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')

    # msg.attach(MIMEText(body, 'html'))
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    try:
        print(f"Connecting to SMTP: {SMTP_SERVER}:{SMTP_PORT}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        print(f"Logging in as: {SMTP_USERNAME}")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        print(f"Sending email to: {to_email}")
        server.sendmail(SMTP_FROM, to_email, text)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        import traceback
        traceback.print_exc()

def check_reminders():
    print("Checking for reminders...")
    db = database.SessionLocal()
    try:
        today = date.today()
        # Logic: Notify 7 days before due date, or on the day
        # You can customize this logic
        
        items = db.query(models.TORItem).all()
        
        for item in items:
            reminders = []
            
            # Check Start Date
            if item.start_date:
                if item.start_date == today:
                    reminders.append(f"Task '{item.task_name}' starts TODAY ({item.start_date}).")
                elif item.start_date == today + timedelta(days=DATE_ALERT):
                    reminders.append(f"Task '{item.task_name}' starts in {DATE_ALERT} days ({item.start_date}).")

            # Check End Date
            if item.end_date:
                if item.end_date == today:
                    reminders.append(f"Task '{item.task_name}' ends TODAY ({item.end_date}).")
                elif item.end_date == today + timedelta(days=DATE_ALERT):
                    reminders.append(f"Task '{item.task_name}' ends in {DATE_ALERT} days ({item.end_date}).")

            # Check Warranty
            if item.warranty_end_date:
                if item.warranty_end_date == today:
                    reminders.append(f"Warranty for '{item.task_name}' expires TODAY ({item.warranty_end_date}).")
                elif item.warranty_end_date == today + timedelta(days=DATE_ALERT): # 30 days for warranty maybe?
                    reminders.append(f"Warranty for '{item.task_name}' expires in {DATE_ALERT} days ({item.warranty_end_date}).")

            if reminders:
                # Send email
                # For now, sending to the configured sender or a fixed admin email
                # In a real app, you might want to send to 'item.responsible' if it's an email
                subject = f"TOR Reminder: {item.task_name}"
                body = "<ul>" + "".join([f"<li>{r}</li>" for r in reminders]) + "</ul>"
                send_email(SMTP_FROM, subject, body) # Sending to self for now

    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'interval', hours=24) # Run once a day
# scheduler.add_job(check_reminders, 'interval', seconds=10) # For testing
