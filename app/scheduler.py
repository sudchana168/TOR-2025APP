from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from . import models, database, line_templates, email_templates
from email.header import Header

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
MAIL_TO = clean_env(os.getenv("MAIL_TO"))
DATE_ALERT = int(clean_env(os.getenv("DATE_ALERT", "7")))

# LINE Configuration
LINE_CHANNEL_ACCESS_TOKEN = clean_env(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_USER_ID = clean_env(os.getenv("LINE_USER_ID"))
LINE_RETRY_KEY = clean_env(os.getenv("LINE_RETRY_KEY")) # Optional
ALERT_METHOD = clean_env(os.getenv("ALERT_METHOD", "EMAIL")).upper() # EMAIL or LINE

# print(f"DATE_ALERT :  {DATE_ALERT}")
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

    # print(f"TO EMAIL : {to_email}")

    
    msg = MIMEMultipart()
    msg['From'] = SMTP_FROM
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')

    # msg.attach(MIMEText(body, 'html'))
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    try:
        print(f"Connecting to SMTP: {SMTP_SERVER}:{SMTP_PORT}")
        
        # Check if we should use SSL based on port 465 or explicit SSL flag if we had one
        # For now, port 465 usually implies SSL
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
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
        
        # Structure: { project_id: { 'name': str, 'email_reminders': [], 'email_reminders_full': [], 'line_reminders': [] } }
        project_groups = {}

        for item in items:
            # Prepare task names
            task_name_full = item.task_name or ""
            task_name_short = task_name_full
            if len(task_name_short) > 40:
                task_name_short = task_name_short[:40] + "..."

            # Check End Date
            if item.end_date:
                delta = (item.end_date - today).days
                
                # Determine eligibility
                is_email_due = False
                is_line_due = False
                
                # Logic: 
                # Project 168: Warranty Reminders
                if item.project_id == 168:
                    if item.start_date:
                        anniv_1 = item.start_date + relativedelta(years=1)
                        anniv_2 = item.start_date + relativedelta(years=2)
                        
                        # Start Date, 1st and 2nd Year Anniversary
                        if today == item.start_date or today == anniv_1 or today == anniv_2:
                            is_email_due = True
                            is_line_due = True
                    
                    # Last Year: Daily reminder 7 days before expiry
                    if 0 <= delta <= 7:
                        is_email_due = True
                        is_line_due = True

                # Default Logic: 
                # Email: 0 <= delta <= DATE_ALERT
                elif 0 <= delta <= DATE_ALERT:
                    is_email_due = True
                    
                # LINE: delta == 0 or delta == DATE_ALERT
                if delta == 0 or delta == DATE_ALERT:
                    is_line_due = True
                
                # Check Configuration
                send_email_flag = False
                send_line_flag = False
                
                if ALERT_METHOD == "BOTH":
                    if is_email_due: send_email_flag = True
                    if is_line_due: send_line_flag = True
                elif ALERT_METHOD == "LINE":
                    if is_line_due: send_line_flag = True
                else: # Default EMAIL
                    if is_email_due: send_email_flag = True

                if send_email_flag or send_line_flag:
                    # Message Creation
                    msg_suffix = ""
                    if delta == 0:
                        msg_suffix = f"ends TODAY ({item.end_date.strftime('%d-%m-%Y')})."
                    elif delta == 1:
                        msg_suffix = f"ends TOMORROW ({item.end_date.strftime('%d-%m-%Y')})."
                    else:
                        msg_suffix = f"ends in {delta} days ({item.end_date.strftime('%d-%m-%Y')})."

                    base_msg_short = f"{item.task_id} : {task_name_short} {msg_suffix}"
                    base_msg_full = f"{item.task_id} : {task_name_full} {msg_suffix}"

                    # Identify Project
                    if item.project:
                        p_id = item.project.id
                        p_name = item.project.name
                    else:
                        p_id = -1
                        p_name = "General / No Project"

                    if p_id not in project_groups:
                        project_groups[p_id] = {
                            'name': p_name,
                            'email_reminders': [],
                            'email_reminders_full': [],
                            'line_reminders': []
                        }

                    if send_email_flag:
                        project_groups[p_id]['email_reminders'].append(base_msg_short)
                        project_groups[p_id]['email_reminders_full'].append(base_msg_full)
                    
                    if send_line_flag:
                        project_groups[p_id]['line_reminders'].append(base_msg_short)

        # Process each group
        for p_id, group in project_groups.items():
            email_reminders_full = group['email_reminders_full']
            line_reminders = group['line_reminders']
            project_name = group['name']

            # Send LINE
            if line_reminders:
                line_msgs = []
                flex_message = line_templates.create_reminder_flex_message(project_name, today.strftime('%d-%m-%Y'), line_reminders)
                line_msgs.append(flex_message)
                send_line_message(line_msgs)

            # Send EMAIL
            if email_reminders_full:
                subject = f"TOR Reminders - {project_name} ({today.strftime('%d-%m-%Y')})"
                body = f"<h2>Project: {project_name}</h2>"
                body += "<ul>" + "".join([f"<li>{r}</li>" for r in email_reminders_full]) + "</ul>"
                
                # Add Enter Site Button (Premium Design)
                body += email_templates.get_enter_site_button_html()
                
                if MAIL_TO:
                    recipients = [email.strip() for email in MAIL_TO.split(',')]
                    for recipient in recipients:
                        if recipient:
                            send_email(recipient, subject, body)
                else:
                    print("MAIL_TO not configured in .env")

    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'cron', hour=10, minute=0) # Run everyday at 10:00 AM
# scheduler.add_job(check_reminders, 'interval', hours=24) # Run once a day
# scheduler.add_job(check_reminders, 'interval', seconds=10) # For testing
