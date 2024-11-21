import smtplib
from email.mime.text import MIMEText
import logging
from config.config import EMAIL_CONFIG


def send_email(jobs):
    """
    Sends an email notification with the new job postings.
    """
    if not jobs:
        logging.info("No new jobs to notify.")
        return

    subject = "New Junior Job Postings in Israel"
    body = "Here are the new junior job postings in Israel:\n\n"
    for job in jobs:
        body += f"Company: {job['company']}\nTitle: {job['title']}\nLocation: {job['location']}\nLink: {job['link']}\n\n"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_CONFIG['sender']
    msg['To'] = EMAIL_CONFIG['receiver']

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
            server.send_message(msg)
        logging.info(f"Email sent successfully with {len(jobs)} job listings.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
