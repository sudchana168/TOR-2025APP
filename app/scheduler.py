from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
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
DATE_ALERT = int(clean_env(os.getenv("DATE_ALERT", "7")))

# LINE Configuration
LINE_CHANNEL_ACCESS_TOKEN = clean_env(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_USER_ID = clean_env(os.getenv("LINE_USER_ID"))
LINE_RETRY_KEY = clean_env(os.getenv("LINE_RETRY_KEY")) # Optional
ALERT_METHOD = clean_env(os.getenv("ALERT_METHOD", "EMAIL")).upper() # EMAIL or LINE

print(f"DATE_ALERT :  {DATE_ALERT}")
print(f"ALERT_METHOD: {ALERT_METHOD}")


def send_email(to_email: str, subject: str, body: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("SMTP credentials not set. Skipping email.")
        print(f"Would have sent email to {to_email}: {subject}")
        return

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

import requests
import uuid
import json

def send_line_message(messages: list):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("LINE credentials not set. Skipping LINE message.")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "X-Line-Retry-Key": LINE_RETRY_KEY if LINE_RETRY_KEY else str(uuid.uuid4())
    }
    
    # LINE allows max 5 messages per request.
    # If we have more, we might need to batch them, but strictly following the loop logic below 
    # we are sending per item or batching all? 
    # The original email logic sent one email PER ITEM if reminders existed.
    # Let's keep it simple: formatting the reminders into text messages.
    
    payload = {
        "to": LINE_USER_ID,
        "messages": messages
    }

    try:
        print(f"Sending LINE push message to {LINE_USER_ID}")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print("LINE message sent successfully.")
    except Exception as e:
        print(f"Failed to send LINE message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")


def check_reminders():
    print("Checking for reminders...")
    db = database.SessionLocal()
    try:
        today = date.today()
        
        items = db.query(models.TORItem).all()
        
        for item in items:
            reminders = []
            
            # # Check Start Date.  *******
            # if item.start_date:
            #     if item.start_date == today:
            #         reminders.append(f"Task '{item.task_name}' starts TODAY ({item.start_date}).")
            #     elif item.start_date == today + timedelta(days=DATE_ALERT):
            #         reminders.append(f"Task '{item.task_name}' starts in {DATE_ALERT} days ({item.start_date}).")

            # Check End Date
            if item.end_date:
                if item.end_date == today:
                    reminders.append(f"Task '{item.task_name}' ends TODAY ({item.end_date}).")
                elif item.end_date == today + timedelta(days=DATE_ALERT):
                    reminders.append(f"Task '{item.task_name}' ends in {DATE_ALERT} days ({item.end_date}).")

            if reminders:
                subject = f"TOR Reminder: {item.task_name}"
                
                if ALERT_METHOD == "LINE":
                    # Create LINE text messages
                    # LINE Text message object format: {"type": "text", "text": "..."}
                    line_msgs = []
                    
                    # # Header message
                    # line_msgs.append({
                    #     "type": "text",
                    #     "text": f"🔔 {subject}"
                    # })
                    
                    # Content message (combining reminders to avoid blowing limits)
                    body_text = "\n".join([f"- {r}" for r in reminders])
                    line_msgs.append({
                        "type": "text",
                        "text": body_text
                    })
                    
                    send_line_message(line_msgs)
                    
                else: 
                    # Default to EMAIL
                    body = "<ul>" + "".join([f"<li>{r}</li>" for r in reminders]) + "</ul>"
                    send_email(SMTP_FROM, subject, body) 

    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'interval', hours=24) # Run once a day
# scheduler.add_job(check_reminders, 'interval', seconds=10) # For testing
